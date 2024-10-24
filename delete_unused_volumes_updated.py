import boto3
import argparse
from datetime import datetime, timedelta

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
        print(f"Failed to assume role {target_arn}. Error: {str(e)}")
        raise

def delete_unused_volumes(account_id, aws_access_key, aws_secret_key, aws_session_token, aws_assume_role_name, region_name):
    print(f'Executing script for account: {account_id}')
    
    arn = f"arn:aws-cn:iam::{account_id}:role/{aws_assume_role_name}"
    print(f'arn: {arn}')
    # Initialize STS client
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token
    )
    sts = session.client('sts')
 
    # Assume role in the target account
    target_account_session = target_session(sts, arn)

    # Access EC2 service in the target account
    ec2 = target_account_session.resource("ec2", region_name=region_name)
    
    volumes = ec2.volumes.all()
    
    current_time = datetime.utcnow()
    
    for volume in volumes:
        # Check if the volume is in 'available' state, which means it is unused
        if volume.state == 'available':
            # Get the volume creation time
            creation_time = volume.create_time.replace(tzinfo=None)
            # Check if the volume has been available for more than one month
            if current_time - creation_time > timedelta(days=30):
                try:
                    print(f'Deleting volume {volume.id}...')
                    volume.delete()
                    print(f'Volume {volume.id} deleted successfully.')
                except Exception as e:
                    print(f'Failed to delete volume {volume.id}. Error: {str(e)}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Delete unused AWS volumes.')
    parser.add_argument('--account-id', required=True, help='AWS account ID')
    parser.add_argument('--access-key', required=True, help='AWS access key ID')
    parser.add_argument('--secret-key', required=True, help='AWS secret access key')
    parser.add_argument('--session-token', required=True, help='AWS session token')
    parser.add_argument('--aws-assume-role-name', required=True, help='AWS Assume Role Name')
    parser.add_argument('--region', required=True, help='AWS region')

    args = parser.parse_args()

    # Call the function to delete unused volumes
    delete_unused_volumes(args.account_id, args.access_key, args.secret_key, args.session_token, args.aws_assume_role_name, args.region)
