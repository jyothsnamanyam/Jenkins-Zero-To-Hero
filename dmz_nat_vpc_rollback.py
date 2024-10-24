"""
Author: Balakrishna Gandam

Purpose
    Used to run python code to manage the aws.

Prerequisites
    - You must have an AWS account, and have your default credentials and AWS Region
      configured.

Running the tests

Running the code
    Run individual functions in the Python shell to make calls to your AWS account.

Additional information
    Running this code might result in charges to your AWS account.
"""
import argparse
import sys
import time
from os import environ
import logging
import logging.handlers
import boto3
import botocore
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from assume_roles import role_arn, rcc_auto_session, rcc_session, target_session, bst_onedesign_session, \
    dmz_onedesign_session
from dynamodb import get_all_by_scan
from multiprocessing import Pool
from vpc_services import *
# from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES
from gb_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, \
    TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES
from threading import Thread

LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


##region and boto3 clients
# regionName = environ['RegionName']
###Global variables


def tgw_vpc_attachment_request(ec2, one_tgw, vpcId, subnets, name):
    attach_tag = f"ONE-DESING-{name}"
    AttachId = create_transit_gateway_spoke_vpc_attachment(ec2, one_tgw, vpcId, subnets, attach_tag)
    if AttachId:
        logger.info(f"TGW {one_tgw} and VPC {name} Attachment was created successfully.")
    elif AttachId == "DuplicateTransitGatewayAttachment":
        logger.info(f"TGW {one_tgw} and VPC {name} Attachment already existed.")
    else:
        logger.error(AttachId)


def accept_transit_gateway_vpc_attachment(ec2, tgwAtchID):
    resp = ec2.accept_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=tgwAtchID
    )


def status_of_vpc_attachment(ec2, tgwAtchID):
    res = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[
            tgwAtchID,
        ],
        DryRun=False
    )
    state = res['TransitGatewayVpcAttachments'][0]['State']
    # print(state)
    return state


def create_tgw_route_table_associations(ec2, tgwRtId, tgwAttId):
    try:
        resp = ec2.associate_transit_gateway_route_table(
            TransitGatewayRouteTableId=tgwRtId,
            TransitGatewayAttachmentId=tgwAttId
        )
        # logger.info(resp['Association'])
        return resp['Association']['State']
    except ClientError as error:
        if error.response['Error']['Code'] == 'Resource.AlreadyAssociated':
            return "AlreadyAssociated"
        else:
            logger.error(error)


def create_tgw_route_table_propagation(ec2, tgwRtId, tgwAttId):
    try:
        resp = ec2.enable_transit_gateway_route_table_propagation(
            TransitGatewayRouteTableId=tgwRtId,
            TransitGatewayAttachmentId=tgwAttId
        )
        logger.info(resp['Propagation'])
        return resp['Propagation']['State']
    except ClientError as error:
        if error.response['Error']['Code'] == 'TransitGatewayRouteTablePropagation.Duplicate':
            # logger.info("when calling the EnableTransitGatewayRouteTablePropagation operation: Propagation '%s' already exists in Transit Gateway Route Table '%s'", tgwAttId, tgwRtId)
            return "Duplicate"
        else:
            logger.info(error)


def tag_Tgwattch(ec2, tgwAtId, name):
    resp = ec2.create_tags(
        Resources=[
            tgwAtId,
        ],
        Tags=[
            {
                'Key': 'Name',
                'Value': name
            },
        ]
    )


def get_routetables(ec2, vpc):
    routetable_list = list()
    paginator = ec2.get_paginator('describe_route_tables')
    response_iterator = paginator.paginate(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc,
                ]
            }
        ],
        DryRun=False,
        PaginationConfig={
            'MaxItems': 100,
            'PageSize': 100
        }
    )
    for page in response_iterator:
        for routetable in page['RouteTables']:
            for asc in routetable['Associations']:
                if asc['Main']:
                    break
                else:
                    routetable_list.append(asc['RouteTableId'])
    return routetable_list


def get_tgw_route_from_routetable(ec2, rt):
    resp = ec2.describe_route_tables(
        DryRun=False,
        RouteTableIds=[rt]
    )
    for route in resp['RouteTables'][0]['Routes']:
        for key in route:
            # if key == "TransitGatewayId" and route['DestinationCidrBlock'] == "0.0.0.0/0":
            if key == "TransitGatewayId":
                # logger.info(route)
                logger.info(f"Destination {route['DestinationCidrBlock']} ===> Transit Gateway {route[key]}")
            #     return "TGW"
            # else:
            #     return "NO-TGW"


def disable_tgw_route_table_propagation(ec2, tgwRtId, tgwAttId, DryRun=True):
    try:
        resp = ec2.disable_transit_gateway_route_table_propagation(
        TransitGatewayRouteTableId=tgwRtId,
        TransitGatewayAttachmentId=tgwAttId,
        DryRun=DryRun,
        )
        logger.info(resp)
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to disable Transit gateway attachment.")

        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.info(
                "Failed, Account doesn't have permission to disbale Transi gateway attachment., please check Automation role permissions.")
        elif error.response['Error']['Code'] == 'TransitGatewayRouteTablePropagation.NotFound':
            logger.info(error)
        else:
            logger.error(error)



