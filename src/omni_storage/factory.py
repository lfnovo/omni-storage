"""Storage factory for creating storage instances."""
import os

from .base import Storage
from .gcs import GCSStorage
from .local import LocalStorage


def get_storage() -> Storage:
    """Get storage instance based on environment configuration.
    
    Environment variables:
        DATADIR: Path to local storage directory
        GCS_BUCKET: Name of the GCS bucket
        
    Returns:
        Storage: Storage instance
    """
    gcs_bucket = os.getenv('GCS_BUCKET')
    if gcs_bucket:
        return GCSStorage(gcs_bucket)
        
    data_dir = os.getenv('DATADIR', './data')
    return LocalStorage(data_dir)
