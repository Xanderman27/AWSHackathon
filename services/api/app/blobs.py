"""Where uploaded bytes live: the local disk, or an S3 bucket.

Classroom photos were the first thing in this app that is not JSON, and a filesystem path is
not an interface you can move to S3. Both backends answer the same three questions — store
these bytes, give them back, forget them — so the router never learns which one it got.

Names are generated server-side (a uuid plus an extension), never taken from an upload, and
both backends refuse anything that is not that shape.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Protocol

# uuid4().hex plus a known image extension. Nothing else is a valid stored name.
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(jpg|jpeg|png|webp|heic)$")


def check_name(name: str) -> str:
    if not SAFE_NAME.match(name) or ".." in name or "/" in name or "\\" in name:
        raise ValueError("bad upload name")
    return name


class Blobs(Protocol):
    def put(self, name: str, data: bytes, content_type: str) -> None: ...
    def get(self, name: str) -> bytes | None: ...
    def delete(self, name: str) -> None: ...
    def reset(self, seed_dir: Path) -> None: ...


class LocalBlobs:
    """Files under data/state/uploads/."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        candidate = (self.root / check_name(name)).resolve()
        if candidate.parent != self.root.resolve():
            raise ValueError("bad upload path")
        return candidate

    def put(self, name: str, data: bytes, content_type: str) -> None:
        self._path(name).write_bytes(data)

    def get(self, name: str) -> bytes | None:
        path = self._path(name)
        return path.read_bytes() if path.exists() else None

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)

    def reset(self, seed_dir: Path) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        if seed_dir.exists():
            for src in seed_dir.iterdir():
                if src.is_file():
                    shutil.copy(src, self.root / src.name)


class S3Blobs:
    """Objects under s3://<bucket>/<prefix>/.

    The bucket stays private: bytes are read by the API and handed to the browser through the
    authorised route, never with a public URL. Presigned URLs are the next step and do not
    change the authorisation check that gates them.
    """

    def __init__(self, bucket: str, prefix: str = "uploads") -> None:
        import boto3
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))

    def _key(self, name: str) -> str:
        return f"{self.prefix}/{check_name(name)}"

    def put(self, name: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self._key(name), Body=data,
                               ContentType=content_type)

    def get(self, name: str) -> bytes | None:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=self._key(name))["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None

    def delete(self, name: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(name))

    def reset(self, seed_dir: Path) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        stale = [
            {"Key": obj["Key"]}
            for page in paginator.paginate(Bucket=self.bucket, Prefix=f"{self.prefix}/")
            for obj in page.get("Contents", [])
        ]
        for batch in (stale[i:i + 1000] for i in range(0, len(stale), 1000)):
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": batch})
        if seed_dir.exists():
            types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                     ".webp": "image/webp", ".heic": "image/heic"}
            for src in seed_dir.iterdir():
                if src.is_file():
                    self.put(src.name, src.read_bytes(), types.get(src.suffix.lower(), "image/jpeg"))
