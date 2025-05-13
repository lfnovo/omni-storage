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
