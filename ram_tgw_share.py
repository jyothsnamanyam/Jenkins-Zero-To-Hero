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

import pandas as pd
import argparse
import json
import sys
import time
from datetime import datetime
import os.path
import logging
import logging.handlers
import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore
from botocore.exceptions import ClientError
from os import environ
import typing as t
from gb_tgw_constants import TGW_CONSTANTS, DYNAMODB_TABLE_ACCOUNT_DATA,  DYNAMODB_TABLE_ONE_DESIGN
#from tst_tgw_constants import TGW_CONSTANTS, DYNAMODB_TABLE_ACCOUNT_DATA,  DYNAMODB_TABLE_ONE_DESIGN
###local imports
from dynamodb import *

##setting logs
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

##env and region specific TGW RAM shares arns.

# with open('raw_data/config.json') as defaults:
#     data = json.load(defaults)
#from tst_tgw_constants import  DYNAMODB_TABLE_ACCOUNT_DATA,  DYNAMODB_TABLE_ONE_DESIGN
#from assume_roles import role_arn, rcc_auto_session, rcc_session, target_session, bst_onedesign_session

def get_today_date():
    """
    Get always execution date.
    date format is DD-shortNameofMonth-year Ex: 02-May-2023
    :return: date
    """
    executed_date = datetime.now()
    # print(executed_date.strftime("%d-%b-%Y"))
    return executed_date.strftime("%d-%b-%Y")


##get the list of shared aws account numbers.
def get_ram_share_principals(client, rSArn):
    principals = []
    paginator = client.get_paginator('list_principals')
    response_iterator = paginator.paginate(
        resourceOwner='SELF',
        resourceShareArns=[
            rSArn,
        ],
        PaginationConfig={
            'MaxItems': 100,
            'PageSize': 100
        }
    )
    for page in response_iterator:
        for principal in page['principals']:
            principals.append(principal['id'])
    return principals


#get the list of aws account associations
def get_resource_share_associations(client, rSArn):
    associations_list = []
    paginator = client.get_paginator('get_resource_share_associations')
    response_iterator = paginator.paginate(
        associationType='PRINCIPAL',
        resourceShareArns=[
            rSArn
        ]
    )
    associations_list.clear()
    for page in response_iterator:
        for association in page['resourceShareAssociations']:
            dummy_dict = dict()
            # print(association)
            dummy_dict['account_number'] = association['associatedEntity']
            dummy_dict['status'] = association['status']
            # print(dummy_dict)
            associations_list.append(dummy_dict)
    # print(associations_list)
    return associations_list


#do share the tgw with list of aws account numbers.
def associate_aws_accounts(client, rSArn, accoutIds_list):
    resp = client.associate_resource_share(
        resourceShareArn=rSArn,
        principals=accoutIds_list
    )
    return resp['resourceShareAssociations']


##main program.
def main(env_type, region_name):
    ######global variabls#####
    # boto3 = bst_onedesign_session(env_type)
    if env_type == "PROD":
        from gb_tgw_constants import TGW_CONSTANTS, DYNAMODB_TABLE_ACCOUNT_DATA,  DYNAMODB_TABLE_ONE_DESIGN
    else:
        from tst_tgw_constants import TGW_CONSTANTS, DYNAMODB_TABLE_ACCOUNT_DATA,  DYNAMODB_TABLE_ONE_DESIGN

    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    ram = boto3.client('ram', region_name=region_name)
    table_name = DYNAMODB_TABLE_ACCOUNT_DATA
    create_table_with_hashKey(dynamodb, table_name, "account_number")
    create_table_with_hash_range_keys(dynamodb, DYNAMODB_TABLE_ONE_DESIGN, "account_number", "vpc_id")
    aws_account_list = list()
    dynamodb_item_list = list()
    ram_share_arn = TGW_CONSTANTS[region_name]['resource_share_arn']
    if env_type == "TEST":
        ram_share_data = "raw_data/ram_share.xlsx"
    else:
        ram_share_data = "raw_data/prod_ram_share.xlsx"
    #ram_share_data = "../raw_data/ram_share.xlsx"

    ####Runner####
    if os.path.exists(ram_share_data):
        logger.info(f"Account Data from local excel file {ram_share_data}.")
        ram_share_df = pd.read_excel(
            ram_share_data,
            dtype={"account_number": "string"}
        )
        for row in ram_share_df.iterrows():
            account_number = row[1]['account_number']
            aws_account_list.append(account_number)
            account_name = row[1]['account_name']
            account_type = row[1]['account_type']
            environment = row[1]['environment']
            tgw_associate_rt_id = TGW_CONSTANTS[region_name][account_type]['association'][environment]
            tgw_propagate_rt_ids = TGW_CONSTANTS[region_name][account_type]['propagation'][environment]
            dydb_item = account_add_item(account_number, account_name, account_type, environment, tgw_associate_rt_id, tgw_propagate_rt_ids)
            dynamodb_item_list.append(dydb_item)
        # print(aws_account_list)
        # print(dynamodb_item_list)
        logger.info(
            f"Sharing the BST{env_type} transit gateway in {region_name} region with aws accounts {aws_account_list}")
        resource_share_associations = associate_aws_accounts(ram, ram_share_arn, aws_account_list)
        if resource_share_associations:
            logger.info("Sharing TransitGateway was successful.")
        logger.info("Adding the data to dynamodb for future operations.")
        batch_items(dynamodb, table_name, dynamodb_item_list)
    else:
        logger.info("Account Data from Jenkins form.")
        account_number = environ['account_number']
        account_name = environ['account_name']
        account_type = environ['account_type']
        environment = environ['environment']
        tgw_associate_rt_id = TGW_CONSTANTS[region_name][account_type]['association'][environment]
        tgw_propagate_rt_ids = TGW_CONSTANTS[region_name][account_type]['propagation'][environment]
        dydb_item = account_add_item(account_number, account_name, account_type, environment, tgw_associate_rt_id,
                                     tgw_propagate_rt_ids)
        logger.info(
            f"Sharing the BST{environment} transit gateway in {region_name} region with aws account {account_number}")
        resource_share_associations = associate_aws_accounts(ram, ram_share_arn, account_number)
        if resource_share_associations:
            logger.info("Sharing TransitGateway was successful.")
        logger.info("Adding the data to dynamodb for future operations.")
        add_item(dynamodb, table_name, dydb_item)
    ##
    logger.info("TGW RAM Share status")
    association_list = get_resource_share_associations(ram, ram_share_arn)
    df = pd.DataFrame(association_list)
    print(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RAM Share",
        epilog="python3 scripts/ram_tgw_share.py --env_type='TEST' --region_name='ap-northeast-1'"
    )
    parser.add_argument('--env_type',
                        required=False,
                        help='account environment type, Ex: TST or GB')
    parser.add_argument('--region_name',
                        required=False,
                        help='aws region name, Ex:ap-northeast-1')
    parser.add_argument('--aws_account_list',
                        required=False,
                        help='aws account number in list format and comma separated, Ex:ap-northeast-1')
    args = parser.parse_args()
    env_type = args.env_type
    region_name = args.region_name
    #resp = main("TST", "ap-northeast-1")
    main(env_type, region_name)