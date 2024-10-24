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
from assume_roles import role_arn, rcc_auto_session, rcc_session, target_session, bst_onedesign_session, dmz_onedesign_session
from dynamodb import get_all_by_scan
from multiprocessing import Pool
from vpc_services import *
#from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES
from gb_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES
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
        #logger.info(resp['Association'])
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
            #logger.info("when calling the EnableTransitGatewayRouteTablePropagation operation: Propagation '%s' already exists in Transit Gateway Route Table '%s'", tgwAttId, tgwRtId)
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
    routetable_list =list()
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
                #logger.info(route)
                logger.info(f"Destination {route['DestinationCidrBlock']} ===> Transit Gateway {route[key]}")
            #     return "TGW"
            # else:
            #     return "NO-TGW"



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
                logger.info(f"Exiting Route: Destination {route['DestinationCidrBlock']} ===> DMZ Transit Gateway {route[key]}")
                try:
                    logger.info(
                        f"Replacing the Route: Destination {route['DestinationCidrBlock']} ===> ONE(BST) Transit Gateway {tgwid}")
                    resp = ec2.replace_route(
                        DestinationCidrBlock=route['DestinationCidrBlock'],
                        DryRun=DryRun,
                        TransitGatewayId=tgwid,
                        RouteTableId=rtId
                    )
                    # print(resp['ResponseMetadata']['HTTPStatusCode'])
                    if resp['ResponseMetadata']['HTTPStatusCode'] == 200:
                        logger.info(f"Replaced {route['DestinationCidrBlock']}  ===> from {route[key]} to ONE TGW {tgwid} in Route table: {rtId}.")
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




# def aws_create_prefix_list(ec2, name, DryRun=False):
#     try:
#         resp = ec2.create_managed_prefix_list(
#             DryRun=DryRun,
#             PrefixListName=name,
#             MaxEntries=100,
#             AddressFamily='IPv4'
#         )
#         # print(resp["PrefixList"]["PrefixListId"])
#         return resp["PrefixList"]["PrefixListId"]
#     except ClientError as error:
#         if error.response['Error']['Code'] == 'DryRunOperation':
#             logger.info("Success, Account does have the permission to create Managed prefix list.")
#             # return "Success"
#         elif error.response['Error']['Code'] == 'UnauthorizedOperation':
#             logger.info(
#                 "Failed, Account doesn't have permission to create Managed Prefix list, please check Automation role permissions.")
#             # return "Fail"
#             # return False
#         else:
#             logger.error(error)
#             #return False
#
# def check_prefix_list(ec2, name):
#     try:
#         resp = ec2.describe_managed_prefix_lists(
#             DryRun=False,
#             Filters=[
#                 {
#                     'Name': 'prefix-list-name',
#                     'Values': [
#                         name
#                     ]
#                 }
#             ]
#         )
#         logger.info(resp["PrefixLists"][0]["PrefixListId"])
#         return resp["PrefixLists"][0]["PrefixListId"]
#     except IndexError as error:
#         return False
#
#
#
# def modify_prefixlist_size(ec2, id):
#     try:
#         resp = ec2.modify_managed_prefix_list(
#             DryRun=False,
#             PrefixListId=id,
#             MaxEntries=200,
#         )
#         print(resp)
#     except ClientError as error:
#         raise error
#
#
# def add_prefixlist_entries(ec2, id, entries):
#     try:
#         resp = ec2.modify_managed_prefix_list(
#             DryRun=False,
#             PrefixListId=id,
#             # MaxEntries=200,
#             AddEntries=entries
#         )
#         print(resp)
#     except ClientError as error:
#         raise error

def check_and_create_prefixlist(ec2, name, entries, DryRun=False):
    global pl_Id
    pl_Id = check_prefix_list(ec2, name)
    if pl_Id:
        logger.info(f"Prefix list {name} found.")
        return pl_Id
    else:
        pl_id = aws_create_prefix_list(ec2, name, entries, DryRun=DryRun)
        return pl_Id


