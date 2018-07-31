# -*- coding: utf-8 -*-

"""AWS cloud helper."""

# standard imports
# None

# 3rd party imports
import boto3
import botocore

# local imports
# None


class ConnError(botocore.vendored.requests.exceptions.ConnectionError):
    """
    A connection error occurred.

    :py:exc:`ConnectionError` wrapper exception.
    """

    pass


class ClientErr(botocore.exceptions.BotoCoreError):
    """
    A connection error occurred.

    :py:exc:`ClientError` wrapper exception.
    """

    pass


def get_aws_client(service: str, key_id: str, secret: str) -> object:
    """
    Get AWS client object.

    :param service: AWS Service
    :param key_id: AWS Key Id
    :param secret: AWS Key Secret
    """
    return boto3.client(service, aws_access_key_id=key_id,
                        aws_secret_access_key=secret)


def get_credencials_report(key_id: str, secret: str) -> dict:
    """
    Get IAM credentials report.

    :param key_id: AWS Key Id
    :param secret: AWS Key Secret
    """
    try:
        client = get_aws_client('iam',
                                key_id=key_id,
                                secret=secret)
        client.generate_credential_report()
        response = client.get_credential_report()
        users = response['Content'].decode().split('\n')[1:]
        return [x.split(',') for x in users]
    except botocore.vendored.requests.exceptions.ConnectionError:
        raise ConnError
    except botocore.exceptions.ClientError:
        raise ClientErr


def get_account_password_policy(key_id: str, secret: str) -> dict:
    """
    Get IAM account password policy.

    :param key_id: AWS Key Id
    :param secret: AWS Key Secret
    """
    try:
        client = get_aws_client('iam',
                                key_id=key_id,
                                secret=secret)
        response = client.get_account_password_policy()
        return response['PasswordPolicy']
    except botocore.vendored.requests.exceptions.ConnectionError:
        raise ConnError
    except botocore.exceptions.ClientError:
        raise ClientErr
