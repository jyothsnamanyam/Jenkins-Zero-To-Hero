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
import datetime
from os import environ
from os.path import dirname
import logging
import logging.handlers
import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore
from botocore.exceptions import ClientError
##setting logs
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
##import source code logics.*



on_prem_cidrs = [
    "10.0.0.0/8",
    "86.116.0.0/15",
    "147.167.0.0/16",
    "160.61.0.0/16",
    "160.62.0.0/16",
    "161.61.0.0/16",
    "162.86.0.0/16",
    "165.140.0.0/16",
    "170.60.0.0/16",
    "192.37.0.0/16",
    "202.236.224.0/21",
    "170.236.0.0/15",
    "172.16.0.0/12",
    "81.146.227.160/28",
    "109.159.241.160/28"
]


def get_vpcs(client):
    response = client.describe_vpcs(
        DryRun=False,
        MaxResults=20
    )
    return response['Vpcs']



def list_azs(ec2, regionName):
    azs_list = []
    resp = ec2.describe_availability_zones(
        Filters=[
            {
                'Name': 'region-name',
                'Values': [
                    regionName,
                ]
            },
        ]
    )
    for az in resp['AvailabilityZones']:
        azs_list.append(az['ZoneId'])
    new_list = list(set(azs_list))
    new_list.sort()
    return new_list
    # print(resp['AvailabilityZones'][0]['ZoneName'])


def list_subnets_by_azs(ec2, vpcid, regionName):
    subnets_list = []
    response = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpcid,
                ]
            },
        ]
    )
    azs_list = list_azs(ec2, regionName)
    #print(azs_list)
    for az in azs_list:
        for sn in response['Subnets']:
            if sn['AvailabilityZoneId'] == az:
                subnets_list.append(sn['SubnetId'])
                break
            else:
                pass
    #print(subnets_list)
    return subnets_list


def create_transit_gateway_vpc_attachment(ec2, tgwid, vpcid, user_sub_list, attach_name, ApplianceMode="disable", DryRun=False):
    resp = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tgwid,
        VpcId=vpcid,
        SubnetIds=user_sub_list,
        Options={
            'DnsSupport': 'enable',
            'Ipv6Support': 'disable',
            'ApplianceModeSupport': ApplianceMode
        },
        TagSpecifications=[
            {
                 'ResourceType': 'transit-gateway-attachment',
                 'Tags': [
                    {
                        'Key': 'Name',
                        'Value': attach_name
                    },
                ]
            },
        ],
        DryRun=DryRun
    )
    return resp


def create_transit_gateway_spoke_vpc_attachment(ec2, tgwid, vpcid, sub_list, attach_name):
    try:
        resp = create_transit_gateway_vpc_attachment(ec2, tgwid, vpcid,sub_list, attach_name, ApplianceMode="disable", DryRun=False)
        # print(resp['TransitGatewayVpcAttachment']['TransitGatewayAttachmentId'])
        return resp['TransitGatewayVpcAttachment']['TransitGatewayAttachmentId']
        #return "Created"
    except ClientError as error:
        if error.response['Error']['Code'] == 'DuplicateTransitGatewayAttachment':
            #logger.info("Transit Gateway VPC Attachment was found.")
            return "DuplicateTransitGatewayAttachment"
        elif error.response['Error']['Code'] == 'InvalidParameterValue':
            return "DuplicateTransitGatewayAttachment"
        elif error.response['Error']['Code'] == 'InvalidTransitGatewayID.NotFound':
            #logger.error(error)
            return error
            #return False
        else:
            #logger.error(error)
            return error
            #return False


def test_transit_gateway_vpc_attachment(ec2, tgwid, vpcid, sublist):
    """
    This function used to test the transit gateway
    vpc attachment creation permission.
    :param tgwid:
    :param vpcid:
    :return: True
    """
    # sub_list = list_subnets_by_azs(vpcid)
    #print(sub_list)
    try:
        resp = create_transit_gateway_vpc_attachment(ec2, tgwid, vpcid, sublist, "test_attach", ApplianceMode="disable", DryRun=True)
        #print(resp)
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to create Transit gateway VPC attachment.")
            return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.info("Failed, Account doesn't have the permission to create Transit gateway VPC attachment, please check Automation role permissions.")
            return "Fail"
        else:
            logger.error(error)
            return False, error



def check_existing_vpc_attachment(ec2, tgwId):
    resp = ec2.describe_transit_gateway_vpc_attachments(
        Filters=[
            {
                'Name': 'transit-gateway-id',
                'Values': [
                    tgwId
                ]
            },
            {
                'Name': 'state',
                'Values': [
                    'available',
                ]
            },
        ]
    )
    # print(resp['TransitGatewayVpcAttachments'])
    return resp['TransitGatewayVpcAttachments']


