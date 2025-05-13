"""Storage factory for creating storage instances."""
import os
from typing import Literal, Optional

from .base import Storage
from .local import LocalStorage


def get_storage(storage_type: Optional[Literal["s3", "gcs", "local"]] = None) -> Storage:
    """Get storage instance.

    If `storage_type` is provided (e.g., "s3", "gcs", "local"), it determines the backend.
    Otherwise, the choice is based on environment variables:
    AWS_S3_BUCKET (for S3), GCS_BUCKET (for GCS), or DATADIR (for local, defaults to './data').

    Args:
        storage_type: Optional. Explicitly specify the storage type.
                      Can be "s3", "gcs", or "local".

    Environment variables (used for configuration regardless of `storage_type` if applicable,
                           or for auto-detection if `storage_type` is None):
        AWS_S3_BUCKET: Name of the S3 bucket (required if storage_type="s3" or for auto-detection).
        AWS_REGION: AWS region (optional for S3).
        GCS_BUCKET: Name of the GCS bucket (required if storage_type="gcs" or for auto-detection).
        DATADIR: Path to local storage directory (used if storage_type="local" or for auto-detection,
                 defaults to './data').

    Returns:
        Storage: A storage instance (S3Storage, GCSStorage, or LocalStorage).

    Raises:
        ValueError: If `storage_type` is provided but its required environment variables are missing,
                    or if an invalid `storage_type` is specified.
    """
    chosen_type: Optional[str] = None

    if storage_type:
        if storage_type not in ["s3", "gcs", "local"]:
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 's3', 'gcs', or 'local'."
            )
        chosen_type = storage_type
    else:
        # Auto-detection logic based on environment variables
        if os.getenv('AWS_S3_BUCKET'):
            chosen_type = "s3"
        elif os.getenv('GCS_BUCKET'):
            chosen_type = "gcs"
        else:
            chosen_type = "local"  # Default to local if no specific cloud env vars found

    if chosen_type == "s3":
        s3_bucket = os.getenv('AWS_S3_BUCKET')
        if not s3_bucket:
            raise ValueError("AWS_S3_BUCKET environment variable is required for S3 storage.")
        from .s3 import S3Storage  # Lazy import S3Storage
        region = os.getenv('AWS_REGION')
        if region:
            return S3Storage(s3_bucket, region_name=region)
        return S3Storage(s3_bucket)

    elif chosen_type == "gcs":
        gcs_bucket = os.getenv('GCS_BUCKET')
        if not gcs_bucket:
            raise ValueError("GCS_BUCKET environment variable is required for GCS storage.")
        from .gcs import GCSStorage  # Lazy import GCSStorage
        return GCSStorage(gcs_bucket)

    elif chosen_type == "local":
        data_dir = os.getenv('DATADIR', './data')
        # LocalStorage is already imported at the top
        return LocalStorage(data_dir)
    
    # This part should ideally not be reached if logic is correct and chosen_type is always set.
    # Adding a fallback error for robustness.
    raise RuntimeError("Could not determine storage type. This should not happen.")
