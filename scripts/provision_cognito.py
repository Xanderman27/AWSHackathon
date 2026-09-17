#!/usr/bin/env python3
"""Create the Cognito user pool the app signs people in against. Safe to run repeatedly.

    services/api/.venv/bin/python scripts/provision_cognito.py

Creates, if missing:
  - User pool     dori-users          email sign-in, one custom attribute
  - App client    dori-web            no secret, admin password auth only
  - Groups        student / teacher / parent
  - The seeded demo accounts, with the passwords printed on the landing page
  - Parameters    /dori/cognito/user_pool_id and /dori/cognito/client_id

Why the password policy is loose: the demo logins are printed on the landing page for judges
to read, so their strength is not what protects anything — being a token-bearing account in a
pool of entirely synthetic learners is. Tightening the policy would break those logins without
making the demo any safer. Real deployments should raise it; see docs/SECURITY.md.

`custom:user_id` carries the internal id (student-01, teacher-01) that the rest of the data is
keyed by, because a Cognito `sub` is a fresh uuid that nothing else in the product knows. It is
created read-only to the app client, so no one can sign up and nominate themselves somebody
else's learner id.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
POOL_NAME = "dori-users"
CLIENT_NAME = "dori-web"
GROUPS = ("student", "teacher", "parent")
PARAM_PREFIX = "/dori/cognito"

SEED = Path(__file__).resolve().parents[1] / "data" / "seed" / "accounts.json"


def say(mark: str, text: str) -> None:
    print(f"[{mark:^6}] {text}")


def find_pool(idp) -> str | None:
    paginator = idp.get_paginator("list_user_pools")
    for page in paginator.paginate(MaxResults=60):
        for pool in page["UserPools"]:
            if pool["Name"] == POOL_NAME:
                return pool["Id"]
    return None


def ensure_pool(idp) -> str:
    existing = find_pool(idp)
    if existing:
        say("exists", f"user pool {POOL_NAME} ({existing})")
        return existing

    created = idp.create_user_pool(
        PoolName=POOL_NAME,
        # Usernames are the sign-in handle. The demo accounts sign in as "sam" and "rivera";
        # families sign in with their email, which is also stored as the email attribute.
        Policies={"PasswordPolicy": {
            "MinimumLength": 8, "RequireUppercase": False, "RequireLowercase": False,
            "RequireNumbers": False, "RequireSymbols": False,
        }},
        AutoVerifiedAttributes=[],
        MfaConfiguration="OFF",
        AccountRecoverySetting={"RecoveryMechanisms": [
            {"Priority": 1, "Name": "verified_email"}]},
        Schema=[
            {"Name": "email", "AttributeDataType": "String", "Mutable": True,
             "Required": False},
            {"Name": "name", "AttributeDataType": "String", "Mutable": True,
             "Required": False},
            # Not mutable, and not writable by the client below: the server sets it once.
            {"Name": "user_id", "AttributeDataType": "String", "Mutable": False,
             "Required": False, "StringAttributeConstraints": {
                 "MinLength": "1", "MaxLength": "64"}},
        ],
        UserPoolTags={"app": "dori"},
    )
    pool_id = created["UserPool"]["Id"]
    say("made", f"user pool {POOL_NAME} ({pool_id})")
    return pool_id


def ensure_client(idp, pool_id: str) -> str:
    for client in idp.list_user_pool_clients(UserPoolId=pool_id, MaxResults=60)["UserPoolClients"]:
        if client["ClientName"] == CLIENT_NAME:
            say("exists", f"app client {CLIENT_NAME}")
            return client["ClientId"]

    created = idp.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=CLIENT_NAME,
        # No secret: the API authorises these calls with its instance role, so there is no
        # shared secret for anything to hold or leak.
        GenerateSecret=False,
        # Admin password auth only. USER_PASSWORD_AUTH would let anyone on the internet
        # attempt sign-ins against the pool directly, bypassing our rate limits and audit log.
        ExplicitAuthFlows=["ALLOW_ADMIN_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        PreventUserExistenceErrors="ENABLED",
        # The client may read these, and write none of them. custom:user_id is absent from
        # both lists on purpose: it decides which learner you are.
        ReadAttributes=["email", "name"],
        WriteAttributes=[],
        IdTokenValidity=8, AccessTokenValidity=8, RefreshTokenValidity=30,
        TokenValidityUnits={"IdToken": "hours", "AccessToken": "hours",
                            "RefreshToken": "days"},
    )
    client_id = created["UserPoolClient"]["ClientId"]
    say("made", f"app client {CLIENT_NAME} ({client_id})")
    return client_id


def ensure_groups(idp, pool_id: str) -> None:
    have = {g["GroupName"] for g in
            idp.list_groups(UserPoolId=pool_id, Limit=60)["Groups"]}
    for group in GROUPS:
        if group in have:
            continue
        idp.create_group(UserPoolId=pool_id, GroupName=group,
                         Description=f"Dori {group}s")
        say("made", f"group {group}")
    if have:
        say("exists", f"groups {', '.join(sorted(have & set(GROUPS)))}")


def ensure_demo_users(idp, pool_id: str) -> None:
    """The seeded logins, so the demo behaves exactly as it did before Cognito."""
    accounts = json.loads(SEED.read_text())
    for acct in accounts:
        username = acct["username"]
        try:
            idp.admin_create_user(
                UserPoolId=pool_id,
                Username=username,
                MessageAction="SUPPRESS",
                UserAttributes=[
                    {"Name": "name", "Value": acct["display_name"]},
                    {"Name": "custom:user_id", "Value": acct["user_id"]},
                ],
            )
            say("made", f"user {username} ({acct['role']})")
        except ClientError as problem:
            if problem.response["Error"]["Code"] != "UsernameExistsException":
                raise
            say("exists", f"user {username}")

        # Set every run, so a pool that drifted lands back on the printed password.
        idp.admin_set_user_password(UserPoolId=pool_id, Username=username,
                                    Password=acct["password"], Permanent=True)
        idp.admin_add_user_to_group(UserPoolId=pool_id, Username=username,
                                    GroupName=acct["role"])


def ensure_parameters(ssm, pool_id: str, client_id: str) -> None:
    for name, value in (("user_pool_id", pool_id), ("client_id", client_id)):
        ssm.put_parameter(Name=f"{PARAM_PREFIX}/{name}", Value=value,
                          Type="String", Overwrite=True)
        say("  ok  ", f"{PARAM_PREFIX}/{name}")


def main() -> int:
    session = boto3.Session(region_name=REGION)
    try:
        session.client("sts").get_caller_identity()
    except Exception as problem:  # noqa: BLE001
        print(f"No usable AWS credentials: {problem}", file=sys.stderr)
        return 1

    idp = session.client("cognito-idp")
    pool_id = ensure_pool(idp)
    client_id = ensure_client(idp, pool_id)
    ensure_groups(idp, pool_id)
    ensure_demo_users(idp, pool_id)
    ensure_parameters(session.client("ssm"), pool_id, client_id)

    print()
    say("  ok  ", "Cognito is ready. The API reads both ids from Parameter Store at startup.")
    print(f"\n  COGNITO_USER_POOL_ID={pool_id}\n  COGNITO_CLIENT_ID={client_id}\n")
    say("  !!  ", "Restart the API (or let the update timer do it) to pick them up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