def get_vpc_attachment(ec2, tgwId, vpcId):
    resp = ec2.describe_transit_gateway_vpc_attachments(
        Filters=[
            {
                'Name': 'transit-gateway-id',
                'Values': [
                    tgwId
                ]
            },
            {
                'Name': 'vpc-id',
                'Values': [
                    vpcId,
                ]
            },
            {
                'Name': 'state',
                'Values': [
                    'available',
                ]
            },
        ]
    )
    # print(resp['TransitGatewayVpcAttachments'])
    return resp['TransitGatewayVpcAttachments'][0]['TransitGatewayAttachmentId']


def list_subnets(ec2, vpcid):
    subnets_list = []
    response = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpcid,
                ]
            },
        ]
    )
    for sn in response['Subnets']:
        subnets_list.append(sn['SubnetId'])
    return subnets_list


def check_vpc_pending_attachment(ec2, tgwId, vpcid):
    resp = ec2.describe_transit_gateway_attachments(
        Filters=[
            {
                'Name': 'transit-gateway-id',
                'Values': [
                    tgwId
                ]
            },
            {
                'Name': 'resource-id',
                'Values': [
                    vpcid,
                ]
            },
            {
                'Name': 'state',
                'Values': [
                    'pendingAcceptance',
                ]
            }
        ]
    )
    vta = resp['TransitGatewayAttachments']
    if not vta:
        print("No Pending TGW attachment for VPC:", vpcid)
        return False
    else:
        for i in range(len(vta)):
            # try:
            vta_vpcid = vta[i]['ResourceId']
            if vta_vpcid == vpcid:
                print("VPC attachment was there for VPC:", vpcid)
                print("VPC attachment ID:", vta[i]['TransitGatewayAttachmentId'])
                return vta[i]['TransitGatewayAttachmentId']
            else:
                # print("VPC was not attached to TGW:", vpcid)
                pass
                #return False
            # except IndexError:
            #     print("No Route table found")


def create_Vpc_rt_prefixlist_route(ec2, rtId, tgId, plId, DryRun=True):
    try:
        resp = ec2.create_route(
            DestinationPrefixListId=plId,
            TransitGatewayId=tgId,
            RouteTableId=rtId,
            DryRun=DryRun
        )
        # print(resp['ResponseMetadata']['HTTPStatusCode'])
        if resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info(f"Added CIDR: {plId} in Route table: {rtId}")
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to create prefix list route.")
            #return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.warning(
                "Failed, Account doesn't have permission to create prefix list route, please check the Automation role permissions.")
            #return "Fail"
        elif error.response['Error']['Code'] == 'RouteAlreadyExists':
            logger.info(error.response['Error']['Message'])
            # return False
        else:
            logger.error(f"Adding route failed in {rtId} due to {error}")
            #return False


def create_Vpc_rt_route(ec2, rtId, tgId, cidr, DryRun=True):
    try:
        resp = ec2.create_route(
            DestinationCidrBlock=cidr,
            TransitGatewayId=tgId,
            RouteTableId=rtId,
            DryRun=DryRun
        )
        # print(resp['ResponseMetadata']['HTTPStatusCode'])
        if resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info(f"Added CIDR: {cidr} in Route table: {rtId}")
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to create route.")
            #return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.warning(
                "Failed, Account doesn't have permission to create route, please check the Automation role permissions.")
            #return "Fail"
        elif error.response['Error']['Code'] == 'RouteAlreadyExists':
            logger.info(error.response['Error']['Message'])
            # return False
        else:
            logger.error(f"Adding route failed in {rtId} due to {error}")
            #return False


def create_spokeVpc_rt_static_route(ec2, rtId, tgId, cidrs, DryRun=True):
    for cidr in cidrs:
        create_Vpc_rt_route(rtId, tgId, cidr, DryRun=DryRun)


def create_spokeVpc_static_route_in_mutl_rt(ec2, rtids, tgId, cidrs, DryRun=True):
    for rt in rtids:
        create_spokeVpc_rt_static_route(rt, tgId, cidrs, DryRun=DryRun)


def get_tgwid_from_routetable(ec2, rt):
    resp = ec2.describe_route_tables(
        DryRun=False,
        RouteTableIds=[rt]
    )
    for route in resp['RouteTables'][0]['Routes']:
        for key in route:
            # if key == "TransitGatewayId" and route['DestinationCidrBlock'] == "0.0.0.0/0":
            if key == "TransitGatewayId":
                #print(route)
                #print(route[key])
                return "TGW"
            else:
                return "NO-TGW"


