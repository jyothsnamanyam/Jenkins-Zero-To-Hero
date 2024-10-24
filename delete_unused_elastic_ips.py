import boto3
import argparse
import json
import logging

# Configure the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION_NAME = "AWS_Automation"

def get_session(response):
    session = boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )
    return session

def target_session(sts, target_arn):
    try:
        response = sts.assume_role(RoleArn=target_arn, RoleSessionName=SESSION_NAME)
        target_session = get_session(response)
        return target_session
    except Exception as e:
        logger.info(f"Failed to assume role {target_arn}. Error: {str(e)}")
        raise

def delete_unused_elastic_ips(account, aws_access_key, aws_secret_key, aws_session_token):
    account_id = account['account_id']
    assume_role_name = account['assume_role_name']
    region_name = account['region']
    
    logger.info(f'Executing script for account: {account_id} in region: {region_name}')
    
    arn = f"arn:aws-cn:iam::{account_id}:role/{assume_role_name}" if region_name.startswith('cn-') \
          else f"arn:aws:iam::{account_id}:role/{assume_role_name}"
    logger.info(f'Assuming role: {arn}')
    
    # Initialize STS client
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token
    )
    sts = session.client('sts', region_name='us-east-1' if not region_name.startswith('cn-') else region_name) # Defaulting STS region
    
    # Assume role in the target account
    target_account_session = target_session(sts, arn)

    # Access EC2 service in the target account
    ec2 = target_account_session.client("ec2", region_name=region_name)
    
    addresses = ec2.describe_addresses()['Addresses']
    
    for address in addresses:
        association_id = address.get('AssociationId')
        tags = address.get('Tags', [])
        
        name_tag = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        
        # Check if the EIP is not associated (i.e., unused) and has a name that starts with CSR
        if not association_id and name_tag and 'CSR' in name_tag:
            try:
                logger.info(f'Deleting Elastic IP {address["PublicIp"]}...')
                ec2.release_address(AllocationId=address['AllocationId'])
                logger.info(f'Elastic IP {address["PublicIp"]} deleted successfully.')
            except Exception as e:
                logger.info(f'Failed to delete Elastic IP {address["PublicIp"]}. Error: {str(e)}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Delete unused AWS Elastic IPs whose names start with CSR.')
    parser.add_argument('--access-key', required=True, help='AWS access key ID')
    parser.add_argument('--secret-key', required=True, help='AWS secret access key')
    parser.add_argument('--session-token', required=True, help='AWS session token')
    parser.add_argument('--config-file', required=True, help='Path to JSON config file with account details')

    args = parser.parse_args()

    # Strip any double quotes from the credentials
    aws_access_key = args.access_key.strip('\"')
    aws_secret_key = args.secret_key.strip('\"')
    aws_session_token = args.session_token.strip('\"')

    # Read accounts configuration
    with open(args.config_file, 'r') as file:
        accounts = json.load(file)

    # Iterate over each account and call the function
    for account in accounts:
        delete_unused_elastic_ips(account, aws_access_key, aws_secret_key, aws_session_token)
