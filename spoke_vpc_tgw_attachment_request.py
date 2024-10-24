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
from assume_roles import role_arn, rcc_auto_session, rcc_session, target_session, bst_onedesign_session, idy_jit_session
from dynamodb import get_all_by_scan
from multiprocessing import Pool
from vpc_services import *
#from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS
from gb_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS
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


def get_accounts_by_type(environ_type, region, account_type):
    bst_session = bst_onedesign_session(environ_type)
    dynamodb = bst_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(DYNAMODB_TABLE_ACCOUNT_DATA)
    akeys = "account_number, account_name"
    response = table.scan(
        ProjectionExpression=akeys,
        FilterExpression=Attr('account_type').eq(account_type)
    )
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])
    ###returning the data.
    return data


def role_arn_list(data):
    arn_list = list()
    if not data:
        logger.error("No accounts data found. Hence existing the job.")
        exit(1)
    else:
        logger.info("Accounts data found.")
        for account in data:
            arn = role_arn(account['account_number'], account['account_name'])
            arn_list.append(arn)
        return arn_list


def tgw_vpc_attachment_request(ec2, one_tgw, vpcId, subnets):
    attach_tag = f"ONE-DESING-{vpcId}"
    resp = create_transit_gateway_spoke_vpc_attachment(ec2, one_tgw, vpcId, subnets, attach_tag)
    # if resp == "Created":
    if "tgw-attach" in resp:
        logger.info(f"TGW {one_tgw} and VPC {vpcId} Attachment was created successfully.")
    elif resp == "DuplicateTransitGatewayAttachment":
        logger.info(f"TGW {one_tgw} and VPC {vpcId} Attachment already existed.")
    else:
        logger.error(resp)


