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

def get_vpcs(client):
    response = client.describe_vpcs(
        DryRun=False,
        MaxResults=20
    )
    return response['Vpcs']

def get_subnets(client, vpcid):
    #ec2 = bst_session.client('ec2', region_name=region)
    response = client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpcid,
                ]
            },
        ]
    )
    return response['Subnets']


def get_routetables(client, vpcid):
    #ec2 = bst_session.client('ec2', region_name=region)
    response = client.describe_route_tables(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpcid,
                ]
            },
        ],
        DryRun=False,
        MaxResults=30
    )
    return response['RouteTables']


def get_tgws(client):
    response = client.describe_transit_gateways(
        MaxResults=10,
        DryRun=False
    )
    return response['TransitGateways']


def get_tgw_routetables(client, tgw_id):
    response = client.describe_transit_gateway_route_tables(
        Filters=[
            {
                'Name': 'transit-gateway-id',
                'Values': [
                    tgw_id,
                ]
            },
        ],
        MaxResults=30,
        DryRun=False
    )
    return response['TransitGatewayRouteTables']


def get_tgw_vpc_attachments(client, tgw_id):
    response = client.describe_transit_gateway_vpc_attachments(
        Filters=[
            {
                'Name': 'transit-gateway-id',
                'Values': [
                    tgw_id,
                ]
            },
        ],
        MaxResults=200,
        DryRun=False
    )
    return response['TransitGatewayVpcAttachments']