def get_default_tgwid_from_routetable(ec2, rt):
    resp = ec2.describe_route_tables(
        DryRun=False,
        RouteTableIds=[rt]
    )
    for route in resp['RouteTables'][0]['Routes']:
        for key in route:
            if key == "TransitGatewayId" and route['DestinationCidrBlock'] == "0.0.0.0/0":
            #if key == "TransitGatewayId":
                #print(route)
                #print(route[key])
                return "TGW"
            else:
                return "NO-TGW"



def replace_default_route(ec2, rtId, tgwid,  DryRun=True):
    try:
        resp = ec2.replace_route(
            DestinationCidrBlock='0.0.0.0/0',
            DryRun=DryRun,
            TransitGatewayId=tgwid,
            RouteTableId=rtId
        )
        # print(resp['ResponseMetadata']['HTTPStatusCode'])
        if resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info(f"Replacing 0.0.0.0/0 CIDR points to ONE TGW {tgwid} in Route table: {rtId}")
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to replace route.")
            #return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.warning(
                "Failed, Account doesn't have permission to replace route, please check the Automation role permissions.")
            #return "Fail"
        elif error.response['Error']['Code'] == 'RouteAlreadyExists':
            logger.info(error.response['Error']['Message'])
            # return False
        else:
            logger.error(f"Replacing route failed in {rtId} due to {error}")
            #return False


def replace_route_one_tgw(ec2, rtId, tgwid, DryRun=True):
    resp = ec2.describe_route_tables(
        DryRun=False,
        RouteTableIds=[rtId]
    )
    for route in resp['RouteTables'][0]['Routes']:
        # logger.info(route)
        try:
            for key in route:
                if key == "TransitGatewayId" and route['DestinationCidrBlock'] == "0.0.0.0/0":
                # if key == "TransitGatewayId":
                    # logger.info(route)
                    logger.info(f"Exiting Route: Destination {route['DestinationCidrBlock']} ===> Exisitng Transit Gateway ID: {route[key]}")
                    try:
                        logger.info(
                            f"Replacing the Route: Destination {route['DestinationCidrBlock']} ===> New Transit Gateway ID: {tgwid}")
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
        except KeyError:
            pass



def create_prefix_list(ec2, name, entries, size, DryRun=False):
    try:
        resp = ec2.create_managed_prefix_list(
            DryRun=DryRun,
            PrefixListName=name,
            Entries=entries,
            MaxEntries=size,
            AddressFamily='IPv4'
        )
        print(resp["PrefixList"]["PrefixListId"])
        return resp["PrefixList"]["PrefixListId"]
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to create Managed prefix list.")
            # return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.info(
                "Failed, Account doesn't have permission to create Managed Prefix list, please check Automation role permissions.")
            # return "Fail"
            # return False
        else:
            logger.error(error)
            #return False


def aws_create_prefix_list(ec2, name, entries, DryRun=False):
    try:
        resp = ec2.create_managed_prefix_list(
            DryRun=DryRun,
            PrefixListName=name,
            Entries=entries,
            MaxEntries=200,
            AddressFamily='IPv4'
        )
        # print(resp["PrefixList"]["PrefixListId"])
        return resp["PrefixList"]["PrefixListId"]
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to create Managed prefix list.")
            # return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.info(
                "Failed, Account doesn't have permission to create Managed Prefix list, please check Automation role permissions.")
            # return "Fail"
            # return False
        else:
            logger.error(error)
            #return False


def check_prefix_list(ec2, name):
    try:
        resp = ec2.describe_managed_prefix_lists(
            DryRun=False,
            Filters=[
                {
                    'Name': 'prefix-list-name',
                    'Values': [
                        name
                    ]
                }
            ]
        )
        logger.info(resp["PrefixLists"][0]["PrefixListId"])
        return resp["PrefixLists"][0]["PrefixListId"]
    except IndexError as error:
        return False


def get_prefix_list_associations(ec2, id):
    try:
        resp = ec2.get_managed_prefix_list_associations(
            DryRun=False,
            PrefixListId=id
        )
        logger.info(resp)
    except ClientError as error:
        raise error


def get_prefix_list_entries(ec2, id):
    try:
        resp = ec2.get_managed_prefix_list_entries(
            DryRun=False,
            PrefixListId=id
        )
        logger.info(resp['Entries'])
    except ClientError as error:
        raise error


def modify_entry_toPrefixList(ec2, id, newcidr, oldcidr):
    try:
        resp = ec2.modify_managed_prefix_list(
            DryRun=False,
            PrefixListId=id,
            AddEntries=[
                {
                    'Cidr': newcidr
                }
            ],
            RemoveEntries=[
                {
                    'Cidr': oldcidr
                }
            ]
        )
        print(resp)
    except ClientError as error:
        raise error


