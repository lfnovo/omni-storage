import os
import pytest
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
