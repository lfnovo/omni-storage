"""Base storage interface."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Literal, Union

from .types import AppendResult


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

    @abstractmethod
    def append_file(
        self,
        content: Union[str, bytes, BinaryIO],
        filename: str,
        create_if_not_exists: bool = True,
        strategy: Literal["auto", "single", "multipart"] = "auto",
        part_size_mb: int = 100,
    ) -> AppendResult:
        """
        Append content to a file.

        This method supports appending data to files across all storage backends.
        For cloud storage (S3, GCS), it uses a multi-part file pattern for large files
        to enable efficient streaming without memory limitations.

        Args:
            content: The content to append. Can be:
                - str: Text content (will be encoded as UTF-8)
                - bytes: Binary content
                - BinaryIO: File-like object (e.g., BytesIO, open file)
            filename: Path to the file to append to
            create_if_not_exists: If True, creates the file if it doesn't exist.
                If False, raises FileNotFoundError for missing files.
            strategy: The append strategy to use:
                - "auto": Automatically choose based on file size (default)
                - "single": Use single file strategy (download-modify-upload for cloud)
                - "multipart": Use multi-part file pattern (recommended for large files)
            part_size_mb: Size threshold in MB for creating new parts in multipart strategy

        Returns:
            AppendResult: Information about the append operation including:
                - path: The file path where content was appended
                - bytes_written: Number of bytes written
                - strategy_used: The strategy that was used
                - parts_count: Number of parts in the file

        Raises:
            FileNotFoundError: If file doesn't exist and create_if_not_exists=False
            RuntimeError: If the append operation fails
            ValueError: If the content type is not supported

        Examples:
            # Append text to a file
            >>> storage = get_storage()
            >>> result = storage.append_file("Hello, world!", "logs/app.log")
            >>> print(f"Appended {result.bytes_written} bytes")

            # Append binary data
            >>> binary_data = b"\\x00\\x01\\x02"
            >>> storage.append_file(binary_data, "data/binary.bin")

            # Append from file-like object
            >>> from io import BytesIO
            >>> buffer = BytesIO(b"streaming data")
            >>> storage.append_file(buffer, "data/stream.txt")

            # Force multipart strategy for large file processing
            >>> storage.append_file(large_content, "big.csv", strategy="multipart")
        """
        pass
