"""Local filesystem storage implementation."""
from pathlib import Path
from typing import BinaryIO, Union

from .base import Storage


class LocalStorage(Storage):
    """Local filesystem storage implementation."""
    
    def __init__(self, base_dir: str):
        """Initialize local storage.
        
        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_full_path(self, file_path: str) -> Path:
        """Get full path for a file."""
        full_path = self.base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path
        
    def save_file(self, file_data: Union[bytes, BinaryIO], destination_path: str) -> str:
        """Save file to local filesystem."""
        full_path = self._get_full_path(destination_path)
        
        if isinstance(file_data, bytes):
            full_path.write_bytes(file_data)
        else:
            with open(full_path, 'wb') as f:
                f.write(file_data.read())
                
        return str(full_path)
    
    def read_file(self, file_path: str) -> bytes:
        """Read file from local filesystem."""
        full_path = self._get_full_path(file_path)
        return full_path.read_bytes()
    
    def get_file_url(self, file_path: str) -> str:
        """Get local filesystem path."""
        return str(self._get_full_path(file_path))