def internet_tgw_request(ec2, region_name, one_tgw, dmz_tgw):
    try:
        old_attach_list = check_existing_vpc_attachment(ec2, dmz_tgw)
        response = get_vpcs(ec2)
        if not old_attach_list:
            #print("Empty", old_attach_list)
            logger.info("Account has no TGW VPC attachments.")
            for vpc in response:
                subnets = list_subnets_by_azs(ec2, vpc['VpcId'], region_name)
                logger.info(f"Get random one subnet {subnets}per az of VPC {vpc['VpcId']}.")
                logger.info(f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with subnets {subnets} each one per AZ.")
                tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
        else:
            #print("Non Empty", old_attach_list)
            logger.info("Account has TGW VPC attachments.")
            for vpc in response:
                for vta in old_attach_list:
                    if vta['VpcId'] == vpc['VpcId']:
                        logger.info(f"VPC {vpc['VpcId']} has existing attachment, Hence getting the subnets from attachment.")
                        subnets = vta['SubnetIds']
                        logger.info(f"Subnets {subnets} from existing attachment.")
                        logger.info(
                            f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with existing subnets {subnets}.")
                        tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
                    else:
                        logger.info(f"VPC {vpc['VpcId']} has not existing attachment, Hence getting the new subnets from VPC.")
                        subnets = list_subnets_by_azs(ec2, vpc['VpcId'], region_name)
                        logger.info(f"Get random one subnet {subnets}per az of VPC {vpc['VpcId']}.")
                        logger.info(
                            f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with subnets {subnets} each one per AZ.")
                        tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
    except ClientError as error:
        logger.error(error)


def intranet_tgw_request(ec2, region_name, one_tgw, bst_tgw):
    ##Creating The Transit gateway VPC attachment creation.
    try:
        old_attach_list = check_existing_vpc_attachment(ec2, bst_tgw)
        response = get_vpcs(ec2)
        if not old_attach_list:
            # print("Empty", old_attach_list)
            logger.info("Account has no TGW VPC attachments.")
            for vpc in response:
                subnets = list_subnets_by_azs(ec2, vpc['VpcId'], region_name)
                logger.info(f"Get random one subnet {subnets}per az of VPC {vpc['VpcId']}.")
                logger.info(
                    f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with subnets {subnets} each one per AZ.")
                tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
        else:
            # print("Non Empty", old_attach_list)
            logger.info("Account has TGW VPC attachments.")
            for vpc in response:
                for vta in old_attach_list:
                    if vta['VpcId'] == vpc['VpcId']:
                        logger.info(
                            f"VPC {vpc['VpcId']} has existing attachment, Hence getting the subnets from attachment.")
                        subnets = vta['SubnetIds']
                        logger.info(f"Subnets {subnets} from existing attachment.")
                        logger.info(
                            f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with existing subnets {subnets}.")
                        tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
                    else:
                        logger.info(
                            f"VPC {vpc['VpcId']} has not existing attachment, Hence getting the new subnets from VPC.")
                        subnets = list_subnets_by_azs(ec2, vpc['VpcId'], region_name)
                        logger.info(f"Get random one subnet {subnets}per az of VPC {vpc['VpcId']}.")
                        logger.info(
                            f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with subnets {subnets} each one per AZ.")
                        tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
    except ClientError as error:
        logger.error(error)


def isolated_tgw_request(ec2, region_name, one_tgw, dmz_tgw):
    ##Creating The Transit gateway VPC attachment creation.
    try:
        old_attach_list = check_existing_vpc_attachment(ec2, dmz_tgw)
        response = get_vpcs(ec2)
        if not old_attach_list:
            # print("Empty", old_attach_list)
            logger.info("Account has no TGW VPC attachments.")
            for vpc in response:
                subnets = list_subnets_by_azs(ec2, vpc['VpcId'], region_name)
                logger.info(f"Get random one subnet {subnets}per az of VPC {vpc['VpcId']}.")
                logger.info(
                    f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with subnets {subnets} each one per AZ.")
                tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
        else:
            # print("Non Empty", old_attach_list)
            logger.info("Account has TGW VPC attachments.")
            for vpc in response:
                for vta in old_attach_list:
                    if vta['VpcId'] == vpc['VpcId']:
                        logger.info(
                            f"VPC {vpc['VpcId']} has existing attachment, Hence getting the subnets from attachment.")
                        subnets = vta['SubnetIds']
                        logger.info(f"Subnets {subnets} from existing attachment.")
                        logger.info(
                            f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with existing subnets {subnets}.")
                        tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
                    else:
                        logger.info(
                            f"VPC {vpc['VpcId']} has not existing attachment, Hence getting the new subnets from VPC.")
                        subnets = list_subnets_by_azs(ec2, vpc['VpcId'], region_name)
                        logger.info(f"Get random one subnet {subnets}per az of VPC {vpc['VpcId']}.")
                        logger.info(
                            f"Creating TGW {one_tgw} and VPC {vpc['VpcId']} Attachment with subnets {subnets} each one per AZ.")
                        tgw_vpc_attachment_request(ec2, one_tgw, vpc['VpcId'], subnets)
    except ClientError as error:
        logger.error(error)



def spoke_vpc_tgw_attach_request_create(account_type, sts, arn, region_name, one_tgw, dmz_tgw, bst_tgw):
    if account_type == "INTERNET":
        target_account_session = target_session(sts, arn)
        ec2 = target_account_session.client("ec2", region_name)
        internet_tgw_request(ec2, region_name, one_tgw, dmz_tgw)
    elif account_type == "INTRANET":
        target_account_session = target_session(sts, arn)
        ec2 = target_account_session.client("ec2", region_name)
        intranet_tgw_request(ec2, region_name, one_tgw, bst_tgw)
    elif account_type == "ISOLATED":
        target_account_session = target_session(sts, arn)
        ec2 = target_account_session.client("ec2", region_name)
        isolated_tgw_request(ec2, region_name, one_tgw, dmz_tgw)
    else:
        logger.error(f"{account_type} was not found.")
        exit(1)


######
def main(env_type, region_name, account_type, access_type):
    if env_type == "PROD":
        from gb_tgw_constants import TGW_CONSTANTS
    else:
        from tst_tgw_constants import TGW_CONSTANTS

    ONE_TGW = TGW_CONSTANTS[region_name]['one_tgw']
    BST_TGW = TGW_CONSTANTS[region_name]['bst_tgw']
    DMZ_TGW = TGW_CONSTANTS[region_name]['dmz_tgw']
    ###BST Session
    #get_account_list_dict(env_type, region_name)
    # arn_data = get_accounts_by_type(env_type, region_name, account_type)
    # arn_list = role_arn_list(arn_data)
    # #"""
    # ###Base seesion
    # base_session = rcc_auto_session(env_type)
    # sts = base_session.client('sts')
    # #arn = "arn:aws:iam::501152149066:role/RRSITST_AWS_AUTOTST_ADM"
    # for arn in arn_list:
    #     logger.info(f"Check and create TGW VPC Attachment  in Account: {arn}")
    #     spoke_vpc_tgw_attach_request_create(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, BST_TGW)
    #     #Thread(target=spoke_vpc_tgw_attach_request_create, args=(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, BST_TGW)).start()

    # get_account_list_dict(env_type, region_name)
    arn_data = get_accounts_by_type(env_type, region_name, account_type)
    # """
    ###Base seesion
    if access_type == "IDY_ROLE_KEYS":
        sts = idy_jit_session(environ['SPOKE_idy_accessKeyId'], environ['SPOKE_idy_secretAccessKey'],
                              environ['SPOKE_idy_sessionToken'], region_name)
        arn_list = list()
        for account in arn_data:
            role_arn = "".join(('arn:aws:iam::', account['account_number'], ':role/', environ['SPOKE_idy_role_name']))
            arn_list.append(role_arn)
        ######
        for arn in arn_list:
            logger.info(f"Check and create TGW VPC Attachment  in Account: {arn}")
            spoke_vpc_tgw_attach_request_create(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, BST_TGW)
            # Thread(target=spoke_vpc_tgw_attach_request_create, args=(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, BST_TGW)).start()
    else:
        arn_list = role_arn_list(arn_data)
        base_session = rcc_auto_session(env_type)
        sts = base_session.client('sts')
        # arn = "arn:aws:iam::501152149066:role/RRSITST_AWS_AUTOTST_ADM"
        for arn in arn_list:
            logger.info(f"Check and create TGW VPC Attachment in Account: {arn}")
            spoke_vpc_tgw_attach_request_create(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, BST_TGW)
            # Thread(target=spoke_vpc_tgw_attach_request_create, args=(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, BST_TGW)).start()

    #"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add routing resources",
        epilog="python3 scripts/spoke_account_create_route.py --env_type='TEST' --region_name='ap-northeast-1' --account_type='INTRANET' --access_type='IDY_ROLE_KEYS'"
    )
    parser.add_argument('--env_type',
                        required=False,
                        help='account environment type, Ex: TEST or PROD')
    parser.add_argument('--region_name',
                        required=False,
                        help='aws region name, Ex:ap-northeast-1')
    parser.add_argument('--account_type',
                        required=False,
                        help='accounts type')
    parser.add_argument('--access_type',
                        required=False,
                        help='access type')

    args = parser.parse_args()
    env_type = args.env_type
    region_name = args.region_name
    account_type = args.account_type
    access_type = args.access_type
    main(env_type, region_name, account_type, access_type)
    #main("TEST", "ap-northeast-1", "INTERNET")





