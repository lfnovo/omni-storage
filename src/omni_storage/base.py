"""Base storage interface."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Union


class Storage(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    def save_file(
        self, file_data: Union[bytes, BinaryIO], destination_path: str
    ) -> str:
        """Save file data to storage.

        Args:
            file_data: The file data as bytes or file-like object
            destination_path: The path where to save the file

        Returns:
            str: The full path where the file was saved
        """
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """Read file data from storage.

        Args:
            file_path: Path to the file to read

        Returns:
            bytes: The file contents
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> str:
        """Get a URL that can be used to access the file.

        Args:
            file_path: Path to the file

        Returns:
            str: URL to access the file
        """
        pass

    @abstractmethod
    def upload_file(self, file_path: str, destination_path: str) -> str:
        """
        Upload a file from the local file system to the storage.

        Args:
            file_path (str): The path to the local file to upload.
            destination_path (str): The path in the storage system where the file should be saved.

        Returns:
            str: The path or identifier of the saved file in the storage system.
        """
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in the storage.

        Args:
            file_path (str): The path of the file in the storage system.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        pass
