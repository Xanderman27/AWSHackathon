#!/usr/bin/env python3
"""Put CloudFront in front of the instance, so the site is HTTPS.

    services/api/.venv/bin/python scripts/deploy_cloudfront.py

This is not about caching. The games open a WebSocket, and a page served over HTTPS cannot
open one to a plain-HTTP origin — browsers block it as mixed content. CloudFront terminates
TLS at the edge and talks HTTP to the instance, which is what makes the whole thing work
without buying a certificate or a domain.

Caching is therefore disabled: every request is proxied. CloudFront here is a TLS front door,
not a CDN.
"""

from __future__ import annotations

import time

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
NAME = "dori-api"
PORT = 8000
COMMENT = "Dori (hackathon)"

# AWS-managed policies. CachingDisabled because the API must never be cached; AllViewer so the
# Upgrade, Connection and Sec-WebSocket-* headers reach the origin and the socket can open.
CACHE_DISABLED = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
ORIGIN_ALL_VIEWER = "216adef6-5c7f-47e4-b989-5492eafa07d3"


def say(mark: str, text: str) -> None:
    print(f"[{mark:^9}] {text}")


def instance_host() -> str:
    ec2 = boto3.client("ec2", region_name=REGION)
    found = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [NAME]},
        {"Name": "instance-state-name", "Values": ["running"]}])
    hosts = [i["PublicDnsName"] for r in found["Reservations"] for i in r["Instances"]]
    if not hosts:
        raise SystemExit("No running dori-api instance. Run scripts/deploy_ec2.py first.")
    return hosts[0]


def existing(cf):
    for item in cf.list_distributions().get("DistributionList", {}).get("Items", []):
        if item.get("Comment") == COMMENT:
            return item
    return None


def main() -> int:
    cf = boto3.client("cloudfront")
    host = instance_host()
    say("  ok  ", f"origin {host}:{PORT}")

    found = existing(cf)
    if found:
        say("exists", f"distribution {found['Id']} → https://{found['DomainName']}")
        current = cf.get_distribution_config(Id=found["Id"])
        config, etag = current["DistributionConfig"], current["ETag"]
        origin = config["Origins"]["Items"][0]
        if origin["DomainName"] == host:
            say("  ok  ", "origin already points at this instance")
            print(f"\n  https://{found['DomainName']}\n")
            return 0
        origin["DomainName"] = host
        origin["Id"] = host
        config["DefaultCacheBehavior"]["TargetOriginId"] = host
        cf.update_distribution(Id=found["Id"], IfMatch=etag, DistributionConfig=config)
        say("updated", f"origin repointed to {host}")
        print(f"\n  https://{found['DomainName']}  (a few minutes to propagate)\n")
        return 0

    config = {
        "CallerReference": f"dori-{int(time.time())}",
        "Comment": COMMENT,
        "Enabled": True,
        "Origins": {"Quantity": 1, "Items": [{
            "Id": host,
            "DomainName": host,
            "CustomOriginConfig": {
                "HTTPPort": PORT,
                "HTTPSPort": 443,
                # The instance speaks plain HTTP; TLS stops at the edge.
                "OriginProtocolPolicy": "http-only",
                "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                "OriginReadTimeout": 60,
                "OriginKeepaliveTimeout": 60,
            },
        }]},
        "DefaultCacheBehavior": {
            "TargetOriginId": host,
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 7,
                "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            "CachePolicyId": CACHE_DISABLED,
            "OriginRequestPolicyId": ORIGIN_ALL_VIEWER,
            "Compress": True,
        },
        "PriceClass": "PriceClass_100",
    }

    try:
        made = cf.create_distribution(DistributionConfig=config)["Distribution"]
    except ClientError as problem:
        say("  FAIL ", f"{problem.response['Error']['Code']}: {problem.response['Error']['Message'][:200]}")
        return 1

    say("made", f"distribution {made['Id']}")
    print(f"\n  https://{made['DomainName']}\n")
    print("  CloudFront takes a few minutes to deploy. Poll with:")
    print(f"    aws cloudfront get-distribution --id {made['Id']} --query Distribution.Status\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
