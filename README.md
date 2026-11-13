# py-symlink

Resolve a symlink chain and report whether the final target exists, the chain is circular, or it exceeds a caller-supplied depth limit.

```python
from py_symlink import SymlinkStatus, validate_symlink

result = validate_symlink("/var/run/current", max_depth=32)

if result.status is SymlinkStatus.OK:
    print("resolved to", result.resolved)
elif result.status is SymlinkStatus.MISSING:
    print("dangling link at", result.resolved)
elif result.status is SymlinkStatus.CIRCULAR:
    print("cycle detected at", result.resolved)
else:  # SymlinkStatus.TOO_DEEP
    print("gave up after", result.depth, "links")
```

The public surface is exactly three names:

- `validate_symlink(path, max_depth=40)` — walk the chain and return a `SymlinkResult`.
- `SymlinkStatus` — an `Enum` with members `OK`, `MISSING`, `CIRCULAR`, `TOO_DEEP`.
- `SymlinkResult` — a value object with attributes `path` (the original argument), `status`, `resolved` (the path where resolution stopped), and `depth` (number of links followed).

## Why this exists

`os.path.realpath` is convenient but lossy: it silently collapses cycles and
stops at an internal limit, so a caller cannot tell a real resolution from a
give-up. That matters when the answer drives a decision — for example, deciding
whether a deployment symlink is healthy or whether a directory scan should skip
a runaway tree. This library follows links one at a time and returns the reason
it stopped, at the cost of doing the walk itself instead of delegating to the
C implementation. The trade-off is a few microseconds per call for a diagnosable
result.

## The awkward edge

A path whose final component is a symlink to a relative target is resolved
against the directory of the link, not the process working directory. This
matches `readlink` semantics but surprises callers who reason in terms of the
current directory; the `resolved` field always holds the absolute path that was
actually tested.

## Notes on semantics

- `max_depth` counts links followed. `max_depth=0` on a symlink returns `TOO_DEEP` with `depth=0`; on a regular file it returns `OK`.
- A negative `max_depth` raises `ValueError`.
- A cycle is reported at the link that would repeat, so `depth` is the number of distinct links already followed.
- A missing target is reported at the first link whose target is absent, whether that is the input itself or a later hop.
- Relative input paths are accepted; `result.path` preserves the argument as given.
