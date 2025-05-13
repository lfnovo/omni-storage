import pytest
from omni_storage.base import Storage

class DummyStorage(Storage):
    def save_file(self, file_data, destination_path):
        return destination_path
    def read_file(self, file_path):
        return b"dummy"
    def get_file_url(self, file_path):
        return f"dummy://{file_path}"

def test_storage_interface():
    s = DummyStorage()
    assert s.save_file(b"x", "foo") == "foo"
    assert s.read_file("foo") == b"dummy"
    assert s.get_file_url("foo") == "dummy://foo"
