"""Manifest management for multi-part file handling."""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional


class ManifestManager:
    """Handles manifest file operations for multi-part file pattern."""

    MANIFEST_VERSION = "1.0"
    MANIFEST_TYPE = "omni-storage-manifest"

    def create_manifest(
        self,
        base_name: str,
        content_type: str = "application/octet-stream",
        encoding: str = "utf-8",
    ) -> Dict:
        """
        Create a new manifest structure.

        Args:
            base_name: The base name of the file (without part suffix)
            content_type: MIME type of the content
            encoding: Character encoding for text files

        Returns:
            Dict: New manifest structure
        """
        now = datetime.now(timezone.utc).isoformat()
        return {
            "version": self.MANIFEST_VERSION,
            "type": self.MANIFEST_TYPE,
            "base_name": base_name,
            "parts": [],
            "total_size": 0,
            "content_type": content_type,
            "encoding": encoding,
            "created": now,
            "updated": now,
        }

    def read_manifest(self, content: bytes) -> Dict:
        """
        Parse JSON manifest from bytes.

        Args:
            content: Raw manifest file content

        Returns:
            Dict: Parsed manifest

        Raises:
            ValueError: If content is not valid JSON or not a manifest
        """
        try:
            manifest = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid manifest content: {e}")

        if manifest.get("type") != self.MANIFEST_TYPE:
            raise ValueError(
                f"Not a valid manifest file (type: {manifest.get('type')})"
            )

        return manifest

    def is_manifest_file(self, content: bytes) -> bool:
        """
        Check if content represents a manifest file.

        Args:
            content: File content to check

        Returns:
            bool: True if content is a valid manifest
        """
        try:
            manifest = self.read_manifest(content)
            return manifest.get("type") == self.MANIFEST_TYPE
        except (ValueError, KeyError):
            return False

    def add_part(
        self,
        manifest: Dict,
        part_name: str,
        size: int,
        checksum: Optional[str] = None,
    ) -> Dict:
        """
        Add a new part to the manifest.

        Args:
            manifest: Existing manifest structure
            part_name: Name of the part file
            size: Size of the part in bytes
            checksum: Optional checksum of the part

        Returns:
            Dict: Updated manifest
        """
        part_info = {
            "name": part_name,
            "size": size,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        if checksum:
            part_info["checksum"] = checksum

        manifest["parts"].append(part_info)
        # Handle manifests that might not have total_size (e.g., incomplete manifests)
        manifest["total_size"] = manifest.get("total_size", 0) + size
        manifest["updated"] = datetime.now(timezone.utc).isoformat()

        return manifest

    def get_next_part_name(self, base_name: str, manifest: Dict) -> str:
        """
        Generate the next sequential part name.

        Args:
            base_name: Base filename (e.g., "data.csv")
            manifest: Current manifest

        Returns:
            str: Next part filename (e.g., "data-part-003.csv")
        """
        # Extract extension from base name
        if "." in base_name:
            name_parts = base_name.rsplit(".", 1)
            base = name_parts[0]
            extension = "." + name_parts[1]
        else:
            base = base_name
            extension = ""

        # Find the highest part number
        max_part_num = 0
        for part in manifest.get("parts", []):
            part_name = part["name"]
            # Try to extract part number from name
            if part_name.startswith(base + "-part-"):
                try:
                    # Extract number between "-part-" and extension
                    num_str = part_name[len(base + "-part-") :].replace(extension, "")
                    part_num = int(num_str)
                    max_part_num = max(max_part_num, part_num)
                except ValueError:
                    continue

        # Generate next part name
        next_part_num = max_part_num + 1
        return f"{base}-part-{next_part_num:03d}{extension}"

    def get_parts_in_order(self, manifest: Dict) -> List[Dict]:
        """
        Get parts sorted by creation time.

        Args:
            manifest: Manifest structure

        Returns:
            List[Dict]: Parts sorted by creation time
        """
        return sorted(manifest.get("parts", []), key=lambda p: p["created"])

    def serialize_manifest(self, manifest: Dict) -> bytes:
        """
        Serialize manifest to JSON bytes.

        Args:
            manifest: Manifest structure

        Returns:
            bytes: JSON-encoded manifest
        """
        return json.dumps(manifest, indent=2).encode("utf-8")
