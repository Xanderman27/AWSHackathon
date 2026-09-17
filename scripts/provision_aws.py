#!/usr/bin/env python3
"""Create the AWS resources the deployed app needs. Safe to run repeatedly.

    services/api/.venv/bin/python scripts/provision_aws.py

Creates, if missing:
  - S3 bucket        dori-uploads-<account>   private, versioning off, public access blocked
  - DynamoDB table   dori-state               pk/sk, on-demand billing
  - IAM role         dori-api-role            + instance profile, for the EC2 that runs the API

The role is what lets the deployed API call Bedrock, S3 and DynamoDB without any long-lived
keys on the box — which also means the app keeps working after your Workshop Studio session
credentials expire.
"""

from __future__ import annotations

import json
import sys
import time

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
TABLE = "dori-state"
ROLE = "dori-api-role"
PROFILE = "dori-api-profile"


def say(mark: str, text: str) -> None:
    print(f"[{mark:^6}] {text}")


def bucket_name(account: str) -> str:
    return f"dori-uploads-{account}"


def ensure_bucket(s3, name: str) -> None:
    try:
        s3.head_bucket(Bucket=name)
        say("exists", f"s3://{name}")
        return
    except ClientError as problem:
        if problem.response["Error"]["Code"] not in ("404", "NoSuchBucket", "403"):
            raise
    s3.create_bucket(Bucket=name)  # us-east-1 takes no LocationConstraint
    s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
    })
    s3.put_bucket_encryption(Bucket=name, ServerSideEncryptionConfiguration={
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    })
    say("made", f"s3://{name} (private, encrypted, public access blocked)")


def ensure_table(ddb, name: str) -> None:
    try:
        ddb.describe_table(TableName=name)
        say("exists", f"dynamodb table {name}")
        return
    except ClientError as problem:
        if problem.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
    ddb.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"},
                   {"AttributeName": "sk", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                              {"AttributeName": "sk", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    say("made", f"dynamodb table {name} (on-demand)")
    ddb.get_waiter("table_exists").wait(TableName=name)
    say("  ok  ", f"{name} is active")


def ensure_role(iam, account: str, bucket: str) -> str:
    trust = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"}]}
    policy = {"Version": "2012-10-17", "Statement": [
        {"Sid": "Bedrock", "Effect": "Allow",
         "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Converse", "bedrock:ConverseStream",
                    # Converse with a guardrailConfig needs this separately; without it the
                    # call is denied and the pipeline quietly falls back to cached drafts.
                    "bedrock:ApplyGuardrail"],
         "Resource": "*"},
        {"Sid": "Uploads", "Effect": "Allow",
         "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
         "Resource": f"arn:aws:s3:::{bucket}/*"},
        {"Sid": "UploadsList", "Effect": "Allow",
         "Action": ["s3:ListBucket"], "Resource": f"arn:aws:s3:::{bucket}"},
        {"Sid": "ServiceIds", "Effect": "Allow",
         # Guardrail ids live in Parameter Store so rotating one needs no redeploy.
         "Action": ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
         "Resource": f"arn:aws:ssm:{REGION}:{account}:parameter/dori/*"},
        {"Sid": "Identity", "Effect": "Allow",
         # Sign-in and sign-up are brokered by the API, so the instance role is what
         # authorises them. Scoped to the one pool, and deliberately without
         # AdminDeleteUser or AdminUpdateUserAttributes: this app creates and authenticates
         # users, and nothing it does should be able to rewrite who someone is.
         "Action": ["cognito-idp:AdminInitiateAuth", "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword", "cognito-idp:AdminAddUserToGroup",
                    "cognito-idp:AdminGetUser"],
         "Resource": f"arn:aws:cognito-idp:{REGION}:{account}:userpool/*"},
        {"Sid": "State", "Effect": "Allow",
         "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem",
                    "dynamodb:Query", "dynamodb:BatchWriteItem", "dynamodb:DescribeTable"],
         "Resource": f"arn:aws:dynamodb:{REGION}:{account}:table/{TABLE}"},
    ]}

    try:
        iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps(trust),
                        Description="Dori API on EC2: Bedrock, S3 uploads, DynamoDB state")
        say("made", f"iam role {ROLE}")
    except ClientError as problem:
        if problem.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        say("exists", f"iam role {ROLE}")

    iam.put_role_policy(RoleName=ROLE, PolicyName="dori-api-access",
                        PolicyDocument=json.dumps(policy))
    say("  ok  ", "inline policy written (least privilege: one bucket, one table)")

    try:
        iam.create_instance_profile(InstanceProfileName=PROFILE)
        say("made", f"instance profile {PROFILE}")
        time.sleep(8)  # IAM is eventually consistent; EC2 rejects a profile it cannot see yet
    except ClientError as problem:
        if problem.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        say("exists", f"instance profile {PROFILE}")

    profile = iam.get_instance_profile(InstanceProfileName=PROFILE)["InstanceProfile"]
    if not any(r["RoleName"] == ROLE for r in profile["Roles"]):
        iam.add_role_to_instance_profile(InstanceProfileName=PROFILE, RoleName=ROLE)
        say("  ok  ", f"{ROLE} attached to {PROFILE}")
    return PROFILE


def main() -> int:
    account = boto3.client("sts").get_caller_identity()["Account"]
    bucket = bucket_name(account)
    print(f"\nAccount {account}, region {REGION}\n")

    try:
        ensure_bucket(boto3.client("s3", region_name=REGION), bucket)
        ensure_table(boto3.client("dynamodb", region_name=REGION), TABLE)
        ensure_role(boto3.client("iam"), account, bucket)
    except ClientError as problem:
        say(" FAIL ", f"{problem.response['Error']['Code']}: {problem.response['Error']['Message'][:160]}")
        return 1

    print(f"""
Done. To run the API against these:

    export STORAGE_BACKEND=aws
    export STATE_TABLE={TABLE}
    export UPLOADS_BUCKET={bucket}
    export AWS_REGION={REGION}

Then seed them:  POST /demo/reset
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
