"""Tests for manifest management."""

import json
from datetime import datetime

import pytest

from omni_storage.manifest import ManifestManager


class TestManifestManager:
    """Test ManifestManager functionality."""

    def setup_method(self):
        """Set up test instance."""
        self.manager = ManifestManager()

    def test_create_manifest(self):
        """Test creating a new manifest."""
        manifest = self.manager.create_manifest("data.csv", "text/csv")

        assert manifest["version"] == "1.0"
        assert manifest["type"] == "omni-storage-manifest"
        assert manifest["base_name"] == "data.csv"
        assert manifest["parts"] == []
        assert manifest["total_size"] == 0
        assert manifest["content_type"] == "text/csv"
        assert manifest["encoding"] == "utf-8"
        assert "created" in manifest
        assert "updated" in manifest

        # Check timestamps are valid ISO format
        datetime.fromisoformat(manifest["created"].replace("Z", "+00:00"))
        datetime.fromisoformat(manifest["updated"].replace("Z", "+00:00"))

    def test_create_manifest_defaults(self):
        """Test creating manifest with default values."""
        manifest = self.manager.create_manifest("data.bin")

        assert manifest["content_type"] == "application/octet-stream"
        assert manifest["encoding"] == "utf-8"

    def test_read_manifest_valid(self):
        """Test reading a valid manifest."""
        manifest_data = {
            "version": "1.0",
            "type": "omni-storage-manifest",
            "base_name": "test.txt",
            "parts": [],
            "total_size": 0,
        }
        content = json.dumps(manifest_data).encode("utf-8")

        manifest = self.manager.read_manifest(content)
        assert manifest["base_name"] == "test.txt"
        assert manifest["type"] == "omni-storage-manifest"

    def test_read_manifest_invalid_json(self):
        """Test reading invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid manifest content"):
            self.manager.read_manifest(b"not json")

    def test_read_manifest_wrong_type(self):
        """Test reading JSON with wrong type raises ValueError."""
        content = json.dumps({"type": "wrong-type"}).encode("utf-8")
        with pytest.raises(ValueError, match="Not a valid manifest file"):
            self.manager.read_manifest(content)

    def test_is_manifest_file_valid(self):
        """Test detecting valid manifest files."""
        manifest = self.manager.create_manifest("test.txt")
        content = self.manager.serialize_manifest(manifest)

        assert self.manager.is_manifest_file(content) is True

    def test_is_manifest_file_invalid(self):
        """Test detecting non-manifest files."""
        assert self.manager.is_manifest_file(b"regular file content") is False
        assert self.manager.is_manifest_file(b'{"type": "other"}') is False

    def test_add_part(self):
        """Test adding parts to manifest."""
        manifest = self.manager.create_manifest("data.csv")
        original_updated = manifest["updated"]

        # Add first part
        manifest = self.manager.add_part(manifest, "data-part-001.csv", 1024)

        assert len(manifest["parts"]) == 1
        assert manifest["parts"][0]["name"] == "data-part-001.csv"
        assert manifest["parts"][0]["size"] == 1024
        assert manifest["total_size"] == 1024
        assert manifest["updated"] != original_updated

        # Add second part with checksum
        manifest = self.manager.add_part(
            manifest, "data-part-002.csv", 2048, checksum="abc123"
        )

        assert len(manifest["parts"]) == 2
        assert manifest["parts"][1]["checksum"] == "abc123"
        assert manifest["total_size"] == 3072

    def test_get_next_part_name_with_extension(self):
        """Test generating next part name for files with extension."""
        manifest = self.manager.create_manifest("data.csv")

        # First part
        next_name = self.manager.get_next_part_name("data.csv", manifest)
        assert next_name == "data-part-001.csv"

        # Add part and get next
        manifest = self.manager.add_part(manifest, next_name, 1024)
        next_name = self.manager.get_next_part_name("data.csv", manifest)
        assert next_name == "data-part-002.csv"

        # Skip to part 10
        manifest = self.manager.add_part(manifest, "data-part-010.csv", 1024)
        next_name = self.manager.get_next_part_name("data.csv", manifest)
        assert next_name == "data-part-011.csv"

    def test_get_next_part_name_without_extension(self):
        """Test generating next part name for files without extension."""
        manifest = self.manager.create_manifest("logfile")

        next_name = self.manager.get_next_part_name("logfile", manifest)
        assert next_name == "logfile-part-001"

    def test_get_next_part_name_multiple_dots(self):
        """Test part naming with filenames containing multiple dots."""
        manifest = self.manager.create_manifest("my.data.backup.csv")

        next_name = self.manager.get_next_part_name("my.data.backup.csv", manifest)
        assert next_name == "my.data.backup-part-001.csv"

    def test_get_parts_in_order(self):
        """Test getting parts sorted by creation time."""
        manifest = self.manager.create_manifest("data.csv")

        # Add parts with different timestamps
        part1 = {
            "name": "data-part-001.csv",
            "size": 1024,
            "created": "2024-01-01T10:00:00Z",
        }
        part2 = {
            "name": "data-part-002.csv",
            "size": 1024,
            "created": "2024-01-01T09:00:00Z",  # Earlier
        }
        part3 = {
            "name": "data-part-003.csv",
            "size": 1024,
            "created": "2024-01-01T11:00:00Z",  # Later
        }

        manifest["parts"] = [part1, part2, part3]

        ordered_parts = self.manager.get_parts_in_order(manifest)
        assert ordered_parts[0]["name"] == "data-part-002.csv"  # Earliest
        assert ordered_parts[1]["name"] == "data-part-001.csv"
        assert ordered_parts[2]["name"] == "data-part-003.csv"  # Latest

    def test_serialize_manifest(self):
        """Test serializing manifest to JSON bytes."""
        manifest = self.manager.create_manifest("test.txt")
        manifest = self.manager.add_part(manifest, "test-part-001.txt", 100)

        serialized = self.manager.serialize_manifest(manifest)

        # Should be valid JSON
        deserialized = json.loads(serialized.decode("utf-8"))
        assert deserialized["base_name"] == "test.txt"
        assert len(deserialized["parts"]) == 1

        # Should be pretty-printed
        assert b"\n" in serialized  # Has newlines from indentation

    def test_roundtrip_manifest(self):
        """Test creating, serializing, and reading back a manifest."""
        # Create and populate manifest
        original = self.manager.create_manifest("data.csv", "text/csv")
        original = self.manager.add_part(original, "data-part-001.csv", 1000)
        original = self.manager.add_part(original, "data-part-002.csv", 2000)

        # Serialize and read back
        serialized = self.manager.serialize_manifest(original)
        restored = self.manager.read_manifest(serialized)

        # Check key fields match
        assert restored["base_name"] == original["base_name"]
        assert restored["total_size"] == original["total_size"]
        assert len(restored["parts"]) == len(original["parts"])
        assert restored["parts"][0]["name"] == original["parts"][0]["name"]
