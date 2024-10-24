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


import sys
import time
import os.path
import logging
import logging.handlers
import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore
from botocore.exceptions import ClientError


######## BOTO3 Clients and Resources #############
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
asg = boto3.client('autoscaling')
ec2 = boto3.resource('ec2')
ec2_client = ec2.meta.client
lambda_client = boto3.client('lambda')
iam = boto3.client('iam')
events_client = boto3.client('events')
cloudwatch = boto3.client('cloudwatch')


######## log settings #############
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


####### GLobal Variables ############
# TGWId="tgw-0d8757ce3dce60396"
#table_name = "NVSGISBSTGB-ONE-DESIGN-DATA"
DYNAMODB_TABLE_ONE_DESIGN = "NVSGISBSTGB-ONE-DESIGN-MIGRATION-DATA"
DYNAMODB_TABLE_PROPAGATE_DATA = "NVSGISBSTGB-ONE-DESIGN-PROPAGATE"
error_line="--------ERROR------ERROR-----ERROR------ERROR-------"


############# Write functions from here #############

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


#add single item to dynamodb.
def add_item(dynamodb, table_name, item):
    table = dynamodb.Table(table_name)
    try:
        table.put_item(
            Item=item
        )
    except ClientError as err:
        logging.warning(error_line)
        logger.error(
            "Couldn't add  data to table %s. Here's why: %s: %s", table_name,
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
        logging.warning(error_line)
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
        logging.warning(error_line)
        logger.error(
            "Couldn't get account %s from table %s. Here's why: %s: %s",
            account_number, table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response['Item']

###
##lambda structure
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


##propagate structure
def propagate_lambda_put_item(TransitGatewayAttachmentId, account_number, account_name, tgw_propagate_rt_ids):
    dynamo_put_item = {
      "tgw_attachmentId": "{}".format(TransitGatewayAttachmentId),
      "account_number": "{}".format(account_number),
      "account_name": "{}".format(account_name),
      "tgw_propagate_rt_ids": tgw_propagate_rt_ids
    }
    return dynamo_put_item

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
        logging.warning(error_line)
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
        logging.warning(error_line)
        logger.error(
            "Couldn't update data %s in table %s. Here's why: %s: %s",
             table.name,
            err.response['Error']['Code'], err.response['Error']['Message'])
        raise
    else:
        return response['Attributes']


def get_tgw_vpc_attachments(tgw_id):
    tgw_vpc_attach_list = list()
    try:
        paginator = ec2_client.get_paginator('describe_transit_gateway_vpc_attachments')
        response_iterator = paginator.paginate(
            Filters=[
                {
                    'Name': 'transit-gateway-id',
                    'Values': [tgw_id]
                },
                {
                    'Name': 'state',
                    'Values': ['pendingAcceptance']
                },
            ],
            DryRun=False,
            PaginationConfig={
                'MaxItems': 200,
                'PageSize': 200
            }
        )
        for page in response_iterator:
            for tgw_vpc_attach in page['TransitGatewayVpcAttachments']:
                tgw_vpc_attach_list.append(tgw_vpc_attach)
        if not tgw_vpc_attach_list:
            # logging.warning(error_line)
            # logger.info("No vpc pending attachment found in TGW %s" % tgw_id)
            return None
        return tgw_vpc_attach_list
    except Exception as e:
        logging.warning(error_line)
        logger.exception("[Error while getting the TransitGateway Vpc Attachments,]: {}".format(e))


def accept_transit_gateway_vpc_attachment(tgwAtchID):
    resp = ec2_client.accept_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=tgwAtchID
    )


def status_of_vpc_attachment(tgwAtchID):
    res = ec2_client.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[
            tgwAtchID,
        ],
        DryRun=False
    )
    state = res['TransitGatewayVpcAttachments'][0]['State']
    account_number = res['TransitGatewayVpcAttachments'][0]['VpcOwnerId']
    return state, account_number


def create_tgw_route_table_associations(tgwRtId, tgwAttId):
    try:
        resp = ec2_client.associate_transit_gateway_route_table(
        TransitGatewayRouteTableId=tgwRtId,
        TransitGatewayAttachmentId=tgwAttId
        )
        #logger.info(resp['Association'])
        return resp['Association']['State']
    except ClientError as error:
        if error.response['Error']['Code'] == 'Resource.AlreadyAssociated':
            return "AlreadyAssociated"
        else:
            logging.warning(error_line)
            logger.info(error)


def create_tgw_route_table_propagation(tgwRtId, tgwAttId):
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
            logging.warning(error_line)
            logger.info(error)


def tag_Tgwattch(tgwAtId, name):
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

###Lambda

