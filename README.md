# Omni Storage

A unified Python interface for file storage, supporting local filesystem, Google Cloud Storage (GCS), and Amazon S3. Easily switch between storage backends using environment variables, and interact with files using a simple, consistent API.

---

## Features

- **Unified Storage Interface**: Use the same API to interact with Local Filesystem, Google Cloud Storage, and Amazon S3.
- **File Operations**: Save and read files as bytes or file-like objects.
- **URL Generation**: Get URLs for files stored in any of the supported storage systems.
- **File Upload**: Upload files directly from local file paths to the storage system.
- **Existence Check**: Check if a file exists in the storage system.
- **Backend Flexibility**: Seamlessly switch between local, GCS, and S3 storage by setting environment variables.
- **Extensible**: Add new storage backends by subclassing the `Storage` abstract base class.
- **Factory Pattern**: Automatically selects the appropriate backend at runtime.

---

## Installation

This package uses [uv](https://github.com/astral-sh/uv) for dependency management. To install dependencies:

```sh
uv sync
```

### Optional dependencies (extras)

Depending on the storage backend(s) you want to use, you can install optional dependencies:

- **Google Cloud Storage support:**
  ```sh
  uv sync --extra gcs
  ```
- **Amazon S3 support:**
  ```sh
  uv sync --extra s3
  ```
- **All:**
  ```sh
  uv sync --all-extras
  ```

---

## Usage

### Selecting the Storage Backend

Omni Storage can determine the appropriate backend in two ways:

1.  **Explicitly via `storage_type` parameter**: You can pass `storage_type="s3"`, `storage_type="gcs"`, or `storage_type="local"` to the `get_storage()` function.
2.  **Automatically via Environment Variables**: If `storage_type` is not provided, the backend is chosen based on the following environment variables:
    -   **Amazon S3**: Set the `AWS_S3_BUCKET` environment variable to your S3 bucket name. Optionally set `AWS_REGION` for your region. AWS credentials must be available in your environment (see [boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)).
    -   **Google Cloud Storage**: Set the `GCS_BUCKET` environment variable to the name of your GCS bucket.
    -   **Local Filesystem**: Set the `DATADIR` environment variable to the desired directory (defaults to `./data` if unset).

Even when `storage_type` is specified, the relevant environment variables (e.g., `AWS_S3_BUCKET` for S3) are still required for configuration.

### Example

```python
from omni_storage.factory import get_storage

# Automatically detect backend from environment variables
# storage = get_storage()

# Or, explicitly specify the backend (e.g., S3)
# Ensure AWS_S3_BUCKET (and optionally AWS_REGION) are set in your environment
storage = get_storage(storage_type="s3")

# Save a file
with open('example.txt', 'rb') as f:
    storage.save_file(f, 'uploads/example.txt')

# Read a file
data = storage.read_file('uploads/example.txt')

# Get file URL
url = storage.get_file_url('uploads/example.txt')
print(url)
```

---

## API

### Abstract Base Class: `Storage`

- `save_file(file_data: Union[bytes, BinaryIO], destination_path: str) -> str`
    - Save file data to storage.
- `read_file(file_path: str) -> bytes`
    - Read file data from storage.
- `get_file_url(file_path: str) -> str`
    - Get a URL or path to access the file.
- `upload_file(local_path: str, destination_path: str) -> str`
    - Upload a file from a local path to storage.
- `exists(file_path: str) -> bool`
    - Check if a file exists in storage.

### Implementations

- `S3Storage(bucket_name: str, region_name: str | None = None)`
    - Stores files in an Amazon S3 bucket.
- `GCSStorage(bucket_name: str)`
    - Stores files in a Google Cloud Storage bucket.
- `LocalStorage(base_dir: str)`
    - Stores files on the local filesystem.

### Factory

- `get_storage(storage_type: Optional[Literal["s3", "gcs", "local"]] = None) -> Storage`
    - Returns a storage instance. If `storage_type` is provided (e.g., "s3", "gcs", "local"),
      it determines the backend. Otherwise, the choice is based on environment variables.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Contributing

Contributions are welcome! Please open issues and pull requests for bug fixes or new features.

---

## Acknowledgements

- Inspired by the need for flexible, pluggable storage solutions in modern Python applications.
