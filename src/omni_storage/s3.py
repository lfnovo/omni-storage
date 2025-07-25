"""Amazon S3 storage implementation."""

from typing import BinaryIO, Literal, Union

import boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

from .base import Storage
from .manifest import ManifestManager
from .types import AppendResult


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
        self.manifest_manager = ManifestManager()

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
        """Read file from S3, handling both single files and manifest-based multipart files."""
        try:
            # First, check if a manifest exists
            manifest_key = f"{file_path}.manifest"
            try:
                manifest_obj = self.s3.get_object(Bucket=self.bucket_name, Key=manifest_key)
                manifest_content = manifest_obj["Body"].read()
                
                # It's a multipart file - read all parts
                try:
                    manifest = self.manifest_manager.read_manifest(manifest_content)
                    return self._read_multipart_file(manifest)
                except ValueError:
                    # Invalid manifest, fall back to direct read
                    pass
            except ClientError:
                # No manifest, continue with direct read
                pass

            # Read as single file
            obj = self.s3.get_object(Bucket=self.bucket_name, Key=file_path)
            return obj["Body"].read()
        except ClientError as e:
            raise RuntimeError(f"Failed to read file from S3: {e}")

    def _read_multipart_file(self, manifest: dict) -> bytes:
        """Read and concatenate all parts of a multipart file."""
        parts = self.manifest_manager.get_parts_in_order(manifest)
        content_parts = []

        for part in parts:
            try:
                part_obj = self.s3.get_object(Bucket=self.bucket_name, Key=part["name"])
                content_parts.append(part_obj["Body"].read())
            except ClientError as e:
                raise RuntimeError(f"Failed to read part {part['name']}: {e}")

        return b"".join(content_parts)

    def get_file_url(self, file_path: str) -> str:
        """Get S3 URL for file."""
        return f"s3://{self.bucket_name}/{file_path}"

    def upload_file(self, file_path: str, destination_path: str) -> str:
        """
        Upload a file from the local file system to Amazon S3.

        Args:
            file_path (str): The path to the local file to upload.
            destination_path (str): The path in S3 where the file should be saved.

        Returns:
            str: The path of the saved file in S3.
        """
        with open(file_path, "rb") as file_obj:
            self.s3.upload_fileobj(file_obj, self.bucket_name, destination_path)
        return destination_path

    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in Amazon S3.

        Args:
            file_path (str): The path of the file in S3.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception:
            return False

    def append_file(
        self,
        content: Union[str, bytes, BinaryIO],
        filename: str,
        create_if_not_exists: bool = True,
        strategy: Literal["auto", "single", "multipart"] = "auto",
        part_size_mb: int = 100,
    ) -> AppendResult:
        """
        Append content to a file in S3.

        Since S3 doesn't support native append, this implementation uses:
        - Single strategy: Download existing content, append, and re-upload
        - Multipart strategy: Create separate part files (Phase 4)

        Args:
            content: Content to append (str, bytes, or file-like object)
            filename: S3 key of the file to append to
            create_if_not_exists: If True, creates file if it doesn't exist
            strategy: Append strategy ("auto", "single", or "multipart")
            part_size_mb: Size threshold for multipart strategy

        Returns:
            AppendResult with operation details

        Raises:
            FileNotFoundError: If file doesn't exist and create_if_not_exists=False
            RuntimeError: If the append operation fails
        """
        # Convert content to bytes
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        elif isinstance(content, bytes):
            content_bytes = content
        elif hasattr(content, "read"):
            # File-like object
            data = content.read()
            if isinstance(data, str):
                content_bytes = data.encode("utf-8")
            else:
                content_bytes = data
        else:
            raise ValueError(
                f"Content type {type(content)} is not supported. "
                "Must be str, bytes, or file-like object with read() method."
            )

        # Check if file exists
        file_exists = self.exists(filename)

        if not file_exists and not create_if_not_exists:
            raise FileNotFoundError(f"File {filename} does not exist in S3")

        # Determine strategy
        if strategy == "auto":
            # Auto-select based on file existence and size
            if file_exists:
                try:
                    # Get file metadata to check size
                    obj_info = self.s3.head_object(Bucket=self.bucket_name, Key=filename)
                    file_size = obj_info.get("ContentLength", 0)
                    
                    # Check if it's already a manifest
                    if file_size < 10 * 1024 * 1024:  # Small files < 10MB, check content
                        obj = self.s3.get_object(Bucket=self.bucket_name, Key=filename)
                        first_bytes = obj["Body"].read(1024)  # Read first 1KB
                        obj["Body"].close()
                        
                        if self.manifest_manager.is_manifest_file(first_bytes):
                            strategy = "multipart"
                        else:
                            # Use multipart if file is larger than threshold
                            strategy = "multipart" if file_size >= part_size_mb * 1024 * 1024 else "single"
                    else:
                        # Large files always use multipart
                        strategy = "multipart"
                except ClientError:
                    strategy = "single"
            else:
                # New files default to single unless explicitly multipart
                strategy = "single"

        # Execute chosen strategy
        if strategy == "single":
            return self._append_single_strategy(filename, content_bytes, file_exists)
        else:
            return self._append_multipart_strategy(filename, content_bytes, file_exists, part_size_mb)

    def _append_single_strategy(
        self, filename: str, content_bytes: bytes, file_exists: bool
    ) -> AppendResult:
        """Implement single file append strategy."""
        try:
            if file_exists:
                # Download existing content
                existing_obj = self.s3.get_object(Bucket=self.bucket_name, Key=filename)
                existing_content = existing_obj["Body"].read()
                combined_content = existing_content + content_bytes
            else:
                # New file
                combined_content = content_bytes

            # Upload the combined content
            self.s3.put_object(
                Bucket=self.bucket_name, Key=filename, Body=combined_content
            )

            return AppendResult(
                path=f"s3://{self.bucket_name}/{filename}",
                bytes_written=len(content_bytes),
                strategy_used="single",
                parts_count=1,
            )

        except ClientError as e:
            raise RuntimeError(f"Failed to append to file in S3: {e}")

    def _append_multipart_strategy(
        self, filename: str, content_bytes: bytes, file_exists: bool, part_size_mb: int
    ) -> AppendResult:
        """Implement multipart append strategy using manifest files."""
        try:
            manifest_key = f"{filename}.manifest"
            
            # Load or create manifest
            if file_exists:
                # Check if manifest exists
                try:
                    manifest_obj = self.s3.get_object(Bucket=self.bucket_name, Key=manifest_key)
                    manifest_content = manifest_obj["Body"].read()
                    manifest = self.manifest_manager.read_manifest(manifest_content)
                except ClientError:
                    # No manifest exists, need to convert single file to multipart
                    return self._convert_to_multipart(filename, content_bytes, part_size_mb)
            else:
                # Create new manifest
                content_type = "text/plain"
                if filename.endswith(".csv"):
                    content_type = "text/csv"
                elif filename.endswith((".bin", ".dat")):
                    content_type = "application/octet-stream"
                    
                manifest = self.manifest_manager.create_manifest(
                    base_name=filename,
                    content_type=content_type
                )

            # Generate part name and upload
            part_name = self.manifest_manager.get_next_part_name(filename, manifest)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=part_name,
                Body=content_bytes
            )

            # Update manifest
            manifest = self.manifest_manager.add_part(
                manifest, part_name, len(content_bytes)
            )

            # Save updated manifest
            manifest_bytes = self.manifest_manager.serialize_manifest(manifest)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=manifest_key,
                Body=manifest_bytes
            )

            return AppendResult(
                path=f"s3://{self.bucket_name}/{filename}",
                bytes_written=len(content_bytes),
                strategy_used="multipart",
                parts_count=len(manifest["parts"]),
            )

        except ClientError as e:
            raise RuntimeError(f"Failed to append using multipart strategy: {e}")

    def _convert_to_multipart(
        self, filename: str, new_content: bytes, part_size_mb: int
    ) -> AppendResult:
        """Convert existing single file to multipart format."""
        try:
            # Download existing file
            existing_obj = self.s3.get_object(Bucket=self.bucket_name, Key=filename)
            existing_content = existing_obj["Body"].read()

            # Create manifest
            content_type = existing_obj.get("ContentType", "application/octet-stream")
            manifest = self.manifest_manager.create_manifest(
                base_name=filename,
                content_type=content_type
            )

            # Upload existing content as first part
            part_name = self.manifest_manager.get_next_part_name(filename, manifest)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=part_name,
                Body=existing_content
            )

            # Update manifest with first part
            manifest = self.manifest_manager.add_part(
                manifest, part_name, len(existing_content)
            )

            # Upload new content as second part
            part_name = self.manifest_manager.get_next_part_name(filename, manifest)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=part_name,
                Body=new_content
            )

            # Update manifest with second part
            manifest = self.manifest_manager.add_part(
                manifest, part_name, len(new_content)
            )

            # Save manifest
            manifest_key = f"{filename}.manifest"
            manifest_bytes = self.manifest_manager.serialize_manifest(manifest)
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=manifest_key,
                Body=manifest_bytes
            )

            # Delete original file (now replaced by parts)
            self.s3.delete_object(Bucket=self.bucket_name, Key=filename)

            return AppendResult(
                path=f"s3://{self.bucket_name}/{filename}",
                bytes_written=len(new_content),
                strategy_used="multipart",
                parts_count=2,
            )

        except ClientError as e:
            raise RuntimeError(f"Failed to convert to multipart: {e}")
