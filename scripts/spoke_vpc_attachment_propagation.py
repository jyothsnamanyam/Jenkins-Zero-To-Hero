



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
from assume_roles import role_arn, rcc_auto_session, rcc_session, target_session, bst_onedesign_session
from dynamodb import get_all_by_scan
from multiprocessing import Pool
from vpc_services import *
#from tst_tgw_constants import DYNAMODB_TABLE_PROPAGATE_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS
from gb_tgw_constants import DYNAMODB_TABLE_PROPAGATE_DATA, ON_PREM_CIDRS_ENTRIES, SAME_CROSS_CIDRS_ENTRIES, TGW_CONSTANTS
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


def get_attachments_rt_ids(environ_type, region, table_name):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    akeys = "tgw_attachmentId, tgw_propagate_rt_ids"
    response = table.scan(
        ProjectionExpression=akeys
    )
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])
    ###returning the data.
    return data


def create_tgw_route_table_propagation(region, tgwRtId, tgwAttId):
    ec2 = boto3.resource('ec2', region_name=region)
    ec2_client = ec2.meta.client
    try:
        resp = ec2_client.enable_transit_gateway_route_table_propagation(
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


def main(environment, region_name, attach_date):
    logger.info("Propagating spoke vpc attachments")
    table_name = f"{DYNAMODB_TABLE_PROPAGATE_DATA}-{attach_date}"
    data = get_attachments_rt_ids(environment, region_name, table_name)
    if not data:
        logger.error("No attachment Ids found. Hence existing the job.")
        exit(1)
    else:
        logger.info("Attachment Ids found.")
        for attachment in data:
            logger.info(f"Spoke VPC attachment ID: {attachment['tgw_attachmentId']} and propagate route table IDs: {attachment['tgw_propagate_rt_ids']} ")
            logger.info(f"Propagating the TransitGateway VPC attachment {attachment['tgw_attachmentId']}")
            propagation_rt_list = attachment['tgw_propagate_rt_ids']
            for prt in propagation_rt_list:
                create_tgw_route_table_propagation(region_name, prt, attachment['tgw_attachmentId'])
            logger.info("TransitGateway VPC attachment propagated successfully.")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Propagation of Spoke vpc attachments.",
        epilog="python3 scripts/spoke_vpc_attachment_propagation.py --environment='TEST' --region_name='ap-northeast-1' --attach_date='05-May-2023'"
    )
    parser.add_argument('--environment',
                        required=False,
                        help='account environment type, Ex: TEST or GB')
    parser.add_argument('--region_name',
                        required=False,
                        help='aws region name, Ex:ap-northeast-1')
    parser.add_argument('--attach_date',
                        required=False,
                        help='Attach Date, Ex:05-May-2023')
    args = parser.parse_args()
    environment = args.environment
    region_name = args.region_name
    attach_date = args.attach_date
    # resp = main("TST", "ap-northeast-1")
    main(environment, region_name, attach_date)

