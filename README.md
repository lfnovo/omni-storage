# Omni Storage

A unified Python interface for file storage, supporting local filesystem, Google Cloud Storage (GCS), and Amazon S3. Easily switch between storage backends using environment variables, and interact with files using a simple, consistent API.

---

## Features

- **Unified Storage Interface**: Use the same API to interact with Local Filesystem, Google Cloud Storage, and Amazon S3.
- **File Operations**: Save, read, and append to files as bytes or file-like objects.
- **Efficient Append**: Smart append operations that use native filesystem append for local storage and multi-part patterns for cloud storage.
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

## Storage Provider Setup

### Local Filesystem Storage

The simplest storage option, ideal for development and testing.

**Required Environment Variables:**
- `DATADIR` (optional): Directory path for file storage. Defaults to `./data` if not set.

**Example Setup:**
```bash
# Optional: Set custom data directory
export DATADIR="/path/to/your/data"

# Or use default ./data directory (no setup needed)
```

**Usage:**
```python
from omni_storage.factory import get_storage

# Automatic detection (when only DATADIR is set)
storage = get_storage()

# Or explicit selection
storage = get_storage(storage_type="local")
```

### Amazon S3 Storage

Store files in Amazon S3 buckets with full AWS integration.

**Required Environment Variables:**
- `AWS_S3_BUCKET`: Your S3 bucket name
- `AWS_REGION` (optional): AWS region (e.g., "us-east-1")

**AWS Credentials:** Must be configured via one of these methods:
- Environment variables: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- AWS credentials file: `~/.aws/credentials`
- IAM roles (when running on AWS infrastructure)
- See [boto3 credentials documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) for all options

**Example Setup:**
```bash
# Required: S3 bucket name
export AWS_S3_BUCKET="my-storage-bucket"

# Optional: AWS region
export AWS_REGION="us-west-2"

# AWS credentials (if not using IAM roles or credentials file)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

**Usage:**
```python
from omni_storage.factory import get_storage

# Automatic detection (when AWS_S3_BUCKET is set)
storage = get_storage()

# Or explicit selection
storage = get_storage(storage_type="s3")
```

### Google Cloud Storage (GCS)

Store files in Google Cloud Storage buckets.

**Required Environment Variables:**
- `GCS_BUCKET`: Your GCS bucket name

**GCS Authentication:** Must be configured via one of these methods:
- Service account key file: Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Application Default Credentials (ADC) when running on Google Cloud
- gcloud CLI authentication for local development
- See [Google Cloud authentication documentation](https://cloud.google.com/docs/authentication/application-default-credentials) for details

**Example Setup:**
```bash
# Required: GCS bucket name
export GCS_BUCKET="my-gcs-bucket"

# Authentication via service account (most common)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Or authenticate via gcloud CLI for development
gcloud auth application-default login
```

**Usage:**
```python
from omni_storage.factory import get_storage

# Automatic detection (when GCS_BUCKET is set)
storage = get_storage()

# Or explicit selection
storage = get_storage(storage_type="gcs")
```

## Backend Selection Logic

Omni Storage can determine the appropriate backend in two ways:

1. **Explicitly via `storage_type` parameter**: Pass `storage_type="s3"`, `storage_type="gcs"`, or `storage_type="local"` to `get_storage()`
2. **Automatically via Environment Variables**: If `storage_type` is not provided, the backend is chosen based on which environment variables are set:
   - If `AWS_S3_BUCKET` is set → S3 storage
   - If `GCS_BUCKET` is set → GCS storage
   - Otherwise → Local storage (using `DATADIR` or default `./data`)

**Note:** Even when using explicit selection, the relevant environment variables for that backend must still be set.

## Usage Examples

### Basic Operations

```python
from omni_storage.factory import get_storage

# Get storage instance (auto-detect from environment)
storage = get_storage()

# Save a file from bytes
data = b"Hello, World!"
storage.save_file(data, 'hello.txt')

# Save a file from file-like object
with open('local_file.txt', 'rb') as f:
    storage.save_file(f, 'uploads/remote_file.txt')

# Read a file
content = storage.read_file('uploads/remote_file.txt')
print(content.decode('utf-8'))

# Upload a file directly from path
storage.upload_file('/path/to/local/file.pdf', 'documents/file.pdf')

# Check if file exists
if storage.exists('documents/file.pdf'):
    print("File exists!")

# Get file URL
url = storage.get_file_url('documents/file.pdf')
print(f"File URL: {url}")
```

### Appending to Files

The `append_file` method allows you to efficiently add content to existing files:

```python
from omni_storage.factory import get_storage

storage = get_storage()

# Append text to a file
storage.append_file("Line 1\n", "log.txt")
storage.append_file("Line 2\n", "log.txt")

# Append binary data
binary_data = b"\x00\x01\x02\x03"
storage.append_file(binary_data, "data.bin")

# Append from file-like objects
from io import StringIO, BytesIO

text_buffer = StringIO("Buffered text content\n")
storage.append_file(text_buffer, "output.txt")

bytes_buffer = BytesIO(b"Binary buffer content")
storage.append_file(bytes_buffer, "binary_output.bin")

# Streaming large CSV data 
import csv
from io import StringIO

# Simulate streaming data from a database
for batch in fetch_large_dataset():
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerows(batch)
    
    # Append CSV data efficiently
    csv_buffer.seek(0)
    storage.append_file(csv_buffer, "large_dataset.csv")
```

**Cloud Storage Optimization**: For S3 and GCS, append operations intelligently choose between:
- **Single-file strategy**: For small files, downloads existing content, appends new data, and re-uploads
- **Multi-part strategy**: For large files (>100MB by default), creates separate part files and a manifest for efficient streaming

The multi-part pattern is transparent to users - when you read a file, it automatically handles both single files and multi-part files seamlessly.

### Provider-Specific Examples

```python
# Force specific storage backend
s3_storage = get_storage(storage_type="s3")      # Requires AWS_S3_BUCKET
gcs_storage = get_storage(storage_type="gcs")     # Requires GCS_BUCKET
local_storage = get_storage(storage_type="local") # Uses DATADIR or ./data

# URLs differ by provider:
# - S3: https://bucket-name.s3.region.amazonaws.com/path/to/file
# - GCS: https://storage.googleapis.com/bucket-name/path/to/file
# - Local: file:///absolute/path/to/file
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
- `append_file(content: Union[str, bytes, BinaryIO], filename: str, create_if_not_exists: bool = True, strategy: Literal["auto", "single", "multipart"] = "auto", part_size_mb: int = 100) -> AppendResult`
    - Append content to an existing file or create a new one.
    - Returns `AppendResult` with: `path`, `bytes_written`, `strategy_used`, and `parts_count`.

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
