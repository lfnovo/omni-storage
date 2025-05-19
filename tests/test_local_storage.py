import os
import tempfile
import pytest
from omni_storage.local import LocalStorage

@pytest.fixture
def temp_storage_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def storage(temp_storage_dir):
    return LocalStorage(temp_storage_dir)

def test_save_and_read_file_bytes(storage):
    data = b"hello world"
    path = "foo/bar.txt"
    storage.save_file(data, path)
    assert storage.read_file(path) == data

def test_save_and_read_file_obj(storage):
    data = b"fileobj test"
    path = "foo/fileobj.txt"
    import io
    fileobj = io.BytesIO(data)
    storage.save_file(fileobj, path)
    assert storage.read_file(path) == data

def test_get_file_url(storage):
    data = b"url test"
    path = "baz/qux.txt"
    storage.save_file(data, path)
    url = storage.get_file_url(path)
    assert os.path.exists(url)
    assert url.endswith(path)

def test_upload_file(storage, temp_storage_dir):
    # Create a temporary file to upload
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(b"upload test")
        tmp_file_path = tmp_file.name
    
    destination_path = "uploaded/test.txt"
    result_path = storage.upload_file(tmp_file_path, destination_path)
    assert result_path == destination_path
    
    # Verify the file was uploaded
    uploaded_file_path = os.path.join(temp_storage_dir, destination_path)
    assert os.path.exists(uploaded_file_path)
    with open(uploaded_file_path, "rb") as f:
        assert f.read() == b"upload test"
    
    # Clean up temporary file
    os.unlink(tmp_file_path)

def test_exists(storage):
    data = b"exists test"
    path = "exists/test.txt"
    storage.save_file(data, path)
    assert storage.exists(path) == True
    assert storage.exists("nonexistent/file.txt") == False
