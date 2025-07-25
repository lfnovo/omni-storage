"""Tests for append_file functionality across storage backends."""

import json
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from omni_storage.gcs import GCSStorage
from omni_storage.local import LocalStorage
from omni_storage.s3 import S3Storage
from omni_storage.types import AppendResult


class TestLocalStorageAppend:
    """Test LocalStorage append_file implementation."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary LocalStorage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            yield storage, tmpdir

    def test_append_to_new_file_text(self, temp_storage):
        """Test appending text to a new file."""
        storage, tmpdir = temp_storage

        result = storage.append_file("Hello, World!", "test.txt")

        assert isinstance(result, AppendResult)
        assert result.bytes_written == 13  # len("Hello, World!".encode("utf-8"))
        assert result.strategy_used == "single"
        assert result.parts_count == 1
        assert "test.txt" in result.path

        # Verify content
        content = storage.read_file("test.txt")
        assert content == b"Hello, World!"

    def test_append_to_existing_file_text(self, temp_storage):
        """Test appending text to an existing file."""
        storage, tmpdir = temp_storage

        # Create initial file
        storage.save_file(b"Hello", "test.txt")

        # Append to it
        result = storage.append_file(", World!", "test.txt")

        assert result.bytes_written == 8  # len(", World!".encode("utf-8"))

        # Verify content
        content = storage.read_file("test.txt")
        assert content == b"Hello, World!"

    def test_append_binary_content(self, temp_storage):
        """Test appending binary content."""
        storage, tmpdir = temp_storage

        binary_data = b"\x00\x01\x02\x03"
        result = storage.append_file(binary_data, "binary.bin")

        assert result.bytes_written == 4
        assert result.strategy_used == "single"

        # Append more binary data
        more_data = b"\x04\x05\x06\x07"
        result2 = storage.append_file(more_data, "binary.bin")

        assert result2.bytes_written == 4

        # Verify combined content
        content = storage.read_file("binary.bin")
        assert content == binary_data + more_data

    def test_append_from_stringio(self, temp_storage):
        """Test appending from StringIO file-like object."""
        storage, tmpdir = temp_storage

        # Create StringIO
        string_buffer = StringIO("This is from StringIO")

        result = storage.append_file(string_buffer, "stringio.txt")

        assert result.bytes_written == 21  # UTF-8 encoded length

        # Verify content
        content = storage.read_file("stringio.txt")
        assert content == b"This is from StringIO"

    def test_append_from_bytesio(self, temp_storage):
        """Test appending from BytesIO file-like object."""
        storage, tmpdir = temp_storage

        # Create BytesIO
        bytes_buffer = BytesIO(b"Binary from BytesIO")

        result = storage.append_file(bytes_buffer, "bytesio.bin")

        assert result.bytes_written == 19

        # Verify content
        content = storage.read_file("bytesio.bin")
        assert content == b"Binary from BytesIO"

    def test_append_multiple_times(self, temp_storage):
        """Test multiple append operations."""
        storage, tmpdir = temp_storage

        # First append
        storage.append_file("Line 1\n", "multi.txt")

        # Second append
        storage.append_file("Line 2\n", "multi.txt")

        # Third append
        storage.append_file("Line 3\n", "multi.txt")

        # Verify content
        content = storage.read_file("multi.txt")
        assert content == b"Line 1\nLine 2\nLine 3\n"

    def test_append_with_nested_directories(self, temp_storage):
        """Test appending to files in nested directories."""
        storage, tmpdir = temp_storage

        result = storage.append_file("Nested content", "path/to/nested/file.txt")

        assert result.bytes_written == 14
        assert storage.exists("path/to/nested/file.txt")

        # Verify directory structure was created
        full_path = Path(tmpdir) / "path" / "to" / "nested" / "file.txt"
        assert full_path.exists()

    def test_append_create_if_not_exists_false(self, temp_storage):
        """Test FileNotFoundError when create_if_not_exists=False."""
        storage, tmpdir = temp_storage

        with pytest.raises(FileNotFoundError) as exc_info:
            storage.append_file(
                "Content", "nonexistent.txt", create_if_not_exists=False
            )

        assert "nonexistent.txt" in str(exc_info.value)

    def test_append_create_if_not_exists_false_existing(self, temp_storage):
        """Test append succeeds when file exists and create_if_not_exists=False."""
        storage, tmpdir = temp_storage

        # Create file first
        storage.save_file(b"Initial", "existing.txt")

        # Should succeed
        result = storage.append_file(
            " content", "existing.txt", create_if_not_exists=False
        )

        assert result.bytes_written == 8
        content = storage.read_file("existing.txt")
        assert content == b"Initial content"

    def test_append_unicode_content(self, temp_storage):
        """Test appending Unicode content."""
        storage, tmpdir = temp_storage

        unicode_text = "Hello 世界 🌍"
        result = storage.append_file(unicode_text, "unicode.txt")

        # UTF-8 encoding of this string is longer than character count
        assert result.bytes_written == len(unicode_text.encode("utf-8"))

        content = storage.read_file("unicode.txt")
        assert content.decode("utf-8") == unicode_text

    def test_append_empty_content(self, temp_storage):
        """Test appending empty content."""
        storage, tmpdir = temp_storage

        # Empty string
        result = storage.append_file("", "empty.txt")
        assert result.bytes_written == 0
        assert storage.exists("empty.txt")

        # Empty bytes
        result = storage.append_file(b"", "empty.txt")
        assert result.bytes_written == 0

        # Empty BytesIO
        result = storage.append_file(BytesIO(b""), "empty.txt")
        assert result.bytes_written == 0

    def test_append_invalid_content_type(self, temp_storage):
        """Test error with invalid content type."""
        storage, tmpdir = temp_storage

        with pytest.raises(ValueError) as exc_info:
            storage.append_file(12345, "invalid.txt")  # type: ignore

        assert "not supported" in str(exc_info.value)

    def test_append_file_like_without_read(self, temp_storage):
        """Test error when file-like object doesn't have read method."""
        storage, tmpdir = temp_storage

        class FakeFile:
            pass

        with pytest.raises(ValueError) as exc_info:
            storage.append_file(FakeFile(), "fake.txt")  # type: ignore

        assert "not supported" in str(exc_info.value)

    def test_append_preserves_existing_content(self, temp_storage):
        """Test that append doesn't overwrite existing content."""
        storage, tmpdir = temp_storage

        # Create file with initial content
        initial = "Initial content\n"
        storage.save_file(initial.encode("utf-8"), "preserve.txt")

        # Append more content
        appended = "Appended content\n"
        storage.append_file(appended, "preserve.txt")

        # Verify both contents are present
        content = storage.read_file("preserve.txt")
        assert content == (initial + appended).encode("utf-8")

    def test_strategy_parameter_ignored(self, temp_storage):
        """Test that strategy parameter is ignored for LocalStorage."""
        storage, tmpdir = temp_storage

        # Try different strategies - all should use "single"
        for strategy in ["auto", "single", "multipart"]:
            result = storage.append_file(
                f"Strategy: {strategy}\n",
                "strategies.txt",
                strategy=strategy,  # type: ignore
            )
            assert result.strategy_used == "single"

    def test_part_size_mb_ignored(self, temp_storage):
        """Test that part_size_mb parameter is ignored for LocalStorage."""
        storage, tmpdir = temp_storage

        result = storage.append_file(
            "Content",
            "partsize.txt",
            part_size_mb=1,  # Should be ignored
        )

        assert result.strategy_used == "single"
        assert result.parts_count == 1


