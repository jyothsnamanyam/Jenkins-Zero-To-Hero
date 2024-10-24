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
import decimal
import argparse
import json
import sys
import time
import datetime
from os import environ
import os.path
import logging
import logging.handlers
import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore
from botocore.exceptions import ClientError


###local imports

##setting logs
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

##env and region specific TGW RAM shares arns.

# with open('config.json') as defaults:
#     data = json.load(defaults)


def create_table_with_hash_range_keys(dynamodb, table_name, hash_key, range_key):
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": hash_key,
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": range_key,
                    "KeyType": "RANGE"
                },
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": hash_key,
                    "AttributeType": "S"
                },
                {
                    "AttributeName": range_key,
                    "AttributeType": "S"
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10
            }
        )
        print(table)
        # Wait until the table exists.
        table.wait_until_exists()
    except ClientError as err:
        if err.response['Error']['Code'] == "ResourceInUseException":
            logger.info(err.response['Error']['Message'])
        else:
            logger.error(
                "Couldn't create table %s. Here's why: %s: %s", table_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
    else:
        return table


def create_table_with_hashKey(dynamodb, table_name, hash_key):
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": hash_key,
                    "KeyType": "HASH"
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": hash_key,
                    "AttributeType": "S"
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10
            }
        )
        print(table)
        # Wait until the table exists.
        table.wait_until_exists()
    except ClientError as err:
        if err.response['Error']['Code'] == "ResourceInUseException":
            logger.info(err.response['Error']['Message'])
        else:
            logger.error(
                "Couldn't create table %s. Here's why: %s: %s", table_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
    else:
        return table

##add_item structure
def lambda_put_item(account_number, vpc_id, account_name, account_type, environment, tag_name, tgw_associate_rt_id, tgw_propagate_rt_ids, TransitGatewayAttachmentId, SubnetIds):
    dynamo_put_item = {
      "account_number": "{}".format(account_number),
      "vpc_id": "{}".format(vpc_id),
      "account_name": "{}".format(account_name),
      "account_type": "{}".format(account_type),
      "environment": "{}".format(environment),
      "tag_name": "{}".format(tag_name),
      "tgw_associate_rt_id": "{}".format(tgw_associate_rt_id),
      "tgw_propagate_rt_ids": tgw_propagate_rt_ids,
      "tgw_attachmentId": "{}".format(TransitGatewayAttachmentId),
      "subnetIds": SubnetIds
    }
    return dynamo_put_item


##add_item structure
def propagate_lambda_put_item(TransitGatewayAttachmentId, account_number, tgw_propagate_rt_ids):
    dynamo_put_item = {
      "tgw_attachmentId": "{}".format(TransitGatewayAttachmentId),
      "account_number": "{}".format(account_number),
      "tgw_propagate_rt_ids": tgw_propagate_rt_ids
    }
    return dynamo_put_item

##add_item structure
def account_add_item(account_number, account_name, account_type, environment, tgw_associate_rt_id, tgw_propagate_rt_ids):
    dynamo_put_item = {
      "account_number": "{}".format(account_number),
      "account_name": "{}".format(account_name),
      "account_type": "{}".format(account_type),
      "environment": "{}".format(environment),
      "tgw_associate_rt_id": "{}".format(tgw_associate_rt_id),
      "tgw_propagate_rt_ids": tgw_propagate_rt_ids
    }
    return dynamo_put_item

#add single item to dynamodb.
def add_item(dynamodb, table_name, item):
    table = dynamodb.Table(table_name)
    try:
        table.put_item(
            Item=item
        )
    except ClientError as err:
        logger.error(
            "Couldn't add to  table %s. Here's why: %s: %s", table_name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise


#add batch items to dynamodb.
def batch_items(dynamodb, table_name, item_list):
    table = dynamodb.Table(table_name)
    try:
        with table.batch_writer() as writer:
            for item in item_list:
                writer.put_item(Item=item)
    except ClientError as err:
        logger.error(
            "Couldn't load data into table %s. Here's why: %s: %s", table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise


#get single item to dynamodb.
def get_item(dynamodb, table_name, account_number):
    table = dynamodb.Table(table_name)
    try:
        response = table.get_item(Key={'account_number': account_number})
    except ClientError as err:
        logger.error(
            "Couldn't get account %s from table %s. Here's why: %s: %s",
            account_number, table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response['Item']


#update single item with multiple values to dynamodb.
def update_item(dynamodb, table_name, account_number, attachId, vpcid, subnetIds):
    table = dynamodb.Table(table_name)
    try:
        response = table.update_item(
            Key={'account_number': account_number},
            UpdateExpression="set #tathId = :tathIdVal, #vId = :vIdVal, #subIds = :subIdVal",
            ExpressionAttributeNames={
                "#tathId": "TransitGatewayAttachmentId",
                "#vId": "VpcId",
                "#subIds": "TGWAttachSubnetIds"
            },
            ExpressionAttributeValues={
                ":tathIdVal": attachId,
                ":vIdVal": vpcid,
                ":subIdVal": subnetIds
            },
            ReturnValues="UPDATED_NEW")
    except ClientError as err:
        logger.error(
            "Couldn't update data %s in table %s. Here's why: %s: %s",
             table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response['Attributes']


#add or update tag to dynamodb.
def update_tag_item(dynamodb, table_name, account_number, tag_name):
    table = dynamodb.Table(table_name)
    try:
        response = table.update_item(
            Key={'account_number': account_number},
            UpdateExpression="set #tgname = :tgVal",
            ExpressionAttributeNames={
                "#tgname": "tag_name"
            },
            ExpressionAttributeValues={
                ":tgVal": tag_name
            },
            ReturnValues="UPDATED_NEW")
    except ClientError as err:
        logger.error(
            "Couldn't update data %s in table %s. Here's why: %s: %s",
             table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response['Attributes']


def get_all(dynamodb, batch_keys):
    MAX_GET_SIZE = 100  # Amazon DynamoDB rejects a get batch larger than 100 items.
    """
    Gets a batch of items from Amazon DynamoDB. Batches can contain keys from
    more than one table.

    When Amazon DynamoDB cannot process all items in a batch, a set of unprocessed
    keys is returned. This function uses an exponential backoff algorithm to retry
    getting the unprocessed keys until all are retrieved or the specified
    number of tries is reached.

    :param batch_keys: The set of keys to retrieve. A batch can contain at most 100
                       keys. Otherwise, Amazon DynamoDB returns an error.
    :return: The dictionary of retrieved items grouped under their respective
             table names.
    """
    tries = 0
    max_tries = 5
    sleepy_time = 1  # Start with 1 second of sleep, then exponentially increase.
    retrieved = {key: [] for key in batch_keys}
    while tries < max_tries:
        response = dynamodb.batch_get_item(RequestItems=batch_keys)
        # Collect any retrieved items and retry unprocessed keys.
        for key in response.get('Responses', []):
            retrieved[key] += response['Responses'][key]
        unprocessed = response['UnprocessedKeys']
        if len(unprocessed) > 0:
            batch_keys = unprocessed
            unprocessed_count = sum(
                [len(batch_key['Keys']) for batch_key in batch_keys.values()])
            logger.info(
                "%s unprocessed keys returned. Sleep, then retry.",
                unprocessed_count)
            tries += 1
            if tries < max_tries:
                logger.info("Sleeping for %s seconds.", sleepy_time)
                time.sleep(sleepy_time)
                sleepy_time = min(sleepy_time * 2, 32)
        else:
            break

    return retrieved



def get_all_by_scan(dynamodb, table):
    items_list = list()
    paginator = dynamodb.get_paginator('scan')
    response_iterator = paginator.paginate(
        TableName=table,
        # AttributesToGet=[
        #     'string',
        # ],
        Select='ALL_ATTRIBUTES',
    )
    for page in response_iterator:
        for item in page["Items"]:
            items_list.append(item)
    return items_list




# dynamodb_item = {'account_name': 'RSB', 'TransitGatewayAttachmentId': 'tgw-attach-0fa318b76fd0781a7', 'associate_table_id': 'tgw-rtb-02d3e41a85947f450', 'egress_propagation_table_id': 'tgw-rtb-0eab41fa0eec8415a', 'VpcId': 'vpc-01faf4f593c4e5b15', 'env_type': 'DEV', 'account_number': '082449889088', 'TGWAttachSubnetIds': ['subnet-036b4dcb19364b32c', 'subnet-072437974850d016e'], 'tag_name': 'RSB-DEV', 'zone_type': 'INTRACONN'}
# print("{}-{}-{}".format(dynamodb_item['account_name'], dynamodb_item['env_type'], dynamodb_item['VpcId'] ))




