import os
from enum import Enum, auto


class SymlinkStatus(Enum):
    """Outcome of validating a symlink chain."""

    OK = auto()
    MISSING = auto()
    CIRCULAR = auto()
    TOO_DEEP = auto()


class SymlinkResult:
    """Result of resolving a symlink chain.

    ``path`` is the original input path. ``resolved`` is the final target path
    when the chain resolved successfully, otherwise the path at which resolution
    stopped (the missing link, the repeated link, or the link that exceeded the
    depth limit). ``depth`` is the number of symlinks followed.
    """

    __slots__ = ("path", "status", "resolved", "depth")

    def __init__(self, path, status, resolved=None, depth=0):
        self.path = path
        self.status = status
        self.resolved = resolved
        self.depth = depth

    def __repr__(self):
        return (
            f"SymlinkResult(path={self.path!r}, status={self.status!r}, "
            f"resolved={self.resolved!r}, depth={self.depth})"
        )

    def __eq__(self, other):
        if not isinstance(other, SymlinkResult):
            return NotImplemented
        return (
            self.path == other.path
            and self.status == other.status
            and self.resolved == other.resolved
            and self.depth == other.depth
        )

    def __hash__(self):
        return hash((self.path, self.status, self.resolved, self.depth))


def validate_symlink(path, max_depth=40):
    """Resolve a symlink chain starting at *path* and report its state.

    The function follows symlinks one at a time, resolving relative targets
    against the directory of the link that points to them. It stops early on
    the first of three terminal conditions:

    * a link target does not exist -> :attr:`SymlinkStatus.MISSING`
    * a link target has already been visited -> :attr:`SymlinkStatus.CIRCULAR`
    * the number of links followed reaches *max_depth* -> :attr:`SymlinkStatus.TOO_DEEP`

    If the path is not a symlink it is returned unchanged with status
    :attr:`SymlinkStatus.OK` and depth 0. If *max_depth* is zero and the path
    is a symlink, the result is :attr:`SymlinkStatus.TOO_DEEP` with depth 0.

    Why a manual walk instead of :func:`os.path.realpath`: ``realpath`` silently
    collapses cycles and truncates at an internal limit, giving no way to tell
    "resolved" from "gave up". This function reports the distinction.

    Args:
        path: Filesystem path to inspect. May be relative or absolute.
        max_depth: Maximum number of symlinks to follow. Must be >= 0.

    Returns:
        SymlinkResult

    Raises:
        ValueError: if *max_depth* is negative.
    """
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")

    original = os.fspath(path)
    current = os.path.abspath(original)
    seen = set()
    depth = 0

    while True:
        if not os.path.lexists(current):
            return SymlinkResult(original, SymlinkStatus.MISSING, current, depth)

        if not os.path.islink(current):
            return SymlinkResult(original, SymlinkStatus.OK, current, depth)

        if depth >= max_depth:
            return SymlinkResult(original, SymlinkStatus.TOO_DEEP, current, depth)

        if current in seen:
            return SymlinkResult(original, SymlinkStatus.CIRCULAR, current, depth)

        seen.add(current)
        target = os.readlink(current)
        if os.path.isabs(target):
            current = os.path.normpath(target)
        else:
            current = os.path.normpath(os.path.join(os.path.dirname(current), target))
        depth += 1