def lambda_handler(event, context):
    """
        This function performs the following actions:
        get_tgw_vpc_attachments(TGWId)
        accept_transit_gateway_vpc_attachment(request['TransitGatewayAttachmentId'])
        update_item(dynamodb, table_name, request['VpcOwnerId'], request['TransitGatewayAttachmentId'], request['VpcId'], request['SubnetIds'])
        create_tgw_route_table_associations(dynamodb_item['associate_table_id'], attch_id)
         tag_Tgwattch(attch_id, tag_name)
        :param event: Encodes all the input variables to the lambda function, when
                      the function is invoked.
                      Essentially AWS Lambda uses this parameter to pass in event
                      data to the handler function.
        :type event: dict
        :param context: AWS Lambda uses this parameter to provide runtime information to your handler.
        :type context: LambdaContext
        :return: None
        """
    logger.info('got event{}'.format(event))


    TGWId = event['TGWId']
    logger.info(f"Transit Gateway ID: {TGWId}")

    table_name = event['DynamodbTable']
    logger.info(f"Dynamo DB Table Name: {table_name}")


    vLocalTimeZone = 'Asia/Kolkata'
    # vNowUTC = time.strftime("%Y-%m-%d %H:%M:%S.%f")
    # print("UTC time", vNowUTC)
    os.environ['TZ'] = vLocalTimeZone
    time.tzset()
    # vNowlocal = time.strftime("%Y-%m-%d %H:%M:%S.%f")
    # print("Local time",vNowlocal)
    vLocalDate = time.strftime("%d-%b-%Y")
    logger.info(f"Current date: {vLocalDate}")

    propagate_table_name = f"{DYNAMODB_TABLE_PROPAGATE_DATA}-{vLocalDate}"
    logger.info(f" Propagation table name: {propagate_table_name}")
    create_table_with_hashKey(dynamodb, propagate_table_name, "tgw_attachmentId")

    ##List of accepted tgw attachment ids.
    accepted_tgw_vpc_attach_list = list()
    dynamodb_batch_item = list()
    dy_propagate_batch_item = list()

    logger.info("Getting all TransitGateway VPC pending attachments.")
    pending_attach_list = get_tgw_vpc_attachments(TGWId)
    #Run only after list True.
    if pending_attach_list:
        logger.info(f"There are total {len(pending_attach_list)} TransitGateway VPC attachment requests are pending.")
        logger.info(f"Performing TransitGateway VPC attachment request acceptance and associating. ")
        for request in pending_attach_list:
            logger.info(f"Accepting the {request['VpcOwnerId']} account TransitGateway VPC attachment Id: {request['TransitGatewayAttachmentId']}")
            accept_transit_gateway_vpc_attachment(request['TransitGatewayAttachmentId'])
            accepted_tgw_vpc_attach_list.append(request['TransitGatewayAttachmentId'])
            logger.info("Getting data from  DynamoDB.")
            dynamodb_item = get_item(dynamodb, table_name, request['VpcOwnerId'])
            logger.info("Updating following TransitGateway VPC  attachments details in DynamoDB.")
            logger.info(f"Spoke VPC Id: {request['VpcId']}")
            logger.info(f"Spoke VPC Subnets: {request['SubnetIds']}")
            logger.info(f"Spoke VPC Attachment ID: {request['TransitGatewayAttachmentId']}")
            tag_name = "{}-{}-{}".format(dynamodb_item['account_name'], dynamodb_item['environment'], request['VpcId'])
            logger.info(f"TransitGateway VPC attachment TAG Name {tag_name} Updating.")
            tag_Tgwattch(request['TransitGatewayAttachmentId'], tag_name)
            dydb_item = lambda_put_item(dynamodb_item['account_number'], request['VpcId'], dynamodb_item['account_name'], dynamodb_item['account_type'], dynamodb_item['environment'], tag_name, dynamodb_item['tgw_associate_rt_id'],
                                        dynamodb_item['tgw_propagate_rt_ids'], request['TransitGatewayAttachmentId'], request['SubnetIds'])
            #print(dydb_item)
            dynamodb_batch_item.append(dydb_item)
            #####Updating Progate DB with Attachment Id and Propagation table IDs
            pdb_item = propagate_lambda_put_item(request['TransitGatewayAttachmentId'], dynamodb_item['account_number'], dynamodb_item['account_name'], dynamodb_item['tgw_propagate_rt_ids'])
            dy_propagate_batch_item.append(pdb_item)
        logger.info("Adding Spoke account details in DynamoDB.")
        batch_items(dynamodb, DYNAMODB_TABLE_ONE_DESIGN, dynamodb_batch_item)
        logger.info("Adding Spoke account Attachment Id and Propagation table IDs in DynamoDB for future operations.")
        batch_items(dynamodb, propagate_table_name, dy_propagate_batch_item)

        ##
        if len(accepted_tgw_vpc_attach_list) != 0:
            for attch_id in accepted_tgw_vpc_attach_list:
                cnt = 0
                while cnt < 20:
                    logger.info("Checking the TransitGateway VPC attachment status.")
                    state, account_number = status_of_vpc_attachment(attch_id)
                    if state == "available": #"pendingAcceptance":
                        logger.info(f"TransitGateway VPC attachment {attch_id} status is available.")
                        dynamodb_item = get_item(dynamodb, table_name, account_number)
                        logger.info(
                            f"Associating the TransitGateway VPC attachment {attch_id} with TransitGateway route table ID: {dynamodb_item['tgw_associate_rt_id']}.")
                        create_tgw_route_table_associations(dynamodb_item['tgw_associate_rt_id'], attch_id)
                        logger.info("TransitGateway VPC attachment request was accepted and associated successfully.")
                        #####propagation logic for all time.##Should be commnted for migration.
                        # logger.info(f"Propagating the TransitGateway VPC attachment {attch_id}")
                        # propagation_rt_list = dynamodb_item['tgw_propagate_rt_ids']
                        # for prt in propagation_rt_list:
                        #     create_tgw_route_table_propagation(prt, attch_id)
                        # logger.info("TransitGateway VPC attachment propagated successfully.")
                        break
                    logger.info(f"{cnt} -- Waiting for attachment should be at Available State...")
                    cnt += 1
                    time.sleep(10)
                ##
            ##

        else:
            logger.warning("There is no accepted TransitGateway VPC attachments to associate with TransitGateway route table.")
    else:
        logger.info("No vpc pending attachment found in TGW %s" % TGWId)
