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
from threading import Thread
from datetime import datetime
from os import environ
from assume_roles import role_arn, rcc_auto_session, rcc_session, target_session, bst_onedesign_session
from tst_tgw_constants import DYNAMODB_TABLE_ACCOUNT_DATA
from dynamodb import get_all_by_scan
from get_services import get_vpcs
from multiprocessing import Pool

import logging
import logging.handlers

LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# region = environ['RegionName']
region = 'ap-northeast-1'

dynamodb_account_scan_data = list()


def get_today_date():
    """
    Get always execution date.
    date format is DD-shortNameofMonth-year Ex: 02-May-2023
    :return: date
    """
    executed_date = datetime.now()
    # print(executed_date.strftime("%d-%b-%Y"))
    return executed_date.strftime("%d-%b-%Y")

def get_account_list_dict(environ_type):
    bst_session = bst_onedesign_session(environ_type)
    dynamodb = bst_session.client('dynamodb', region_name=region)
    data = get_all_by_scan(dynamodb, DYNAMODB_TABLE_ACCOUNT_DATA)
    dynamodb_account_scan_data.clear()
    for item in data:
        dummy_dict = dict()
        dummy_dict['account_number'] = item['account_number']['S']
        dummy_dict['account_name'] = item['account_name']['S']
        dynamodb_account_scan_data.append(dummy_dict)
    print(dynamodb_account_scan_data)
    return dynamodb_account_scan_data


def role_arn_list(environ_type):
    data = get_account_list_dict(environ_type)
    arn_list = list()
    for account in data:
        arn = role_arn(account['account_number'], account['account_name'])
        arn_list.append(arn)
    return arn_list


def print_vpcs(sts, arn):
    target_account_session = target_session(sts, arn)
    ec2_client = target_account_session.client("ec2", region)
    response = get_vpcs(ec2_client)
    print(response)


######

#def main(region, env_type, account_number, account_name):
def main(env_type):
    base_session = rcc_auto_session(env_type)
    sts = base_session.client('sts')
    arn_list = role_arn_list(env_type)
    for arn in arn_list:
        print(arn)
        # print_vpcs(sts, arn)
        Thread(target=print_vpcs, args=(sts, arn)).start()

    # for i in range(5):
    #         Thread(target=f, args=(i,)).start()


if __name__ == "__main__":
    #regions = ["ap-northeast-1", "eu-central-1", "eu-west-1", "us-east-1"]
    # main("ap-northeast-1", "TST", "082449889088", "RSBTST")
    main( "TST")







