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
import json
import sys
import time
import datetime
import os.path
import logging
import logging.handlers
import boto3
from boto3.dynamodb.conditions import Key, Attr
import botocore
from botocore.exceptions import ClientError
import io
from zipfile import ZipFile
import os

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


####
regionName = environ['RegionName']
lambda_client = boto3.client('lambda', region_name=regionName)
iam = boto3.client('iam')
events_client = boto3.client('events', region_name=regionName)

##env and region specific TGW RAM shares arns.

with open('raw_data/config.json') as defaults:
    data = json.load(defaults)


##################################Lambda######



def create_iam_role(role_name):
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy))
        logger.info(f"Created role {role['Role']['RoleName']}")
    except ClientError as error:
        if error.response['Error']['Code'] == 'EntityAlreadyExists':
            logger.info(f"Role {role_name} Already Exists.")
        else:
            logger.exception(f"Couldn't create role {role_name}")
            raise
    else:
        return role['Role']['Arn']


def get_role_arn(name):
    res = iam.get_role(
        RoleName=name
    )
    print(res)
    return res['Role']['Arn']


def create_policy(name):
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "iam:UpdateAssumeRolePolicy",
                    "iam:GetRole",
                    "iam:PassRole",
                    "iam:CreateServiceLinkedRole"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "ec2:CreateTags",
                    "ec2:AssociateTransitGatewayRouteTable",
                    "ec2:AcceptTransitGatewayVpcAttachment",
                    "ec2:EnableTransitGatewayRouteTablePropagation",
                    "ec2:DescribeTransitGatewayAttachments",
                    "ec2:DescribeTransitGatewayRouteTables",
                    "ec2:DescribeTags",
                    "ec2:DescribeVpcs",
                    "ec2:GetTransitGatewayRouteTablePropagations",
                    "ec2:DescribeRegions",
                    "ec2:GetTransitGatewayAttachmentPropagations",
                    "ec2:DescribeTransitGateways",
                    "ec2:DescribeTransitGatewayVpcAttachments",
                    "ec2:DescribeSubnets",
                    "ec2:GetTransitGatewayRouteTableAssociations"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "events:*"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "cloudwatch:*"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "lambda:AddPermission",
                    "lambda:CreateEventSourceMapping",
                    "lambda:CreateFunction",
                    "lambda:DeleteEventSourceMapping",
                    "lambda:DeleteFunction",
                    "lambda:GetEventSourceMapping",
                    "lambda:ListEventSourceMappings",
                    "lambda:RemovePermission",
                    "lambda:UpdateEventSourceMapping",
                    "lambda:UpdateFunctionCode",
                    "lambda:UpdateFunctionConfiguration",
                    "lambda:GetFunction",
                    "lambda:ListFunctions"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "sqs:ReceiveMessage",
                    "sqs:SendMessage",
                    "sqs:SetQueueAttributes",
                    "sqs:PurgeQueue",
                    "sqs:DeleteMessage"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*",
                "Effect": "Allow"
            },
            {
                "Action": [
                    "cloudformation:DescribeStacks"
                ],
                "Resource": "*",
                "Effect": "Allow"
            },
            {
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutDestination",
                    "logs:PutDestinationPolicy",
                    "logs:PutLogEvents",
                    "logs:PutMetricFilter"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": "dynamodb:*",
                "Resource": "arn:aws:dynamodb:*:*:*",
                "Effect": "Allow"
            }
        ]
    }
    try:
        policy = iam.create_policy(
            PolicyName=name, Description="TGW VPC Lambda policy",
            PolicyDocument=json.dumps(policy_doc))
        logger.info(f"Created policy {policy['Policy']['Arn']}.")
    except ClientError:
        logger.exception(f"Couldn't create policy {name}" )
        raise
    else:
        return policy['Policy']['Arn']


def attach_to_role(role_name, policy_arn):
    try:
        res = iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        logger.info("Attached policy %s to role %s.", policy_arn, role_name)
    except ClientError:
        logger.exception("Couldn't attach policy %s to role %s.", policy_arn, role_name)
        raise
    else:
        print(res)

#####Lamda Codes######
def files_to_zip(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root, f)
            archive_name = full_path[len(path) + len(os.sep):]
            yield full_path, archive_name


def make_zip_file(path):
    zip_name = "code.zip"
    with ZipFile(zip_name, 'w') as z:
        for full_path, archive_name in files_to_zip(path=path):
            z.write(full_path, archive_name)
    return zip_name


