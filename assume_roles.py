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
#
import logging

import boto3
import json
from boto3.session import Session

# with open('defaults.json') as defaults:
#     data = json.load(defaults)

###global session name
#base auto role arns
rcc_tst_auto_arn = "arn:aws:iam::304512965277:role/RCC_AWS_AUTOTST_ADM"
rcc_gb_auto_arn = "arn:aws:iam::304512965277:role/RCC_AWS_AUTO_ADM"

#tst role arns
rcc_tst_arn = "arn:aws:iam::900804374729:role/RRCCTST_AWS_AUTOTST_ADM"
bst_tst_arn = "arn:aws:iam::636711886667:role/RBSTTST_AWS_AUTOTST_ADM"
bst_tst_one_arn = "arn:aws:iam::636711886667:role/RBST_AWS_TSTAUTO_ADM"
dmz_tst_arn = "arn:aws:iam::728756811910:role/RDMZTST_AWS_AUTOTST_ADM"
dmz_tst_one_arn = "arn:aws:iam::728756811910:role/RDMZ_AWS_TSTAUTO_ADM"


#gb role arns
rcc_gb_arn = "arn:aws:iam::304512965277:role/RCC_AWS_RCCAUTO_ADM"
bst_gb_arn = "arn:aws:iam::366103429990:role/RBST_AWS_AUTO_ADM"
bst_gb_one_arn ="arn:aws:iam::366103429990:role/RBST_AWS_EWTP_CONNECTIVITY"
dmz_gb_arn = "arn:aws:iam::132910123013:role/RDMZ_AWS_AUTO_ADM"
dmz_gb_one_arn ="arn:aws:iam::132910123013:role/RDMZ_AWS_NSTP_CONNECTIVITY"



SESSION_NAME = "one-design-session"



def role_arn(account_number, account_name):
    global role_arn
    if "TST" in account_name:
        if account_name == "RCCTST":
            role_arn = rcc_tst_arn
        else:
            role_arn = "".join(('arn:aws:iam::', account_number, ':role/R', account_name, '_AWS_AUTOTST_ADM'))
    else:
        if account_name == "RCC":
            role_arn = rcc_gb_arn
        else:
            role_arn = "".join(('arn:aws:iam::', account_number, ':role/R', account_name, '_AWS_AUTO_ADM'))
    return role_arn



def get_session(response):
    session = boto3.Session(aws_access_key_id=response['Credentials']['AccessKeyId'],
                      aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                      aws_session_token=response['Credentials']['SessionToken'])
    sts = session.client('sts')
    return session


"""

def local_jenkins(env_type):
    from connect import ConnectJenkins
    global connectObj
    if env_type == "GB":
        connectObj = ConnectJenkins("GB")
    elif env_type == "PGB":
        connectObj = ConnectJenkins("GB")
    elif env_type == "DEV":
        connectObj = ConnectJenkins("GB")
    elif env_type == "TST":
        connectObj = ConnectJenkins("TST")
    elif env_type == "TEST":
        connectObj = ConnectJenkins("TST")
    else:
        print(f"{env_type} Not found.")
    resp = connectObj.get_keys(env_type)
    # print(resp)
    session = boto3.Session(aws_access_key_id=resp['AccessKeyId'],
                            aws_secret_access_key=resp['SecretAccessKey'],
                            aws_session_token=resp['SessionToken'])
    sts = session.client('sts')
    return session

"""


def rcc_auto_session(environ_type):
    ##default Jenkins Instance profile
    sts = boto3.client('sts')
    ## Default RCC role
    if environ_type == 'TEST':
        resp = sts.assume_role(RoleArn=rcc_tst_auto_arn, RoleSessionName=SESSION_NAME)
        rcc_session = get_session(resp)
        return rcc_session
    elif environ_type == 'PROD':
        resp = sts.assume_role(RoleArn=rcc_gb_auto_arn, RoleSessionName=SESSION_NAME)
        rcc_session = get_session(resp)
        return rcc_session
    else:
        logging.error(f"Selected Environment{environ_type} not found.")
    #Local Jenkins
    # rcc_session = local_jenkins(environ_type)
    # return rcc_session




