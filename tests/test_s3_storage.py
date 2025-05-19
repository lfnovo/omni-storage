import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from omni_storage.s3 import S3Storage

@pytest.fixture
def s3_storage():
    with patch('boto3.client') as mock_client:
        storage = S3Storage("test-bucket")
        storage.s3 = MagicMock()
        yield storage

def test_save_and_read_file_bytes(s3_storage):
    data = b"hello world"
    path = "foo/bar.txt"
    
    s3_storage.s3.put_object = MagicMock()
    s3_storage.s3.get_object.return_value = {'Body': MagicMock(read=MagicMock(return_value=data))}
    
    result = s3_storage.save_file(data, path)
    assert result == path
    assert s3_storage.read_file(path) == data

def test_save_and_read_file_obj(s3_storage):
    data = b"fileobj test"
    path = "foo/fileobj.txt"
    import io
    fileobj = io.BytesIO(data)
    
    s3_storage.s3.upload_fileobj = MagicMock()
    s3_storage.s3.get_object.return_value = {'Body': MagicMock(read=MagicMock(return_value=data))}
    
    result = s3_storage.save_file(fileobj, path)
    assert result == path
    assert s3_storage.read_file(path) == data

def test_get_file_url(s3_storage):
    data = b"url test"
    path = "baz/qux.txt"
    
    s3_storage.s3.put_object = MagicMock()
    result = s3_storage.save_file(data, path)
    url = s3_storage.get_file_url(path)
    assert url == f"s3://test-bucket/{path}"

def test_upload_file(s3_storage):
    # Create a temporary file to upload
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(b"upload test")
        tmp_file_path = tmp_file.name
    
    destination_path = "uploaded/test.txt"
    s3_storage.s3.upload_fileobj = MagicMock()
    result_path = s3_storage.upload_file(tmp_file_path, destination_path)
    assert result_path == destination_path
    
    # Clean up temporary file
    os.unlink(tmp_file_path)

def test_exists(s3_storage):
    path = "exists/test.txt"
    nonexistent_path = "nonexistent/file.txt"
    
    # Mock head_object to succeed for existing file and raise exception for nonexistent
    def head_object_side_effect(Bucket, Key):
        if Key == path:
            return {}
        raise Exception("Not found")
    
    s3_storage.s3.head_object.side_effect = head_object_side_effect
    
    assert s3_storage.exists(path) == True
    assert s3_storage.exists(nonexistent_path) == False