class TestS3StorageAppend:
    """Test S3Storage append_file implementation."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_boto.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def s3_storage(self, mock_s3_client):
        """Create S3Storage instance with mocked client."""
        return S3Storage("test-bucket", "us-east-1")

    def test_append_to_new_file(self, s3_storage, mock_s3_client):
        """Test appending to a new file in S3."""
        # Mock file doesn't exist
        mock_s3_client.head_object.side_effect = Exception("Not found")

        result = s3_storage.append_file("Hello S3!", "new-file.txt")

        assert isinstance(result, AppendResult)
        assert result.bytes_written == 9
        assert result.strategy_used == "single"
        assert result.parts_count == 1
        assert result.path == "s3://test-bucket/new-file.txt"

        # Verify S3 API calls
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="new-file.txt"
        )
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="new-file.txt", Body=b"Hello S3!"
        )

    def test_append_to_existing_file(self, s3_storage, mock_s3_client):
        """Test appending to an existing file in S3."""
        # Mock file exists with small size (triggers single strategy)
        mock_s3_client.head_object.side_effect = [
            {"ContentLength": 100},  # File exists check
            {"ContentLength": 100},  # Size check
        ]

        # Mock existing content - not a manifest
        mock_body1 = MagicMock()
        mock_body1.read.return_value = b"Existing"  # First 1KB check
        mock_body1.close = MagicMock()
        
        mock_body2 = MagicMock()
        mock_body2.read.return_value = b"Existing content"
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_body1},  # Content check
            {"Body": mock_body2},  # Actual read
        ]

        result = s3_storage.append_file(" + new content", "existing.txt")

        assert result.bytes_written == 14  # len(" + new content")
        assert result.strategy_used == "single"

        # Verify put_object was called with combined content
        put_calls = [call for call in mock_s3_client.put_object.call_args_list
                     if call[1]["Key"] == "existing.txt"]
        assert len(put_calls) == 1
        assert put_calls[0][1]["Body"] == b"Existing content + new content"

    def test_append_binary_content(self, s3_storage, mock_s3_client):
        """Test appending binary content to S3."""
        mock_s3_client.head_object.side_effect = Exception("Not found")

        binary_data = b"\x00\x01\x02\x03"
        result = s3_storage.append_file(binary_data, "binary.bin")

        assert result.bytes_written == 4
        mock_s3_client.put_object.assert_called_with(
            Bucket="test-bucket", Key="binary.bin", Body=binary_data
        )

    def test_append_from_file_like_object(self, s3_storage, mock_s3_client):
        """Test appending from file-like objects."""
        mock_s3_client.head_object.side_effect = Exception("Not found")

        # Test StringIO
        string_buffer = StringIO("String content")
        result = s3_storage.append_file(string_buffer, "string.txt")
        assert result.bytes_written == 14

        # Test BytesIO
        bytes_buffer = BytesIO(b"Binary content")
        result = s3_storage.append_file(bytes_buffer, "binary.bin")
        assert result.bytes_written == 14

    def test_append_create_if_not_exists_false(self, s3_storage, mock_s3_client):
        """Test FileNotFoundError when create_if_not_exists=False."""
        # Mock file doesn't exist
        mock_s3_client.head_object.side_effect = Exception("Not found")

        with pytest.raises(FileNotFoundError) as exc_info:
            s3_storage.append_file("Content", "missing.txt", create_if_not_exists=False)

        assert "missing.txt" in str(exc_info.value)
        # Should not attempt to upload
        mock_s3_client.put_object.assert_not_called()

    def test_append_s3_error_handling(self, s3_storage, mock_s3_client):
        """Test error handling for S3 operations."""
        from botocore.exceptions import ClientError

        # Mock S3 error
        mock_s3_client.head_object.side_effect = Exception("Not found")
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "PutObject"
        )

        with pytest.raises(RuntimeError) as exc_info:
            s3_storage.append_file("Content", "error.txt")

        assert "Failed to append to file in S3" in str(exc_info.value)

    def test_append_multipart_strategy_new_file(self, s3_storage, mock_s3_client):
        """Test multipart strategy for new file."""
        # Mock file doesn't exist
        mock_s3_client.head_object.side_effect = Exception("Not found")
        
        result = s3_storage.append_file("First part", "data.csv", strategy="multipart")
        
        assert result.strategy_used == "multipart"
        assert result.parts_count == 1
        
        # Verify manifest was created
        manifest_calls = [
            call for call in mock_s3_client.put_object.call_args_list
            if call[1]["Key"] == "data.csv.manifest"
        ]
        assert len(manifest_calls) == 1
        
        # Verify part was created
        part_calls = [
            call for call in mock_s3_client.put_object.call_args_list
            if "data-part-" in call[1]["Key"]
        ]
        assert len(part_calls) == 1

    def test_append_invalid_content_type(self, s3_storage, mock_s3_client):
        """Test error with invalid content type."""
        with pytest.raises(ValueError) as exc_info:
            s3_storage.append_file(12345, "invalid.txt")  # type: ignore

        assert "not supported" in str(exc_info.value)

    def test_append_to_manifest_file(self, s3_storage, mock_s3_client):
        """Test appending to a file that happens to be a manifest."""
        # Mock small file exists
        mock_s3_client.head_object.side_effect = [
            {"ContentLength": 100},  # File exists check
            {"ContentLength": 100},  # Size check - small file
        ]
        
        # Mock content that looks like a manifest
        manifest_content = b'{"type": "omni-storage-manifest", "parts": [], "total_size": 0}'
        mock_body1 = MagicMock()
        mock_body1.read.return_value = manifest_content[:100]  # First 1KB
        mock_body1.close = MagicMock()
        
        # Mock manifest exists (multipart strategy will check)
        mock_manifest_body = MagicMock()
        mock_manifest_body.read.return_value = manifest_content
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_body1},  # Content check - is manifest
            {"Body": mock_manifest_body},  # Read manifest for multipart
        ]

        # Append should use multipart strategy
        result = s3_storage.append_file(b"New data", "data.json")

        assert result.strategy_used == "multipart"
        assert result.parts_count == 1

    def test_append_multiple_times(self, s3_storage, mock_s3_client):
        """Test multiple append operations with single strategy."""
        # Reset mock
        mock_s3_client.reset_mock()
        
        # First append (new file)
        mock_s3_client.head_object.side_effect = Exception("Not found")
        s3_storage.append_file("Line 1\n", "multi.txt")
        
        # Second append - file exists now
        mock_s3_client.head_object.side_effect = [
            {"ContentLength": 7},  # File exists
            {"ContentLength": 7},  # Size check - small
        ]
        
        mock_body1 = MagicMock()
        mock_body1.read.return_value = b"Line 1"  # First 1KB
        mock_body1.close = MagicMock()
        
        mock_body2 = MagicMock()
        mock_body2.read.return_value = b"Line 1\n"
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_body1},  # Content check
            {"Body": mock_body2},  # Actual read
        ]
        
        s3_storage.append_file("Line 2\n", "multi.txt")
        
        # Third append
        mock_s3_client.head_object.side_effect = [
            {"ContentLength": 14},  # File exists
            {"ContentLength": 14},  # Size check - small
        ]
        
        mock_body3 = MagicMock()
        mock_body3.read.return_value = b"Line 1\nL"  # First 1KB
        mock_body3.close = MagicMock()
        
        mock_body4 = MagicMock()
        mock_body4.read.return_value = b"Line 1\nLine 2\n"
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_body3},  # Content check
            {"Body": mock_body4},  # Actual read
        ]
        
        s3_storage.append_file("Line 3\n", "multi.txt")

        # Verify all put_object calls
        put_calls = [call for call in mock_s3_client.put_object.call_args_list
                     if call[1]["Key"] == "multi.txt"]
        assert len(put_calls) == 3
        
        # Check contents
        assert put_calls[0][1]["Body"] == b"Line 1\n"
        assert put_calls[1][1]["Body"] == b"Line 1\nLine 2\n"
        assert put_calls[2][1]["Body"] == b"Line 1\nLine 2\nLine 3\n"

    def test_append_to_existing_manifest_file(self, s3_storage, mock_s3_client):
        """Test appending to existing multipart file with manifest."""
        # Mock file exists
        mock_s3_client.head_object.return_value = {"ContentLength": 200}
        
        # Mock manifest exists with one part
        manifest_data = {
            "version": "1.0",
            "type": "omni-storage-manifest",
            "base_name": "data.csv",
            "parts": [
                {"name": "data-part-001.csv", "size": 100, "created": "2024-01-01T00:00:00Z"}
            ],
            "total_size": 100,
            "content_type": "text/csv",
            "encoding": "utf-8"
        }
        manifest_json = json.dumps(manifest_data).encode("utf-8")
        
        # Set up mocks
        mock_manifest_body = MagicMock()
        mock_manifest_body.read.return_value = manifest_json
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_manifest_body},  # Manifest read
        ]
        
        # Append new content
        result = s3_storage.append_file("Second part", "data.csv", strategy="multipart")
        
        assert result.strategy_used == "multipart"
        assert result.parts_count == 2
        
        # Verify new part was uploaded
        part_calls = [
            call for call in mock_s3_client.put_object.call_args_list
            if call[1]["Key"] == "data-part-002.csv"
        ]
        assert len(part_calls) == 1
        assert part_calls[0][1]["Body"] == b"Second part"

    def test_convert_single_to_multipart(self, s3_storage, mock_s3_client):
        """Test converting single file to multipart on size threshold."""
        # Mock large file exists
        mock_s3_client.head_object.side_effect = [
            {"ContentLength": 100},  # First check - file exists
            {"ContentLength": 150 * 1024 * 1024},  # Second check - large file
        ]
        
        # Mock no manifest exists
        mock_s3_client.get_object.side_effect = [
            ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject"),  # No manifest
            {"Body": MagicMock(read=lambda: b"Existing large content")},  # Original file
        ]
        
        # Append with auto strategy
        result = s3_storage.append_file("New content", "large.bin", part_size_mb=100)
        
        assert result.strategy_used == "multipart"
        assert result.parts_count == 2
        
        # Verify delete was called on original file
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="large.bin"
        )
        
        # Verify manifest was created
        manifest_calls = [
            call for call in mock_s3_client.put_object.call_args_list
            if call[1]["Key"] == "large.bin.manifest"
        ]
        assert len(manifest_calls) == 1

    def test_read_file_with_manifest(self, s3_storage, mock_s3_client):
        """Test reading a multipart file transparently."""
        # Mock manifest
        manifest_data = {
            "version": "1.0",
            "type": "omni-storage-manifest",
            "base_name": "data.csv",
            "parts": [
                {"name": "data-part-001.csv", "size": 7, "created": "2024-01-01T00:00:00Z"},
                {"name": "data-part-002.csv", "size": 8, "created": "2024-01-01T01:00:00Z"}
            ],
            "total_size": 15
        }
        manifest_json = json.dumps(manifest_data).encode("utf-8")
        
        # Mock responses
        mock_manifest_body = MagicMock()
        mock_manifest_body.read.return_value = manifest_json
        
        mock_part1_body = MagicMock()
        mock_part1_body.read.return_value = b"Part 1\n"
        
        mock_part2_body = MagicMock()
        mock_part2_body.read.return_value = b"Part 2\n"
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_manifest_body},  # Manifest
            {"Body": mock_part1_body},     # Part 1
            {"Body": mock_part2_body},     # Part 2
        ]
        
        # Read file
        content = s3_storage.read_file("data.csv")
        
        assert content == b"Part 1\nPart 2\n"
        
        # Verify correct files were read
        assert mock_s3_client.get_object.call_count == 3

    def test_read_file_no_manifest_fallback(self, s3_storage, mock_s3_client):
        """Test reading single file when no manifest exists."""
        # Mock no manifest, but file exists
        mock_file_body = MagicMock()
        mock_file_body.read.return_value = b"Single file content"
        
        mock_s3_client.get_object.side_effect = [
            ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject"),  # No manifest
            {"Body": mock_file_body},  # Regular file
        ]
        
        content = s3_storage.read_file("single.txt")
        
        assert content == b"Single file content"

    def test_auto_strategy_detects_manifest(self, s3_storage, mock_s3_client):
        """Test auto strategy detects existing manifest files."""
        # Mock small file that is a manifest
        mock_s3_client.head_object.side_effect = [
            {"ContentLength": 100},  # File exists check
            {"ContentLength": 500},  # Size check - small file
        ]
        
        # Mock file content is a manifest with proper structure
        manifest_json = b'{"type": "omni-storage-manifest", "parts": [], "total_size": 0, "base_name": "data.json"}'
        mock_body = MagicMock()
        mock_body.read.return_value = manifest_json
        mock_body.close = MagicMock()
        
        mock_manifest_body = MagicMock()
        mock_manifest_body.read.return_value = manifest_json
        
        mock_s3_client.get_object.side_effect = [
            {"Body": mock_body},  # Check content
            {"Body": mock_manifest_body},  # Read manifest for append
        ]
        
        result = s3_storage.append_file("New part", "data.json")
        
        # Should use multipart strategy
        assert result.strategy_used == "multipart"
        assert result.parts_count == 1


class TestGCSStorageAppend:
    """Test GCSStorage append_file implementation."""

    @pytest.fixture
    def mock_storage_client(self):
        """Create a mock GCS storage client."""
        with patch("omni_storage.gcs.storage.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_client.bucket.return_value = mock_bucket
            mock_client_class.return_value = mock_client
            yield mock_client, mock_bucket

    @pytest.fixture
    def gcs_storage(self, mock_storage_client):
        """Create GCSStorage instance with mocked client."""
        return GCSStorage("test-bucket")

    def test_append_to_new_file(self, gcs_storage, mock_storage_client):
        """Test appending to a new file in GCS."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock file doesn't exist
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob

        result = gcs_storage.append_file("Hello GCS!", "new-file.txt")

        assert isinstance(result, AppendResult)
        assert result.bytes_written == 10
        assert result.strategy_used == "single"
        assert result.parts_count == 1
        assert result.path == "gs://test-bucket/new-file.txt"

        # Verify GCS API calls
        mock_blob.upload_from_string.assert_called_once_with(b"Hello GCS!")

    def test_append_to_existing_file(self, gcs_storage, mock_storage_client):
        """Test appending to an existing file in GCS."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock file exists with small size
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.size = 100
        mock_blob.download_as_bytes.side_effect = [
            b"Existing",  # First 1KB check (for auto strategy)
            b"Existing content",  # Full download
        ]
        mock_bucket.blob.return_value = mock_blob

        result = gcs_storage.append_file(" + new content", "existing.txt")

        assert result.bytes_written == 14
        assert result.strategy_used == "single"

        # Verify combined content was uploaded
        mock_blob.upload_from_string.assert_called_with(b"Existing content + new content")

    def test_append_binary_content(self, gcs_storage, mock_storage_client):
        """Test appending binary content to GCS."""
        mock_client, mock_bucket = mock_storage_client
        
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob

        binary_data = b"\x00\x01\x02\x03"
        result = gcs_storage.append_file(binary_data, "binary.bin")

        assert result.bytes_written == 4
        mock_blob.upload_from_string.assert_called_with(binary_data)

    def test_append_from_file_like_object(self, gcs_storage, mock_storage_client):
        """Test appending from file-like objects."""
        mock_client, mock_bucket = mock_storage_client
        
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob

        # Test StringIO
        string_buffer = StringIO("String content")
        result = gcs_storage.append_file(string_buffer, "string.txt")
        assert result.bytes_written == 14

        # Test BytesIO
        bytes_buffer = BytesIO(b"Binary content")
        result = gcs_storage.append_file(bytes_buffer, "binary.bin")
        assert result.bytes_written == 14

    def test_append_create_if_not_exists_false(self, gcs_storage, mock_storage_client):
        """Test FileNotFoundError when create_if_not_exists=False."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock file doesn't exist
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob

        with pytest.raises(FileNotFoundError) as exc_info:
            gcs_storage.append_file("Content", "missing.txt", create_if_not_exists=False)

        assert "missing.txt" in str(exc_info.value)
        # Should not attempt to upload
        mock_blob.upload_from_string.assert_not_called()

    def test_append_gcs_error_handling(self, gcs_storage, mock_storage_client):
        """Test error handling for GCS operations."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock GCS error
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_blob.upload_from_string.side_effect = Exception("Permission denied")
        mock_bucket.blob.return_value = mock_blob

        with pytest.raises(RuntimeError) as exc_info:
            gcs_storage.append_file("Content", "error.txt")

        assert "Failed to append to file in GCS" in str(exc_info.value)

    def test_append_multipart_strategy_new_file(self, gcs_storage, mock_storage_client):
        """Test multipart strategy for new file."""
        mock_client, mock_bucket = mock_storage_client
        
        # Setup mocks for blobs
        file_blob = MagicMock()
        file_blob.exists.return_value = False
        
        manifest_blob = MagicMock()
        part_blob = MagicMock()
        
        # Return different blobs based on the key
        def get_blob(key):
            if key.endswith(".manifest"):
                return manifest_blob
            elif "part-" in key:
                return part_blob
            else:
                return file_blob
        
        mock_bucket.blob.side_effect = get_blob
        
        result = gcs_storage.append_file("First part", "data.csv", strategy="multipart")
        
        assert result.strategy_used == "multipart"
        assert result.parts_count == 1
        
        # Verify manifest was created
        manifest_calls = [c for c in manifest_blob.upload_from_string.call_args_list]
        assert len(manifest_calls) == 1
        
        # Verify part was created
        part_calls = [c for c in part_blob.upload_from_string.call_args_list]
        assert len(part_calls) == 1
        assert part_calls[0][0][0] == b"First part"

    def test_append_invalid_content_type(self, gcs_storage, mock_storage_client):
        """Test error with invalid content type."""
        with pytest.raises(ValueError) as exc_info:
            gcs_storage.append_file(12345, "invalid.txt")  # type: ignore

        assert "not supported" in str(exc_info.value)

    def test_append_to_existing_manifest_file(self, gcs_storage, mock_storage_client):
        """Test appending to existing multipart file with manifest."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock file exists
        file_blob = MagicMock()
        file_blob.exists.return_value = True
        
        # Mock manifest exists with one part
        manifest_data = {
            "version": "1.0",
            "type": "omni-storage-manifest",
            "base_name": "data.csv",
            "parts": [
                {"name": "data-part-001.csv", "size": 100, "created": "2024-01-01T00:00:00Z"}
            ],
            "total_size": 100,
            "content_type": "text/csv",
            "encoding": "utf-8"
        }
        manifest_json = json.dumps(manifest_data).encode("utf-8")
        
        manifest_blob = MagicMock()
        manifest_blob.exists.return_value = True
        manifest_blob.download_as_bytes.return_value = manifest_json
        
        part_blob = MagicMock()
        
        # Return different blobs based on the key
        def get_blob(key):
            if key == "data.csv.manifest":
                return manifest_blob
            elif "part-" in key:
                return part_blob
            else:
                return file_blob
        
        mock_bucket.blob.side_effect = get_blob
        
        # Append new content
        result = gcs_storage.append_file("Second part", "data.csv", strategy="multipart")
        
        assert result.strategy_used == "multipart"
        assert result.parts_count == 2
        
        # Verify new part was uploaded
        part_calls = [c for c in part_blob.upload_from_string.call_args_list]
        assert len(part_calls) == 1
        assert part_calls[0][0][0] == b"Second part"

    def test_convert_single_to_multipart(self, gcs_storage, mock_storage_client):
        """Test converting single file to multipart on size threshold."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock large file exists
        file_blob = MagicMock()
        file_blob.exists.return_value = True
        file_blob.size = 150 * 1024 * 1024  # 150MB
        file_blob.content_type = "application/octet-stream"
        file_blob.download_as_bytes.return_value = b"Existing large content"
        
        # Mock no manifest exists
        manifest_blob = MagicMock()
        manifest_blob.exists.return_value = False
        
        part_blob = MagicMock()
        
        # Return different blobs based on the key
        def get_blob(key):
            if key.endswith(".manifest"):
                return manifest_blob
            elif "part-" in key:
                return part_blob
            else:
                return file_blob
        
        mock_bucket.blob.side_effect = get_blob
        
        # Append with auto strategy
        result = gcs_storage.append_file("New content", "large.bin", part_size_mb=100)
        
        assert result.strategy_used == "multipart"
        assert result.parts_count == 2
        
        # Verify delete was called on original file
        file_blob.delete.assert_called_once()
        
        # Verify manifest was created
        manifest_calls = [c for c in manifest_blob.upload_from_string.call_args_list]
        assert len(manifest_calls) == 1

    def test_read_file_with_manifest(self, gcs_storage, mock_storage_client):
        """Test reading a multipart file transparently."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock manifest
        manifest_data = {
            "version": "1.0",
            "type": "omni-storage-manifest",
            "base_name": "data.csv",
            "parts": [
                {"name": "data-part-001.csv", "size": 7, "created": "2024-01-01T00:00:00Z"},
                {"name": "data-part-002.csv", "size": 8, "created": "2024-01-01T01:00:00Z"}
            ],
            "total_size": 15
        }
        manifest_json = json.dumps(manifest_data).encode("utf-8")
        
        # Mock manifest blob
        manifest_blob = MagicMock()
        manifest_blob.exists.return_value = True
        manifest_blob.download_as_bytes.return_value = manifest_json
        
        # Mock part blobs
        part1_blob = MagicMock()
        part1_blob.download_as_bytes.return_value = b"Part 1\n"
        
        part2_blob = MagicMock()
        part2_blob.download_as_bytes.return_value = b"Part 2\n"
        
        # Return different blobs based on the key
        def get_blob(key):
            if key == "data.csv.manifest":
                return manifest_blob
            elif key == "data-part-001.csv":
                return part1_blob
            elif key == "data-part-002.csv":
                return part2_blob
            else:
                return MagicMock()
        
        mock_bucket.blob.side_effect = get_blob
        
        # Read file
        content = gcs_storage.read_file("data.csv")
        
        assert content == b"Part 1\nPart 2\n"

    def test_read_file_no_manifest_fallback(self, gcs_storage, mock_storage_client):
        """Test reading single file when no manifest exists."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock no manifest
        manifest_blob = MagicMock()
        manifest_blob.exists.return_value = False
        
        # Mock regular file
        file_blob = MagicMock()
        file_blob.download_as_bytes.return_value = b"Single file content"
        
        # Return different blobs based on the key
        def get_blob(key):
            if key.endswith(".manifest"):
                return manifest_blob
            else:
                return file_blob
        
        mock_bucket.blob.side_effect = get_blob
        
        content = gcs_storage.read_file("single.txt")
        
        assert content == b"Single file content"

    def test_auto_strategy_detects_manifest(self, gcs_storage, mock_storage_client):
        """Test auto strategy detects existing manifest files."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock small file that is a manifest
        file_blob = MagicMock()
        file_blob.exists.return_value = True
        file_blob.size = 500
        
        # Mock file content is a manifest
        manifest_json = b'{"type": "omni-storage-manifest", "parts": [], "total_size": 0, "base_name": "data.json"}'
        file_blob.download_as_bytes.return_value = manifest_json
        
        # Mock manifest exists
        manifest_blob = MagicMock()
        manifest_blob.exists.return_value = True
        manifest_blob.download_as_bytes.return_value = manifest_json
        
        part_blob = MagicMock()
        
        # Return different blobs based on the key
        def get_blob(key):
            if key.endswith(".manifest"):
                return manifest_blob
            elif "part-" in key:
                return part_blob
            else:
                return file_blob
        
        mock_bucket.blob.side_effect = get_blob
        
        result = gcs_storage.append_file("New part", "data.json")
        
        # Should use multipart strategy
        assert result.strategy_used == "multipart"
        assert result.parts_count == 1

    def test_part_limit_error(self, gcs_storage, mock_storage_client):
        """Test error when reaching GCS compose limit."""
        mock_client, mock_bucket = mock_storage_client
        
        # Mock file exists
        file_blob = MagicMock()
        file_blob.exists.return_value = True
        
        # Mock manifest with 30 parts (near limit)
        manifest_data = {
            "version": "1.0",
            "type": "omni-storage-manifest",
            "base_name": "data.csv",
            "parts": [{"name": f"data-part-{i:03d}.csv", "size": 100} for i in range(1, 31)],
            "total_size": 3000
        }
        manifest_json = json.dumps(manifest_data).encode("utf-8")
        
        manifest_blob = MagicMock()
        manifest_blob.exists.return_value = True
        manifest_blob.download_as_bytes.return_value = manifest_json
        
        # Return different blobs
        def get_blob(key):
            if key.endswith(".manifest"):
                return manifest_blob
            else:
                return file_blob
        
        mock_bucket.blob.side_effect = get_blob
        
        # Should raise error about part limit
        with pytest.raises(RuntimeError) as exc_info:
            gcs_storage.append_file("More data", "data.csv", strategy="multipart")
        
        assert "part limit" in str(exc_info.value)
