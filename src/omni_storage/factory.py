"""Storage factory for creating storage instances."""
import os

from .base import Storage
from .local import LocalStorage


def get_storage() -> Storage:
    """Get storage instance based on environment configuration.
    
    Environment variables:
        AWS_S3_BUCKET: Name of the S3 bucket
        AWS_REGION: AWS region (optional)
        GCS_BUCKET: Name of the GCS bucket
        DATADIR: Path to local storage directory
    
    Returns:
        Storage: Storage instance
    """
    s3_bucket = os.getenv('AWS_S3_BUCKET')
    if s3_bucket:
        from .s3 import S3Storage  # Lazy import S3Storage
        region = os.getenv('AWS_REGION')
        if region:
            return S3Storage(s3_bucket, region_name=region)
        return S3Storage(s3_bucket)

    gcs_bucket = os.getenv('GCS_BUCKET')
    if gcs_bucket:
        from .gcs import GCSStorage  # Lazy import GCSStorage
        return GCSStorage(gcs_bucket)

    data_dir = os.getenv('DATADIR', './data')
    return LocalStorage(data_dir)
