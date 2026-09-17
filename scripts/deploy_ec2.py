#!/usr/bin/env python3
"""Launch (or replace) the EC2 instance that serves Dori.

    services/api/.venv/bin/python scripts/deploy_ec2.py

One instance, on purpose: the collaborative games keep their rooms in process memory, so two
instances would put teammates in different rooms. State and photos live in DynamoDB and S3,
so the instance itself is disposable — this script can destroy and recreate it freely.

It carries no credentials. The instance assumes dori-api-role for Bedrock, S3 and DynamoDB.
"""

from __future__ import annotations

import sys
import time

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
NAME = "dori-api"
SG_NAME = "dori-api-sg"
PROFILE = "dori-api-profile"
PORT = 8000
REPO = "https://github.com/Xanderman27/AWSHackathon.git"
BUCKET = None  # filled from the account id

USER_DATA = """#!/bin/bash
set -xeuo pipefail
exec > >(tee /var/log/dori-boot.log) 2>&1

dnf -y update
dnf -y install python3.11 python3.11-pip git tar gzip

cd /opt
git clone --depth 1 {repo} dori
cd /opt/dori

python3.11 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r services/api/requirements.txt

# The built front end comes from S3 rather than being compiled here: no Node on the box,
# and a boot that cannot fail on a JavaScript toolchain.
aws s3 cp s3://{bucket}/deploy/web-dist.tar.gz /tmp/web-dist.tar.gz
mkdir -p apps/web && tar -xzf /tmp/web-dist.tar.gz -C apps/web

cat > /etc/systemd/system/dori.service <<UNIT
[Unit]
Description=Dori
After=network-online.target

[Service]
WorkingDirectory=/opt/dori/services/api
Environment=STORAGE_BACKEND=aws
Environment=STATE_TABLE=dori-state
Environment=UPLOADS_BUCKET={bucket}
Environment=AWS_REGION={region}
Environment=DEMO_OFFLINE=0
Environment=BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
ExecStart=/opt/dori/.venv/bin/python -m uvicorn app.serve:root --host 0.0.0.0 --port {port}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now dori

# Seed DynamoDB and S3 on first boot only, so a redeploy never wipes live demo state.
sleep 8
if [ "$(aws dynamodb scan --table-name dori-state --max-items 1 --region {region} \
        --query 'Count' --output text)" = "0" ]; then
  curl -s -X POST http://localhost:{port}/api/demo/reset || true
fi
echo BOOT-COMPLETE
"""


def say(mark: str, text: str) -> None:
    print(f"[{mark:^9}] {text}")


def ensure_security_group(ec2, vpc_id: str) -> str:
    existing = ec2.describe_security_groups(Filters=[
        {"Name": "group-name", "Values": [SG_NAME]}, {"Name": "vpc-id", "Values": [vpc_id]}])
    if existing["SecurityGroups"]:
        say("exists", f"security group {SG_NAME}")
        return existing["SecurityGroups"][0]["GroupId"]
    group_id = ec2.create_security_group(
        GroupName=SG_NAME, Description="Dori API", VpcId=vpc_id)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": PORT, "ToPort": PORT,
        "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "app (CloudFront fronts this)"}]}])
    say("made", f"security group {SG_NAME} (tcp/{PORT})")
    return group_id


def terminate_old(ec2) -> None:
    found = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [NAME]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])
    ids = [i["InstanceId"] for r in found["Reservations"] for i in r["Instances"]]
    if ids:
        ec2.terminate_instances(InstanceIds=ids)
        say("replaced", f"terminated {', '.join(ids)}")


def main() -> int:
    account = boto3.client("sts").get_caller_identity()["Account"]
    bucket = f"dori-uploads-{account}"
    ec2 = boto3.client("ec2", region_name=REGION)
    ssm = boto3.client("ssm", region_name=REGION)

    ami = ssm.get_parameter(
        Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
    )["Parameter"]["Value"]
    say("  ok  ", f"Amazon Linux 2023 AMI {ami}")

    vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]
    subnet = ec2.describe_subnets(Filters=[
        {"Name": "vpc-id", "Values": [vpc["VpcId"]]},
        {"Name": "map-public-ip-on-launch", "Values": ["true"]}])["Subnets"][0]
    group_id = ensure_security_group(ec2, vpc["VpcId"])

    terminate_old(ec2)

    user_data = USER_DATA.format(repo=REPO, bucket=bucket, region=REGION, port=PORT)
    try:
        instance = ec2.run_instances(
            ImageId=ami, InstanceType="t3.small", MinCount=1, MaxCount=1,
            IamInstanceProfile={"Name": PROFILE},
            NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet["SubnetId"],
                                "AssociatePublicIpAddress": True, "Groups": [group_id]}],
            UserData=user_data,
            TagSpecifications=[{"ResourceType": "instance",
                                "Tags": [{"Key": "Name", "Value": NAME}]}],
            MetadataOptions={"HttpTokens": "required"},
        )["Instances"][0]
    except ClientError as problem:
        say("  FAIL ", f"{problem.response['Error']['Code']}: {problem.response['Error']['Message'][:200]}")
        return 1

    instance_id = instance["InstanceId"]
    say("launched", f"{instance_id} (t3.small)")
    ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
    described = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
    host = described["PublicDnsName"]
    say("  ok  ", f"running at {host}")

    print("\nWaiting for the app to answer (first boot installs Python packages)…")
    import urllib.error
    import urllib.request
    for attempt in range(60):
        try:
            with urllib.request.urlopen(f"http://{host}:{PORT}/api/health", timeout=4) as response:
                if response.status == 200:
                    say("  ok  ", f"healthy after {attempt * 10}s")
                    print(f"\n  http://{host}:{PORT}\n")
                    print(f"  instance: {instance_id}")
                    print("  logs:     aws ssm start-session, or check /var/log/dori-boot.log\n")
                    return 0
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(10)
        if attempt % 3 == 0:
            print(f"    … {attempt * 10}s")
    say("  FAIL ", "the app did not come up in 10 minutes")
    print(f"  instance {instance_id} at {host}; check /var/log/dori-boot.log")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
