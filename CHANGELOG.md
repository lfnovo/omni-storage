# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0]

### Added
- `append_file` method to all storage backends for efficient file appending
  - LocalStorage: Uses native filesystem append operations
  - S3Storage: Implements intelligent strategy selection between single-file and multi-part patterns
  - GCSStorage: Similar to S3 with support for both single-file and multi-part strategies
- Multi-part file pattern for cloud storage to efficiently handle large file appends
  - Automatic strategy selection based on file size (default threshold: 100MB)
  - Transparent reading of multi-part files through existing `read_file` method
  - Manifest-based tracking of file parts for cloud storage
- `AppendResult` named tuple to provide detailed information about append operations
- `ManifestManager` utility class for handling multi-part file manifests
- Comprehensive test coverage for all append operations (45 tests total)

### Changed
- Enhanced `read_file` method in S3Storage and GCSStorage to transparently handle multi-part files
- Updated type hints to include new append-related types

## [0.2.1]

### Fixed
- Minor bug fixes and improvements

## [0.2.0]

### Added
- `storage_type` parameter to `get_storage` for explicit backend selection

## [0.1.3]

### Added
- py.typed file for full type checking support
- Lazy loading of storage providers to prevent ModuleNotFoundError

## [0.1.0]

### Added
- Unified storage interface for Local, S3, and GCS
- Basic file operations: save, read, upload, exists, get_url
- Factory pattern for automatic backend selection
- Environment variable-based configuration