# def create_tgw_rt_prefix_reference(ec2, tgwRtId, PlId, AttachID):
#     try:
#         resp = ec2.create_transit_gateway_prefix_list_reference(
#         TransitGatewayRouteTableId=tgwRtId,
#         PrefixListId=PlId,
#         TransitGatewayAttachmentId=AttachID,
#         Blackhole=False,
#         DryRun=False
#         )
#         print(resp)
#     except ClientError as error:
#         if error.response['Error']['Code'] == 'AssociationAlreadyExists':
#             #logger.info(error.response['Error']['Message'])
#             logger.info(error.response['Error']['Message'])
#             return "Success"
#         elif error.response['Error']['Code'] == 'UnauthorizedOperation':
#              return error.response['Error']['Message']
#         else:
#             logger.error(error)

def dmz_subnets(ec2, vpc):
    response = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc,
                ]
            },
        ]
    )
    for sn in response:
        for t in sn['Tags']:
            if t['Key'] == "Name" and "PSMGMTNET" in t['Value']:
                print(sn['SubnetId'])


def subnets_from_exiting_tgw_attachment(ec2, dmz_tgw, vpc):
    global subnets
    try:
        old_attach_list = check_existing_vpc_attachment(ec2, dmz_tgw)
        if not old_attach_list:
            logger.info("old_attach_list")
        else:
            for vta in old_attach_list:
                if vta['VpcId'] == vpc:
                    logger.info(f"VPC {vpc} has existing attachment, Hence getting the subnets from attachment.")
                    subnets = vta['SubnetIds']
                    logger.info(f"Subnets {subnets} from existing attachment.")
                    return subnets
    except ClientError as error:
        logger.error(error)


