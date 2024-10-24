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

def delete_unused_nics(account, aws_access_key, aws_secret_key, aws_session_token):
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
    
    nics = ec2.describe_network_interfaces()['NetworkInterfaces']
    for nic in nics:
        nic_id = nic['NetworkInterfaceId']
        status = nic['Status']
        tags = nic.get('TagSet', [])

        # Check if any tag contains 'CSR' (case-insensitive)
        csr_tag_present = any('CSR' in tag['Value'].upper() for tag in tags)

        # Check if the NIC is in 'available' state and if any tag contains 'CSR'
        if status == 'available' and csr_tag_present:
            logger.info(f'Account ID: {account_id}, NIC ENI ID: {nic_id} contains "CSR" in its tags:')
            
            # Log all tags for the NIC
            for tag in tags:
                logger.info(f'Tag Key: {tag["Key"]}, Tag Value: {tag["Value"]}')
            
            try:
                logger.info(f'Deleting NIC {nic_id} with tags: {tags}...')
                #ec2.delete_network_interface(NetworkInterfaceId=nic_id)
                logger.info(f'NIC {nic_id} deleted successfully.')
            except Exception as e:
                logger.error(f'Failed to delete NIC {nic_id}. Error: {str(e)}')

    
    # for nic in nics:
    #     nic_id = nic['NetworkInterfaceId']
    #     status = nic['Status']
    #     tags = nic.get('TagSet', [])
        
    #     name_tag = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        
    #     # Check if the NIC is in 'available' state, which means it is unused
    #     # and if the name starts with 'CSR' or contains 'CSR'
    #     if status == 'available' and name_tag and 'CSR' in name_tag:
    #         logger.info(f'Account ID: {account_id}, NIC ENI ID: {nic_id} contains "CISCO CSR".')
    #         try:
    #              logger.info(f'Deleting NIC {nic_id} with name {name_tag}...')
    #             # ec2.delete_network_interface(NetworkInterfaceId=nic_id)
    #             # logger.info(f'NIC {nic_id} deleted successfully.')
    #         except Exception as e:
    #             logger.info(f'Failed to delete NIC {nic_id}. Error: {str(e)}')





if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Delete unused AWS NICs with names starting with or containing CSR.')
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
        delete_unused_nics(account, aws_access_key, aws_secret_key, aws_session_token)