def replace_route_one_tgw(ec2, rtId, tgwid, DryRun=True):
    resp = ec2.describe_route_tables(
        DryRun=False,
        RouteTableIds=[rtId]
    )
    for route in resp['RouteTables'][0]['Routes']:
        for key in route:
            # if key == "TransitGatewayId" and route['DestinationCidrBlock'] == "0.0.0.0/0":
            if key == "TransitGatewayId":
                # logger.info(route)
                logger.info(
                    f"Exiting Route: Destination {route['DestinationCidrBlock']} ===> Transit Gateway {route[key]}")
                try:
                    logger.info(
                        f"Replacing the Route: Destination {route['DestinationCidrBlock']} ===> Transit Gateway {tgwid}")
                    resp = ec2.replace_route(
                        DestinationCidrBlock=route['DestinationCidrBlock'],
                        DryRun=DryRun,
                        TransitGatewayId=tgwid,
                        RouteTableId=rtId
                    )
                    # print(resp['ResponseMetadata']['HTTPStatusCode'])
                    if resp['ResponseMetadata']['HTTPStatusCode'] == 200:
                        logger.info(
                            f"Replaced {route['DestinationCidrBlock']}  ===> from {route[key]} to ONE TGW {tgwid} in Route table: {rtId}.")
                except ClientError as error:
                    if error.response['Error']['Code'] == 'DryRunOperation':
                        logger.info("Success, Account does have the permission to replace route.")
                        # return "Success"
                    elif error.response['Error']['Code'] == 'UnauthorizedOperation':
                        logger.error(
                            "Failed, Account doesn't have permission to replace route, please check the Automation role permissions.")
                        # return "Fail"
                    elif error.response['Error']['Code'] == 'RouteAlreadyExists':
                        logger.warning(error.response['Error']['Message'])
                        # return False
                    else:
                        logger.error(f"Replacing route failed in {rtId} due to {error}")



######
def main(env_type, region_name):
    if env_type == "PROD":
        from gb_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, \
            TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES
    else:
        from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, \
            TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES

    ONE_TGW = TGW_CONSTANTS[region_name]['one_tgw']
    DMZ_TGW = TGW_CONSTANTS[region_name]['dmz_tgw']
    DMZ_VPC_NAME = f"VPC{TGW_CONSTANTS[region_name]['short_region']}DMZ"
    NATGB_VPC_NAME = f"VPC{TGW_CONSTANTS[region_name]['short_region']}NATGB"
    NATPGB_VPC_NAME = f"VPC{TGW_CONSTANTS[region_name]['short_region']}NATPGB"
    NATDEV_VPC_NAME = f"VPC{TGW_CONSTANTS[region_name]['short_region']}NATDEV"
    ###DMZ Session
    dmz_session = dmz_onedesign_session(env_type)
    dmz_ec2 = dmz_session.client("ec2", region_name)
    ###
    bst_session = bst_onedesign_session(env_type)
    bst_ec2 = bst_session.client("ec2", region_name)
    #####
    # logger.info(f"DMZ VPC: {DMZ_VPC_NAME}")
    ###Getting the VPCs by Tag Name.
    vpcs_list = list()
    #####AWS PUBLIC CIDRS###############
    response = get_vpcs(dmz_ec2)
    # logger.info(response)
    for vpc in response:
        vpcs_dict = dict()
        # logger.info(vpc['VpcId'])
        for t in vpc['Tags']:
            if t['Key'] == "Name":
                # logger.info(t['Value'])
                if t['Value'] == DMZ_VPC_NAME:
                    vpcs_dict["DMZ"] = vpc['VpcId']
                elif t['Value'] == NATGB_VPC_NAME:
                    vpcs_dict["NATGB"] = vpc['VpcId']
                elif t['Value'] == NATPGB_VPC_NAME:
                    vpcs_dict["NATPGB"] = vpc['VpcId']
                elif t['Value'] == NATDEV_VPC_NAME:
                    vpcs_dict["NATDEV"] = vpc['VpcId']
        if vpcs_dict:
            vpcs_list.append(vpcs_dict)
    logger.info(f"These are the VPCs {vpcs_list} found in DMZ.")
    ##########################ROUTING RULES############.

    for vpc in vpcs_list:
        for key, value in vpc.items():
            ExistAttachID = get_vpc_attachment(bst_ec2, ONE_TGW, value)
            logger.info(f"Found existing ONE TGW and {key }VPC Attachment ID: {ExistAttachID} , Hence disabling the propagation.")
            propagation_rt_list = TGW_CONSTANTS[region_name]['DMZSPOKE']['propagation'][key]
            for prt in propagation_rt_list:
                disable_tgw_route_table_propagation(bst_ec2, prt, ExistAttachID, DryRun=False)
            logger.info(f"Updating the routing rules in VPC {vpc}")
            route_tables = get_routetables(dmz_ec2, value)
            logger.info(f"VPC {key} Route tables are {route_tables}")
            for rt in route_tables:
                logger.info(f"Route Table ID: {rt}")
                replace_route_one_tgw(dmz_ec2, rt, DMZ_TGW, DryRun=False)

    logging.warning("Make sure you remove the DMZ VPC CIDR from BGP Import filter in EWTP IPSEC-VPN.")
    # """


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add routing resources",
        epilog="python3 scripts/dmz_nat_vpc_spoke_automation.py --env_type='TEST' --region_name='ap-northeast-1' "
    )
    parser.add_argument('--env_type',
                        required=False,
                        help='account environment type, Ex: TEST or PROD')
    parser.add_argument('--region_name',
                        required=False,
                        help='aws region name, Ex:ap-northeast-1')

    args = parser.parse_args()
    env_type = args.env_type
    region_name = args.region_name
    main(env_type, region_name)
    # main("TEST", "ap-northeast-1", "INTERNET")