def create_schedule_tgw_lambda(lambda_func_name, lambda_role_arn, transitgatewayId, dynamodbTable):
    """
    Create the sched_tgw2 function, responsible for polling TGW
    attachments for spoke VPCs.

    :param event:
    :return:
    """
    event_rule_name = "{}-rule".format(lambda_func_name)
    logger.info('Creating event rule: ' + event_rule_name)
    response = events_client.put_rule(
            Name=event_rule_name,
            ScheduleExpression='rate(2 minutes)',
            State='ENABLED'
        )
    events_source_arn = response.get('RuleArn')

    logger.info(f'Creating Lambda function zip file...')
    lambda_code_path = "lambda_code"
    make_zip_file(lambda_code_path)
    with open("code.zip", 'rb') as f:
        zipped_code = f.read()
    ##local path of lambda code
    logger.info(f'Creating Lambda function ...')
    response = lambda_client.create_function(
            FunctionName=lambda_func_name,
            Runtime='python3.9',
            Role=lambda_role_arn,
            Handler='spoke_vpc_attachment.lambda_handler',
            # Code={
            #     'ZipFile': zipped_code
            # },
            Code=dict(ZipFile=zipped_code),
            Timeout=300
        )

    logger.info(f'Lambda function {lambda_func_name} created...')
    sched_evt_lambda_arn = response.get('FunctionArn')

    response = lambda_client.add_permission(
            FunctionName=sched_evt_lambda_arn,
            StatementId= lambda_func_name,
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=events_source_arn
        )

    logger.info('Event put targets')

    Input = {
             'TGWId' : transitgatewayId,
             'DynamodbTable' : dynamodbTable

             }

    target_id_name = lambda_func_name
    response = events_client.put_targets(
        Rule=event_rule_name,
        Targets=
        [{
            'Id': target_id_name,
            'Arn': sched_evt_lambda_arn,
            'Input': json.dumps(Input)
        }]
    )


def make_zip_file_bytes(path):
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        for full_path, archive_name in files_to_zip(path=path):
            z.write(full_path, archive_name)
    return buf.getvalue()


def update_lambda_code(lambda_func_name):
    lambda_code_path = "lambda_code"
    if not os.path.isdir(lambda_code_path):
        raise ValueError(f'Lambda directory does not exist {lambda_code_path}')
    logger.info(f'Updating Lambda function code ...')
    response = lambda_client.update_function_code(
        FunctionName=lambda_func_name,
        ZipFile=make_zip_file_bytes(path=lambda_code_path)
    )

def main(environment, region_name, action):
    logger.info("Creating tgw lambda role.")
    role_name = "NVSGISBSTGB-ONE-DESIGN-TGW-LambdaExecutionRole"
    # role_arn = get_role_arn(role_name)
    # if not role_arn:
    role_arn = create_iam_role(role_name)
    logger.info("Creating tgw lambda policy.")
    policy_arn = create_policy("PAWSBSTTGWVPCLAMBDA")
    print(policy_arn)
    attach_to_role(role_name, policy_arn)
    time.sleep(30)
    # else:
    #     logger.info("Role already exists.")
    # role_arn = "arn:aws:iam::636711886667:role/NVSGISBSTGB-ONE-DESIGN-TGW-LambdaExecutionRole"
    # role_arn = "arn:aws:iam::636711886667:role/NVSGISBSTGB-ONE-DESIGN-TGW-LambdaExecutionRole"
    transitgatewayId = data[environment][region_name]['transitgatewayId']
    lambda_func_name = data['lambda_func_name']
    dynamodb_table = data['dynamodb_table']
    if action == "CREATE":
        create_schedule_tgw_lambda(lambda_func_name, role_arn, transitgatewayId, dynamodb_table)
    elif action == "UPDATE":
        update_lambda_code(lambda_func_name)
    else:
        logger.error("Selected action was not found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LAMBDA CODE",
        epilog="python3 scripts/lambda_creation.py --environment='TEST' --region_name='ap-northeast-1' --action='CREATE'"
    )
    parser.add_argument('--environment',
                        required=False,
                        help='account environment type, Ex: TEST or GB')
    parser.add_argument('--region_name',
                        required=False,
                        help='aws region name, Ex:ap-northeast-1')
    parser.add_argument('--action',
                        required=False,
                        help='action create or update')
    args = parser.parse_args()
    environment = args.environment
    region_name = args.region_name
    action = args.action

    # resp = main("TST", "ap-northeast-1")
    main(environment, region_name, action)