######
def main(env_type, region_name):
    if env_type == "PROD":
        from gb_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES
    else:
        from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS, DMZ_SAME_CIDRS_ENTRIES, AWS_CIDRS_ENTRIES

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
    aws_public_cidrs_entryList = list()
    cidrs = AWS_CIDRS_ENTRIES[region_name]

    for i in cidrs:
        dummy_dict = dict()
        dummy_dict['Cidr'] = i
        aws_public_cidrs_entryList.append(dummy_dict)
    logger.info(aws_public_cidrs_entryList)
    aws_public_pl_id = check_and_create_prefixlist(bst_ec2, "aws_public_cidrs", aws_public_cidrs_entryList,
                                                   DryRun=False)

    ########VPN Prefix list in DMZGB01
    # on_prem_2 = create_prefix_list(bst_ec2, "onprem-cidrs-prefixListTWO", ON_PREM_CIDRS_ENTRIES, DryRun=False)
    # time.sleep(30)
    # logger.info("Creating Prefixlist reference to VPN in DMZ.")
    # check_modify_tgw_rt_prefix_reference(bst_ec2, "tgw-rtb-0d1b3fd78a809429a", "pl-07da824ad0d0a0b9e",
    #                                      "tgw-attach-07cb26d2225f55438")
    # # check_modify_tgw_rt_prefix_reference(bst_ec2, "tgw-rtb-0d1b3fd78a809429a", "pl-07da824ad0d0a0b9e",
    # #                                      "tgw-attach-01b8e2061d87d8aff")
    # create_tgw_rt_prefix_reference(bst_ec2, "tgw-rtb-0d1b3fd78a809429a", on_prem_2, "tgw-attach-01b8e2061d87d8aff")
    #"""
    #####AWS PUBLIC CIDRS###############
    response = get_vpcs(dmz_ec2)
    # logger.info(response)
    for vpc in response:
        vpcs_dict = dict()
        #logger.info(vpc['VpcId'])
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
    logger.info(f"These are the VPCs {vpcs_list} found in DMZ GB Account.")
    
    # resp = create_tgw_rt_prefix_reference(bst_ec2, "tgw-rtb-0d2c8974ba2823bdc", aws_public_pl_id, "tgw-attach-0ba0e5f12c22a4ac8")
    # if resp == "Success":
    #     print("Success")
    # else:
    #     logger.info(resp)
    #     encode_mesg = resp.split(":")
    #     logger.info(encode_mesg[1])
    #     sts_client = bst_session.client("sts")
    #     response = sts_client.decode_authorization_message(
    #         EncodedMessage=encode_mesg[1]
    #     )
    #     logger.info(response)

    ###################Attachment, Assocaiation and Propagation################
    #"""
    ###TGW vpc attch list.
    tgw_vpc_attach_list = list()
    for vpc in vpcs_list:
        logger.info(f"Creating TGW VPC attachment for VPC {vpc}")
        for key, value in vpc.items():
            # if key == "DMZ":
            #     ExistAttachID = get_vpc_attachment(bst_ec2, ONE_TGW, value)
            # #print(key, value)
            # temp_attach_dict = dict()
            subnets = subnets_from_exiting_tgw_attachment(dmz_ec2, DMZ_TGW, value)
            #print(subnets)
            tag_name = f"ONE-DESING-{key}"
            AttachID = create_transit_gateway_spoke_vpc_attachment(dmz_ec2, ONE_TGW, value, subnets, tag_name)
            if AttachID == "DuplicateTransitGatewayAttachment":
                logger.info(f"Transit Gateway and  {key} VPC  Attachment was already existed.")
                ExistAttachID = get_vpc_attachment(bst_ec2, ONE_TGW, value)
                logger.info(f"Existing ONE TGW and {key} VPC Attachment ID: {ExistAttachID}")
                ####DMZ GB VPC logic
                tgw_associate_rt_id = TGW_CONSTANTS[region_name]['DMZSPOKE']['association'][key]
                logger.info(
                    f"Associating the TransitGateway VPC attachment {ExistAttachID} with TransitGateway route table ID: {tgw_associate_rt_id}.")
                create_tgw_route_table_associations(bst_ec2, tgw_associate_rt_id, ExistAttachID)
                logger.info(
                    "TransitGateway VPC attachment request was accepted and associated successfully.")
                #####propagation logic for all time.##Should be commented for migration.
                if key == "DMZ":
                    logger.info(f"Propagating the TransitGateway {key} VPC attachment {ExistAttachID}")
                    propagation_rt_list = TGW_CONSTANTS[region_name]['DMZSPOKE']['propagation'][key]
                    for prt in propagation_rt_list:
                        create_tgw_route_table_propagation(bst_ec2, prt, ExistAttachID)
                    logger.info("TransitGateway VPC attachment propagated successfully.")
                else:
                    logger.info(
                        f"Creating the AWS public cloud prefixlist reference for {key} VPC attachment ID {ExistAttachID}")
                    prefixList_references_rt_list = TGW_CONSTANTS[region_name]['NATVPCS_AWSPUBLICCIDRS']['prefixList_references'][key]
                    for prt in prefixList_references_rt_list:
                        # create_tgw_route_table_propagation(bst_ec2, prt, AttachID)
                        # logger.info("TransitGateway VPC attachment propagated successfully.")
                        if check_modify_tgw_rt_prefix_reference(bst_ec2, prt, aws_public_pl_id, ExistAttachID):
                            logger.info("AWS Public CIDRs prefix list reference was created successfully.")
                ####Creating Tag.
                tag_name = f"NVSGISBSTGB-ONE-DESIGN-{key}"
                tag_Tgwattch(bst_ec2, ExistAttachID, tag_name)
            else:
                logger.info(f"Transit gateway and {key} vpc attachment id {AttachID}.")
                logger.info("Checking the TransitGateway VPC attachment status.")
                cnt = 0
                while cnt < 15:
                    if status_of_vpc_attachment(dmz_ec2, AttachID) == "pendingAcceptance":
                        logger.info(f"TransitGateway VPC attachment {AttachID} status is pendingAcceptance.")
                        break
                    logger.info("Waiting for attachment should be at Pending Acceptance State...")
                    cnt += 1
                    time.sleep(5)
                logger.info(f"Performing TransitGateway and VPC {key} attachment request acceptance, associating "
                            f"and Propagating.")
                accept_transit_gateway_vpc_attachment(bst_ec2, AttachID)
                cnt = 0
                while cnt < 20:
                    logger.info("Checking the TransitGateway VPC attachment status.")
                    #state = status_of_vpc_attachment(bst_ec2, AttachID)
                    if status_of_vpc_attachment(bst_ec2, AttachID) == "available":  # "pendingAcceptance":
                        logger.info(f"TransitGateway VPC attachment {AttachID} status is available.")
                        tgw_associate_rt_id = TGW_CONSTANTS[region_name]['DMZSPOKE']['association'][key]
                        logger.info(
                            f"Associating the TransitGateway VPC attachment {AttachID} with TransitGateway route table ID: {tgw_associate_rt_id}.")
                        create_tgw_route_table_associations(bst_ec2, tgw_associate_rt_id, AttachID)
                        logger.info(
                            "TransitGateway VPC attachment request was accepted and associated successfully.")
                        #####propagation logic for all time.##Should be commented for migration.
                        if key == "DMZ":
                            logger.info(f"Propagating the TransitGateway {key} VPC attachment {AttachID}")
                            propagation_rt_list = TGW_CONSTANTS[region_name]['DMZSPOKE']['propagation'][key]
                            for prt in propagation_rt_list:
                                create_tgw_route_table_propagation(bst_ec2, prt, AttachID)
                            logger.info("TransitGateway VPC attachment propagated successfully.")
                        else:
                            logger.info(f"Creating the AWS public cloud prefixlist reference for {key} VPC attachment ID {AttachID}")
                            prefixList_references_rt_list = TGW_CONSTANTS[region_name]['NATVPCS_AWSPUBLICCIDRS']['prefixList_references'][key]
                            for prt in prefixList_references_rt_list:
                                # create_tgw_route_table_propagation(bst_ec2, prt, AttachID)
                                #logger.info("TransitGateway VPC attachment propagated successfully.")
                                if check_modify_tgw_rt_prefix_reference(bst_ec2, prt, aws_public_pl_id, AttachID):
                                    logger.info("AWS Public CIDRs prefix list reference was created successfully.")
                        ####Creating Tag.
                        tag_name = f"NVSGISBSTGB-ONE-DESIGN-{key}"
                        tag_Tgwattch(bst_ec2, AttachID, tag_name)
                        break
                    logger.info(f"{cnt} -- Waiting for attachment should be at Available State...")
                    cnt += 1
                    time.sleep(10)

    # logger.info(f"TGW NAT VPCs Attachment IDs: {tgw_vpc_attach_list}")
    ###########
    
    ##########################ROUTING RULES############.

    for vpc in vpcs_list:
        logger.info(f"Creating routing rules in VPC {vpc}")
        for key, value in vpc.items():
            if key == "DMZ":
                route_tables = get_routetables(dmz_ec2, value)
                logger.info(f"VPC {key} Route tables are {route_tables}")
                for rt in route_tables:
                    logger.info(f"Route Table ID: {rt}")
                    # logger.info(f"Adding Same region cidrs in Route Table ID: {rt}")
                    # regions_pl_id = check_and_create_prefixlist(dmz_ec2, "same_region_cidrs", DMZ_SAME_CIDRS_ENTRIES[region_name], DryRun=False)
                    logger.info(f"Replacing the Routes in Route Table ID: {rt}")
                    #get_tgw_route_from_routetable(dmz_ec2, rt)
                    replace_route_one_tgw(dmz_ec2, rt, ONE_TGW, DryRun=False)
            else:
                route_tables = get_routetables(dmz_ec2, value)
                logger.info(f"VPC {key} Route tables are {route_tables}")
                for rt in route_tables:
                    logger.info(f"Route Table ID: {rt}")
                    # get_tgw_route_from_routetable(dmz_ec2, rt)
                    replace_route_one_tgw(dmz_ec2, rt, ONE_TGW, DryRun=False)



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
    #main("TEST", "ap-northeast-1")
