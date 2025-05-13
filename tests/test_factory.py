import os
import pytest
from pathlib import Path
from omni_storage.factory import get_storage
from omni_storage.local import LocalStorage
from omni_storage.gcs import GCSStorage
from omni_storage.s3 import S3Storage


def test_factory_local(monkeypatch):
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("DATADIR", "/tmp/factorytest")
    storage = get_storage()
    assert isinstance(storage, LocalStorage)

def test_factory_gcs(monkeypatch, mocker):
    # Mock GCS client initialization
    mock_gcs_client_constructor = mocker.patch('omni_storage.gcs.storage.Client')
    mock_bucket_instance = mocker.MagicMock()
    mock_gcs_client_instance = mock_gcs_client_constructor.return_value
    mock_gcs_client_instance.bucket.return_value = mock_bucket_instance

    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("GCS_BUCKET", "dummy-gcs-bucket")
    monkeypatch.delenv("DATADIR", raising=False)
    
    storage = get_storage()
    
    assert isinstance(storage, GCSStorage)
    mock_gcs_client_constructor.assert_called_once_with()
    mock_gcs_client_instance.bucket.assert_called_once_with("dummy-gcs-bucket")

def test_factory_s3(monkeypatch, mocker):
    # Mock S3 client initialization
    mock_s3_client_constructor = mocker.patch('omni_storage.s3.boto3.client')

    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.setenv("AWS_S3_BUCKET", "dummy-s3-bucket")
    monkeypatch.setenv("AWS_REGION", "us-east-1") # Test with region
    monkeypatch.delenv("DATADIR", raising=False)

    storage = get_storage()
    
    assert isinstance(storage, S3Storage)
    mock_s3_client_constructor.assert_called_once_with('s3', region_name='us-east-1')

# New tests for explicit storage_type parameter

def test_factory_explicit_local(monkeypatch):
    monkeypatch.setenv("DATADIR", "/tmp/explicit_local")
    # Ensure other env vars that might trigger auto-detection are not set or are ignored
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    storage = get_storage(storage_type="local")
    assert isinstance(storage, LocalStorage)
    assert storage.base_dir == Path("/tmp/explicit_local").resolve()

def test_factory_explicit_local_default_datadir(monkeypatch):
    monkeypatch.delenv("DATADIR", raising=False)
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    storage = get_storage(storage_type="local")
    assert isinstance(storage, LocalStorage)
    assert storage.base_dir == Path("./data").resolve() # Default DATADIR

def test_factory_explicit_gcs(monkeypatch, mocker):
    mock_gcs_client_constructor = mocker.patch('omni_storage.gcs.storage.Client')
    mock_bucket_instance = mocker.MagicMock()
    mock_gcs_client_instance = mock_gcs_client_constructor.return_value
    mock_gcs_client_instance.bucket.return_value = mock_bucket_instance

    monkeypatch.setenv("GCS_BUCKET", "dummy-gcs-bucket-explicit")
    # Ensure other env vars are not interfering if GCS is explicitly chosen
    monkeypatch.setenv("AWS_S3_BUCKET", "should-be-ignored-s3-bucket") 
    monkeypatch.setenv("DATADIR", "/tmp/should-be-ignored-dir")

    storage = get_storage(storage_type="gcs")
    assert isinstance(storage, GCSStorage)
    mock_gcs_client_constructor.assert_called_once_with()
    mock_gcs_client_instance.bucket.assert_called_once_with("dummy-gcs-bucket-explicit")

def test_factory_explicit_s3(monkeypatch, mocker):
    mock_s3_client_constructor = mocker.patch('omni_storage.s3.boto3.client')
    monkeypatch.setenv("AWS_S3_BUCKET", "dummy-s3-bucket-explicit")
    monkeypatch.delenv("AWS_REGION", raising=False) # Test without region first
    # Ensure other env vars are not interfering
    monkeypatch.setenv("GCS_BUCKET", "should-be-ignored-gcs-bucket")

    storage = get_storage(storage_type="s3")
    assert isinstance(storage, S3Storage)
    mock_s3_client_constructor.assert_called_once_with('s3', region_name=None)

def test_factory_explicit_s3_with_region(monkeypatch, mocker):
    mock_s3_client_constructor = mocker.patch('omni_storage.s3.boto3.client')
    monkeypatch.setenv("AWS_S3_BUCKET", "dummy-s3-bucket-region-explicit")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")

    storage = get_storage(storage_type="s3")
    assert isinstance(storage, S3Storage)
    mock_s3_client_constructor.assert_called_once_with('s3', region_name='eu-west-1')

def test_factory_explicit_local_overrides_s3_env(monkeypatch):
    monkeypatch.setenv("AWS_S3_BUCKET", "active-s3-bucket") # S3 env var is set
    monkeypatch.setenv("DATADIR", "/tmp/local_override")
    storage = get_storage(storage_type="local") # But we ask for local
    assert isinstance(storage, LocalStorage)
    assert storage.base_dir == Path("/tmp/local_override").resolve()

def test_factory_explicit_gcs_overrides_local_env(monkeypatch, mocker):
    mock_gcs_client_constructor = mocker.patch('omni_storage.gcs.storage.Client')
    mock_gcs_client_instance = mock_gcs_client_constructor.return_value
    mock_gcs_client_instance.bucket.return_value = mocker.MagicMock()

    monkeypatch.setenv("DATADIR", "/tmp/active-local-dir") # Local env var is set
    monkeypatch.setenv("GCS_BUCKET", "gcs-override-bucket")
    storage = get_storage(storage_type="gcs") # But we ask for GCS
    assert isinstance(storage, GCSStorage)
    mock_gcs_client_constructor.assert_called_once()
    mock_gcs_client_instance.bucket.assert_called_once_with("gcs-override-bucket")


# Tests for missing environment variables when storage_type is specified

def test_factory_explicit_s3_missing_bucket_env(monkeypatch):
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    with pytest.raises(ValueError, match="AWS_S3_BUCKET environment variable is required for S3 storage."):
        get_storage(storage_type="s3")

def test_factory_explicit_gcs_missing_bucket_env(monkeypatch):
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    with pytest.raises(ValueError, match="GCS_BUCKET environment variable is required for GCS storage."):
        get_storage(storage_type="gcs")

# Test for invalid storage_type

def test_factory_invalid_storage_type(monkeypatch):
    with pytest.raises(ValueError, match="Invalid storage_type: invalid_type. Must be 's3', 'gcs', or 'local'."):
        get_storage(storage_type="invalid_type")
