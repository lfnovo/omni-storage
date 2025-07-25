"""Google Cloud Storage implementation."""

from typing import BinaryIO, Literal, Union

from google.cloud import storage

from .base import Storage
from .manifest import ManifestManager
from .types import AppendResult


class GCSStorage(Storage):
    """Google Cloud Storage implementation."""

    def __init__(self, bucket_name: str):
        """Initialize GCS storage.

        Args:
            bucket_name: Name of the GCS bucket
        """
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name
        self.manifest_manager = ManifestManager()

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
        """Read file from GCS, handling both single files and manifest-based multipart files."""
        # Remove gs:// prefix if present
        if file_path.startswith("gs://"):
            # Extract just the object path after bucket name
            file_path = file_path.split("/", 3)[-1]

        try:
            # First, check if a manifest exists
            manifest_key = f"{file_path}.manifest"
            manifest_blob = self.bucket.blob(manifest_key)
            
            if manifest_blob.exists():
                manifest_content = manifest_blob.download_as_bytes()
                
                # It's a multipart file - read all parts
                try:
                    manifest = self.manifest_manager.read_manifest(manifest_content)
                    return self._read_multipart_file(manifest)
                except ValueError:
                    # Invalid manifest, fall back to direct read
                    pass

            # Read as single file
            blob = self.bucket.blob(file_path)
            return blob.download_as_bytes()
        except Exception as e:
            raise RuntimeError(f"Failed to read file from GCS: {e}")

    def _read_multipart_file(self, manifest: dict) -> bytes:
        """Read and concatenate all parts of a multipart file."""
        parts = self.manifest_manager.get_parts_in_order(manifest)
        content_parts = []

        for part in parts:
            try:
                part_blob = self.bucket.blob(part["name"])
                content_parts.append(part_blob.download_as_bytes())
            except Exception as e:
                raise RuntimeError(f"Failed to read part {part['name']}: {e}")

        return b"".join(content_parts)

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

    def append_file(
        self,
        content: Union[str, bytes, BinaryIO],
        filename: str,
        create_if_not_exists: bool = True,
        strategy: Literal["auto", "single", "multipart"] = "auto",
        part_size_mb: int = 100,
    ) -> AppendResult:
        """
        Append content to a file in GCS.

        GCS supports compose operation for combining up to 32 objects.
        For larger files, we use manifest-based multipart pattern.

        Args:
            content: Content to append (str, bytes, or file-like object)
            filename: GCS blob name of the file to append to
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
            raise FileNotFoundError(f"File {filename} does not exist in GCS")

        # Determine strategy
        if strategy == "auto":
            # Auto-select based on file existence and size
            if file_exists:
                try:
                    blob = self.bucket.blob(filename)
                    blob.reload()  # Load metadata
                    file_size = blob.size or 0
                    
                    # Check if it's already a manifest
                    if file_size < 10 * 1024 * 1024:  # Small files < 10MB, check content
                        first_bytes = blob.download_as_bytes(start=0, end=1024)
                        
                        if self.manifest_manager.is_manifest_file(first_bytes):
                            strategy = "multipart"
                        else:
                            # Use multipart if file is larger than threshold
                            strategy = "multipart" if file_size >= part_size_mb * 1024 * 1024 else "single"
                    else:
                        # Large files always use multipart
                        strategy = "multipart"
                except Exception:
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
            blob = self.bucket.blob(filename)
            
            if file_exists:
                # Download existing content
                existing_content = blob.download_as_bytes()
                combined_content = existing_content + content_bytes
            else:
                # New file
                combined_content = content_bytes

            # Upload the combined content
            blob.upload_from_string(combined_content)

            return AppendResult(
                path=f"gs://{self.bucket_name}/{filename}",
                bytes_written=len(content_bytes),
                strategy_used="single",
                parts_count=1,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to append to file in GCS: {e}")

    def _append_multipart_strategy(
        self, filename: str, content_bytes: bytes, file_exists: bool, part_size_mb: int
    ) -> AppendResult:
        """Implement multipart append strategy using manifest files."""
        try:
            manifest_key = f"{filename}.manifest"
            
            # Load or create manifest
            if file_exists:
                # Check if manifest exists
                manifest_blob = self.bucket.blob(manifest_key)
                if manifest_blob.exists():
                    manifest_content = manifest_blob.download_as_bytes()
                    manifest = self.manifest_manager.read_manifest(manifest_content)
                else:
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

            # Check if we need to compact parts (GCS compose limit is 32)
            if len(manifest["parts"]) >= 30:
                manifest = self._compact_parts(filename, manifest)

            # Generate part name and upload
            part_name = self.manifest_manager.get_next_part_name(filename, manifest)
            part_blob = self.bucket.blob(part_name)
            part_blob.upload_from_string(content_bytes)

            # Update manifest
            manifest = self.manifest_manager.add_part(
                manifest, part_name, len(content_bytes)
            )

            # Save updated manifest
            manifest_bytes = self.manifest_manager.serialize_manifest(manifest)
            manifest_blob = self.bucket.blob(manifest_key)
            manifest_blob.upload_from_string(manifest_bytes)

            return AppendResult(
                path=f"gs://{self.bucket_name}/{filename}",
                bytes_written=len(content_bytes),
                strategy_used="multipart",
                parts_count=len(manifest["parts"]),
            )

        except Exception as e:
            raise RuntimeError(f"Failed to append using multipart strategy: {e}")

    def _convert_to_multipart(
        self, filename: str, new_content: bytes, part_size_mb: int
    ) -> AppendResult:
        """Convert existing single file to multipart format."""
        try:
            # Download existing file
            blob = self.bucket.blob(filename)
            existing_content = blob.download_as_bytes()

            # Create manifest
            blob.reload()  # Get metadata
            content_type = blob.content_type or "application/octet-stream"
            manifest = self.manifest_manager.create_manifest(
                base_name=filename,
                content_type=content_type
            )

            # Upload existing content as first part
            part_name = self.manifest_manager.get_next_part_name(filename, manifest)
            part_blob = self.bucket.blob(part_name)
            part_blob.upload_from_string(existing_content)

            # Update manifest with first part
            manifest = self.manifest_manager.add_part(
                manifest, part_name, len(existing_content)
            )

            # Upload new content as second part
            part_name = self.manifest_manager.get_next_part_name(filename, manifest)
            part_blob = self.bucket.blob(part_name)
            part_blob.upload_from_string(new_content)

            # Update manifest with second part
            manifest = self.manifest_manager.add_part(
                manifest, part_name, len(new_content)
            )

            # Save manifest
            manifest_key = f"{filename}.manifest"
            manifest_bytes = self.manifest_manager.serialize_manifest(manifest)
            manifest_blob = self.bucket.blob(manifest_key)
            manifest_blob.upload_from_string(manifest_bytes)

            # Delete original file (now replaced by parts)
            blob.delete()

            return AppendResult(
                path=f"gs://{self.bucket_name}/{filename}",
                bytes_written=len(new_content),
                strategy_used="multipart",
                parts_count=2,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to convert to multipart: {e}")

    def _compact_parts(self, filename: str, manifest: dict) -> dict:
        """Compact multiple parts into fewer parts using GCS compose."""
        # This handles GCS compose limit of 32 objects
        # For simplicity in this implementation, we'll raise an error
        # In production, you'd compose existing parts into larger parts
        raise RuntimeError(
            f"File {filename} has reached the part limit. "
            "Consider implementing part compaction for production use."
        )
