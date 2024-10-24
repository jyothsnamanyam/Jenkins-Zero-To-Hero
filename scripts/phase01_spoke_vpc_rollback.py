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
#from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES
from gb_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES
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
        logger.error("NO accounts data found. Hence existing the job.")
        exit(1)
    else:
        logger.info("Accounts data found.")
        for account in data:
            arn = role_arn(account['account_number'], account['account_name'])
            arn_list.append(arn)
        return arn_list


def check_and_delete_prefixlist_route(ec2, name, rt, DryRun=True):
    global pl_Id
    pl_Id = check_prefix_list(ec2, name)
    if pl_Id:
        logger.info(f"Prefix list {name} found, Hence deleting prefix list route.")
        delete_prefixList_route(ec2, pl_Id, rt, DryRun=DryRun)
    else:
        logger.info(f"Prefix list {name} not found.")




def internet_route(ec2, dmz_tgw, DryRun=None):
    ##Getting all vpcs routetable ids in that account by region.
    route_table_list = get_routetables(ec2)
    for route_table in route_table_list:
        ##replacing the default from DMZ TGW to ONE TGW.
        logger.info(f"Updating the Route Table: {route_table}")
        replace_route_one_tgw(ec2, route_table, dmz_tgw, DryRun=DryRun)
        ##delete the on prem prefix list route
        check_and_delete_prefixlist_route(ec2, "on_prem_cidrs", route_table, DryRun=DryRun)
        ##delete the same and cross prefix route
        check_and_delete_prefixlist_route(ec2, "same_cross_cidrs", route_table, DryRun=DryRun)


def intranet_route(ec2, bst_tgw, DryRun=None):
    ##Creating the same and cross prefix list
    #regions_pl_id = create_prefix_list(ec2, "same_cross_cidrs", cidrEntries, DryRun=DryRun)
    ##Getting all vpcs routetable ids in that account by region.
    route_table_list = get_routetables(ec2)
    for route_table in route_table_list:
        ##Creating the same and cross prefix route
        ##replacing the default from BST TGW to ONE TGW.
        logger.info(f"Updating the Route Table: {route_table}")
        replace_route_one_tgw(ec2, route_table, bst_tgw, DryRun=DryRun)
        check_and_delete_prefixlist_route(ec2, "same_cross_cidrs", route_table, DryRun=DryRun)


def isolated_route(ec2, dmz_tgw, DryRun=None):
    ##Getting all vpcs routetable ids in that account by region.
    route_table_list = get_routetables(ec2)
    ##Checking replace route permission
    for route_table in route_table_list:
        ##replacing the default from DMZ TGW to ONE TGW.
        logger.info(f"Updating the Route Table: {route_table}")
        replace_route_one_tgw(ec2, route_table, dmz_tgw, DryRun=DryRun)


def spoke_account_route_create(account_type, sts, arn, region_name, bst_tgw, dmz_tgw, DryRun):
    if account_type == "INTRANET":
        target_account_session = target_session(sts, arn)
        ec2 = target_account_session.client("ec2", region_name)
        intranet_route(ec2, bst_tgw, DryRun=DryRun)
    elif account_type == "INTERNET":
        target_account_session = target_session(sts, arn)
        ec2 = target_account_session.client("ec2", region_name)
        internet_route(ec2, dmz_tgw, DryRun=DryRun)
    elif account_type == "ISOLATED":
        target_account_session = target_session(sts, arn)
        ec2 = target_account_session.client("ec2", region_name)
        isolated_route(ec2, dmz_tgw, DryRun=DryRun)
    else:
        logger.error(f"{account_type} was not found.")



######
def main(env_type, region_name, account_type, access_type):
    global pl_id
    if env_type == "PROD":
        from gb_tgw_constants import TGW_CONSTANTS, DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES
    else:
        from tst_tgw_constants import TGW_CONSTANTS, DYNAMODB_TABLE_ACCOUNT_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES

    ONE_TGW = TGW_CONSTANTS[region_name]['one_tgw']
    BST_TGW = TGW_CONSTANTS[region_name]['bst_tgw']
    DMZ_TGW = TGW_CONSTANTS[region_name]['dmz_tgw']
    ####

    arn_data = get_accounts_by_type(env_type, region_name, account_type)
    # arn_data = [
    #     "866919043554",
    #     # "720243969453",
    # ]
    # """
    ###Base seesion
    if access_type == "IDY_ROLE_KEYS":
        sts = idy_jit_session(environ['SPOKE_idy_accessKeyId'], environ['SPOKE_idy_secretAccessKey'],
                              environ['SPOKE_idy_sessionToken'], region_name)
        # arn = "arn:aws:iam::866919043554:role/RIDY_AWS_AWSGLOBALJIT01"
        # logger.info(f"Create Routing rules in Account: {arn}")
        # spoke_account_route_create(account_type, sts, arn, region_name, ONE_TGW, DryRun=False)
        #"""
        arn_list = list()
        for account in arn_data:
            role_arn = "".join(
                ('arn:aws:iam::', account['account_number'], ':role/', environ['SPOKE_idy_role_name']))
            arn_list.append(role_arn)
        ######
        for arn in arn_list:
            logger.info(f"Create Routing rules in Account: {arn}")
            spoke_account_route_create(account_type, sts, arn, region_name, BST_TGW, DMZ_TGW, DryRun=False)
            # Thread(target=spoke_account_route_create, args=(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, SAME_CROSS_CIDRS_ENTRIES[region_name] )).start()
        #"""
    else:
        arn_list = role_arn_list(arn_data)
        base_session = rcc_auto_session(env_type)
        sts = base_session.client('sts')
        # arn = "arn:aws:iam::501152149066:role/RRSITST_AWS_AUTOTST_ADM"
        for arn in arn_list:
            logger.info(f"Create Routing rules in Account: {arn}")
            spoke_account_route_create(account_type, sts, arn, region_name, BST_TGW, DMZ_TGW, DryRun=True)
            # Thread(target=spoke_account_route_create, args=(account_type, sts, arn, region_name, ONE_TGW, DMZ_TGW, SAME_CROSS_CIDRS_ENTRIES[region_name] )).start()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add routing resources",
        epilog="python3 scripts/phase01_spoke_vpc_rollback.py --env_type='TEST' --region_name='ap-northeast-1' --account_type='INTRANET' --access_type='IDY_ROLE_KEYS'"
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
    #main("TEST", "ap-northeast-1", , "INTERNET")





