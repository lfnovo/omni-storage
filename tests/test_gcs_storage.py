import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from omni_storage.gcs import GCSStorage

@pytest.fixture
def gcs_storage():
    with patch('google.cloud.storage.Client') as mock_client:
        mock_bucket = MagicMock()
        mock_bucket.name = "test-bucket"
        mock_client.return_value.bucket.return_value = mock_bucket
        storage = GCSStorage("test-bucket")
        yield storage

def test_save_and_read_file_bytes(gcs_storage):
    data = b"hello world"
    path = "foo/bar.txt"
    
    gcs_storage.bucket.blob.return_value.upload_from_string = MagicMock()
    gcs_storage.bucket.blob.return_value.download_as_bytes.return_value = data
    
    result = gcs_storage.save_file(data, path)
    assert result == path
    assert gcs_storage.read_file(path) == data

def test_save_and_read_file_obj(gcs_storage):
    data = b"fileobj test"
    path = "foo/fileobj.txt"
    import io
    fileobj = io.BytesIO(data)
    
    gcs_storage.bucket.blob.return_value.upload_from_file = MagicMock()
    gcs_storage.bucket.blob.return_value.download_as_bytes.return_value = data
    
    result = gcs_storage.save_file(fileobj, path)
    assert result == path
    assert gcs_storage.read_file(path) == data

def test_get_file_url(gcs_storage):
    data = b"url test"
    path = "baz/qux.txt"
    
    gcs_storage.bucket.blob.return_value.upload_from_string = MagicMock()
    result = gcs_storage.save_file(data, path)
    url = gcs_storage.get_file_url(path)
    assert url == f"gs://test-bucket/{path}"

def test_upload_file(gcs_storage):
    # Create a temporary file to upload
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(b"upload test")
        tmp_file_path = tmp_file.name
    
    destination_path = "uploaded/test.txt"
    gcs_storage.bucket.blob.return_value.upload_from_file = MagicMock()
    result_path = gcs_storage.upload_file(tmp_file_path, destination_path)
    assert result_path == destination_path
    gcs_storage.bucket.blob.assert_called_with(destination_path)
    
    # Clean up temporary file
    os.unlink(tmp_file_path)

def test_exists(gcs_storage):
    path = "exists/test.txt"
    nonexistent_path = "nonexistent/file.txt"
    
    # Mock blob.exists() to return True for existing file
    existing_blob = MagicMock()
    existing_blob.exists.return_value = True
    nonexistent_blob = MagicMock()
    nonexistent_blob.exists.return_value = False
    
    gcs_storage.bucket.blob.side_effect = lambda p: existing_blob if p == path else nonexistent_blob
    
    assert gcs_storage.exists(path) == True
    assert gcs_storage.exists(nonexistent_path) == False
