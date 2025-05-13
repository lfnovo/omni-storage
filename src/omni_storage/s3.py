"""Amazon S3 storage implementation."""

from typing import BinaryIO, Union

import boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

from .base import Storage


class S3Storage(Storage):
    """Amazon S3 Storage implementation."""

    def __init__(self, bucket_name: str, region_name: str | None = None):
        """Initialize S3 storage.

        Args:
            bucket_name: Name of the S3 bucket
            region_name: AWS region (optional)
        """
        self.bucket_name = bucket_name
        self.s3 = boto3.client("s3", region_name=region_name)

    def save_file(
        self, file_data: Union[bytes, BinaryIO], destination_path: str
    ) -> str:
        """Save file to S3."""
        try:
            if isinstance(file_data, bytes):
                self.s3.put_object(
                    Bucket=self.bucket_name, Key=destination_path, Body=file_data
                )
            else:
                self.s3.upload_fileobj(file_data, self.bucket_name, destination_path)
            return destination_path
        except ClientError as e:
            raise RuntimeError(f"Failed to save file to S3: {e}")

    def read_file(self, file_path: str) -> bytes:
        """Read file from S3."""
        try:
            obj = self.s3.get_object(Bucket=self.bucket_name, Key=file_path)
            return obj["Body"].read()
        except ClientError as e:
            raise RuntimeError(f"Failed to read file from S3: {e}")

    def get_file_url(self, file_path: str) -> str:
        """Get S3 URL for file."""
        return f"s3://{self.bucket_name}/{file_path}"