def rcc_session(environ_type):
    rcc_session = rcc_auto_session(environ_type)
    sts = rcc_session.client('sts')
    ## Default RCC role
    if environ_type == 'TEST':
        resp = sts.assume_role(RoleArn=rcc_tst_arn, RoleSessionName=SESSION_NAME)
        rcc_session = get_session(resp)
        return rcc_session
    else:
        resp = sts.assume_role(RoleArn=rcc_gb_arn, RoleSessionName=SESSION_NAME)
        rcc_session = get_session(resp)
        return rcc_session


def bst_onedesign_session(environ_type):
    rcc_session = rcc_auto_session(environ_type)
    sts = rcc_session.client('sts')
    ##
    if environ_type == 'TEST':
        resp = sts.assume_role(RoleArn=bst_tst_arn, RoleSessionName=SESSION_NAME)
        bst_session = get_session(resp)
        sts = bst_session.client('sts')
        resp = sts.assume_role(RoleArn=bst_tst_one_arn, RoleSessionName=SESSION_NAME)
        bst_one_session = get_session(resp)
        return bst_one_session
    else:
        resp = sts.assume_role(RoleArn=bst_gb_arn, RoleSessionName=SESSION_NAME)
        bst_session = get_session(resp)
        sts = bst_session.client('sts')
        resp = sts.assume_role(RoleArn=bst_gb_one_arn, RoleSessionName=SESSION_NAME)
        bst_one_session = get_session(resp)
        return bst_one_session


def target_session(sts, target_arn):
    response = sts.assume_role(RoleArn=target_arn, RoleSessionName=SESSION_NAME)
    target_session = get_session(response)
    return target_session


def dmz_onedesign_session(environ_type):
    rcc_session = rcc_auto_session(environ_type)
    sts = rcc_session.client('sts')
    ##
    if environ_type == 'TEST':
        resp = sts.assume_role(RoleArn=dmz_tst_arn, RoleSessionName=SESSION_NAME)
        dmz_session = get_session(resp)
        sts = dmz_session.client('sts')
        resp = sts.assume_role(RoleArn=dmz_tst_one_arn, RoleSessionName=SESSION_NAME)
        dmz_one_session = get_session(resp)
        return dmz_one_session
    else:
        resp = sts.assume_role(RoleArn=dmz_gb_arn, RoleSessionName=SESSION_NAME)
        dmz_session = get_session(resp)
        sts = dmz_session.client('sts')
        resp = sts.assume_role(RoleArn=dmz_gb_one_arn, RoleSessionName=SESSION_NAME)
        dmz_one_session = get_session(resp)
        return dmz_one_session


def idy_jit_session(accessKeyId, secretAccessKey, sessionToken, region_name):
    sts = boto3.client('sts', aws_access_key_id=accessKeyId,
                      aws_secret_access_key=secretAccessKey,
                      aws_session_token=sessionToken,
                      region_name=region_name)
    account_arn = sts.get_caller_identity()["Arn"]
    print(account_arn)
    return sts
    # #role_name = "RIDY_AWS_RDRA_AWSJIT1"
    # role_arn = "".join(('arn:aws:iam::', account_id, ':role/', role_name))
    # role_sess = "GLOBAL_ROLE_AWSJIT_Session"
    # resp = sts.assume_role(RoleArn=role_arn, RoleSessionName=role_sess)
    # session = boto3.Session(aws_access_key_id=resp['Credentials']['AccessKeyId'],
    #                         aws_secret_access_key=resp['Credentials']['SecretAccessKey'],
    #                         aws_session_token=resp['Credentials']['SessionToken'],
    #                         region_name=region_name)
    # sts = session.client('sts')
    # account_arn = sts.get_caller_identity()["Arn"]
    # print(account_arn)
    # return session