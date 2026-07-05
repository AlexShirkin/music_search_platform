"""S3-compatible object storage (MinIO locally, Evolution Object Storage in prod)."""

from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from music_platform.config import Settings, get_settings


def get_s3_client(settings: Settings | None = None) -> BaseClient:
    cfg = settings or get_settings()
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key,
        aws_secret_access_key=cfg.s3_secret_key,
        region_name="us-east-1",
    )


def ensure_bucket(client: BaseClient, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def upload_file(
    client: BaseClient,
    bucket: str,
    key: str,
    local_path: Path,
) -> str:
    client.upload_file(str(local_path), bucket, key)
    return key


def object_exists(client: BaseClient, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
    except ClientError:
        return False
    return True
