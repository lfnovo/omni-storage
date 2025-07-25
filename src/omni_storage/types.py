"""Type definitions for omni-storage."""

from typing import Literal, NamedTuple


class AppendResult(NamedTuple):
    """Result of an append operation.

    Attributes:
        path: The path where the content was appended
        bytes_written: Number of bytes written in this append operation
        strategy_used: The strategy used for appending ('single' or 'multipart')
        parts_count: Total number of parts in the file (1 for single strategy)
    """

    path: str
    bytes_written: int
    strategy_used: Literal["single", "multipart"]
    parts_count: int = 1
