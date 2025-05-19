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

    def save_file(
        self, file_data: Union[bytes, BinaryIO], destination_path: str
    ) -> str:
        """Save file to GCS."""
        blob = self.bucket.blob(destination_path)

        if isinstance(file_data, bytes):
            blob.upload_from_string(file_data)
        else:
            blob.upload_from_file(file_data)

        return destination_path

    def upload_file(self, file_path: str, destination_path: str) -> str:
        """
        Upload a file from the local file system to Google Cloud Storage.

        Args:
            file_path (str): The path to the local file to upload.
            destination_path (str): The path in GCS where the file should be saved.

        Returns:
            str: The path of the saved file in GCS.
        """
        blob = self.bucket.blob(destination_path)
        with open(file_path, "rb") as file_obj:
            blob.upload_from_file(file_obj)
        return destination_path

    def read_file(self, file_path: str) -> bytes:
        """Read file from GCS."""
        # Remove gs:// prefix if present
        if file_path.startswith("gs://"):
            # Extract just the object path after bucket name
            file_path = file_path.split("/", 3)[-1]

        blob = self.bucket.blob(file_path)
        return blob.download_as_bytes()

    def get_file_url(self, file_path: str) -> str:
        """Get GCS URL for file."""
        return f"gs://{self.bucket.name}/{file_path}"

    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in Google Cloud Storage.

        Args:
            file_path (str): The path of the file in GCS.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        # Remove gs:// prefix if present
        if file_path.startswith("gs://"):
            file_path = file_path.split("/", 3)[-1]
        blob = self.bucket.blob(file_path)
        return blob.exists()
