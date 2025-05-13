"""Google Cloud Storage implementation."""
from typing import BinaryIO, Union

from google.cloud import storage

from .base import Storage


class GCSStorage(Storage):
    """Google Cloud Storage implementation."""
    
    def __init__(self, bucket_name: str):
        """Initialize GCS storage.
        
        Args:
            bucket_name: Name of the GCS bucket
        """
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        
    def save_file(self, file_data: Union[bytes, BinaryIO], destination_path: str) -> str:
        """Save file to GCS."""
        blob = self.bucket.blob(destination_path)
        
        if isinstance(file_data, bytes):
            blob.upload_from_string(file_data)
        else:
            blob.upload_from_file(file_data)
            
        return destination_path
    
    def read_file(self, file_path: str) -> bytes:
        """Read file from GCS."""
        # Remove gs:// prefix if present
        if file_path.startswith('gs://'):
            # Extract just the object path after bucket name
            file_path = file_path.split('/', 3)[-1]
            
        blob = self.bucket.blob(file_path)
        return blob.download_as_bytes()
    
    def get_file_url(self, file_path: str) -> str:
        """Get GCS URL for file."""
        return f"gs://{self.bucket.name}/{file_path}"