def modify_PrefixList_Size(ec2, id, size):
    try:
        resp = ec2.modify_managed_prefix_list(
            DryRun=False,
            PrefixListId=id,
            MaxEntries=size,
        )
        print(resp)
    except ClientError as error:
        raise error



def get_routetables(ec2):
    routetable_list =list()
    paginator = ec2.get_paginator('describe_route_tables')
    response_iterator = paginator.paginate(
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


def delete_cidr_route(ec2, cidr, rt, DryRun=True):
    try:
        response = ec2.delete_route(
            DestinationCidrBlock=cidr,
            DryRun=DryRun,
            RouteTableId=rt
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to delete the cidr block.")
            return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.info(
                "Failed, Account doesn't have permission to delete the cidr block, please check Automation role permissions.")
            return "Fail"
            # return False
        else:
            logger.error(error)
            #return False


def delete_prefixList_route(ec2, pl_id, rt, DryRun=True):
    resp = ec2.describe_route_tables(
        DryRun=False,
        RouteTableIds=[rt]
    )
    for route in resp['RouteTables'][0]['Routes']:
        # logger.info(route)
        for key in route:
            try:
                if key == "TransitGatewayId" :
                    # logger.info(route)
                    logger.info(
                        f"Exiting Route: Destination {route['DestinationPrefixListId']} ===> Exisitng Transit Gateway ID: {route[key]}")
                    if pl_id == route['DestinationPrefixListId']:
                        try:
                            response = ec2.delete_route(
                                DestinationPrefixListId=pl_id,
                                DryRun=DryRun,
                                RouteTableId=rt
                            )
                        except ClientError as error:
                            if error.response['Error']['Code'] == 'DryRunOperation':
                                logger.info("Success, Account does have the permission to delete the prefix list route.")
                                return "Success"
                            elif error.response['Error']['Code'] == 'UnauthorizedOperation':
                                logger.info(
                                    "Failed, Account doesn't have permission to delete prefix list route, please check Automation role permissions.")
                                return "Fail"
                                # return False
                            else:
                                logger.error(error)
                                #return False
            except KeyError:
                pass


def delete_prefixList(ec2, pl_id, DryRun=True):
    try:
        response = ec2.delete_managed_prefix_list(
            DryRun=DryRun,
            PrefixListId=pl_id
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            logger.info("Success, Account does have the permission to delete the prefix list.")
            return "Success"
        elif error.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.info(
                "Failed, Account doesn't have permission to delete prefix list, please check Automation role permissions.")
            return "Fail"
            # return False
        else:
            logger.error(error)
            #return False


def create_tgw_rt_prefix_reference(ec2, tgwRtId, PlId, AttachID):
    try:
        resp = ec2.create_transit_gateway_prefix_list_reference(
        TransitGatewayRouteTableId=tgwRtId,
        PrefixListId=PlId,
        TransitGatewayAttachmentId=AttachID,
        Blackhole=False,
        DryRun=False
        )
        print(resp)
    except ClientError as error:
        if error.response['Error']['Code'] == 'AssociationAlreadyExists':
            #logger.info(error.response['Error']['Message'])
            logger.info(error.response['Error']['Message'])
        else:
            logger.error(error)



def modify_tgw_rt_prefix_reference(ec2, tgwRtId, PlId, AttachID):
    resp = ec2.modify_transit_gateway_prefix_list_reference(
    TransitGatewayRouteTableId=tgwRtId,
    PrefixListId=PlId,
    TransitGatewayAttachmentId=AttachID,
    Blackhole=False,
    DryRun=False
    )
    logger.info(resp)


def check_modify_tgw_rt_prefix_reference(ec2, tgwRtId, PlId, AttachID):
    try:
        resp = ec2.create_transit_gateway_prefix_list_reference(
        TransitGatewayRouteTableId=tgwRtId,
        PrefixListId=PlId,
        TransitGatewayAttachmentId=AttachID,
        Blackhole=False,
        DryRun=False
        )
        logger.info(resp)
        return True
    except ClientError as error:
        if error.response['Error']['Code'] == 'AssociationAlreadyExists':
            resp = ec2.modify_transit_gateway_prefix_list_reference(
                TransitGatewayRouteTableId=tgwRtId,
                PrefixListId=PlId,
                TransitGatewayAttachmentId=AttachID,
                Blackhole=False,
                DryRun=False
            )
            logger.info(resp)
        else:
            logger.error(error)
