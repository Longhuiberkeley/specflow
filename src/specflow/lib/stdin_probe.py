"""Non-consuming "is there really piped data on stdin?" probe.

``select()`` with a zero timeout reports a stream as readable both when bytes
are waiting AND when it is at EOF (``</dev/null``, an empty closed pipe, an
agent harness with no stdin). Treating EOF as data made ``specflow update``
warn "Stdin data ignored" on every non-interactive field update, so consumer
agents appended ``</dev/null`` to hundreds of calls. This helper settles the
question without consuming anything and without blocking on an idle pipe.
"""

from __future__ import annotations

import select
import sys
from typing import IO


def stdin_has_data(stream: IO | None = None) -> bool:
    """Return True only when ``stream`` (default ``sys.stdin``) holds bytes.

    Decision order:
      1. A TTY, a closed stream, or no stream at all -> False.
      2. ``select()`` with a zero timeout says nothing is readable (an idle
         open pipe, a slow producer) -> False, without blocking.
      3. Readable -> peek one byte through the buffered layer: ``b''`` means
         EOF (``/dev/null``, an empty closed pipe) -> False; otherwise True.
         The peek never consumes, so a later ``read()`` still sees the body.
      4. Streams without a file descriptor (``io.StringIO`` under test) fall
         back to a seek-and-restore one-character probe.
    """
    if stream is None:
        stream = sys.stdin
    if stream is None:
        return False
    try:
        if stream.closed or stream.isatty():
            return False
    except (AttributeError, ValueError, OSError):
        return False

    try:
        readable = bool(select.select([stream], [], [], 0.0)[0])
    except (OSError, ValueError, TypeError):
        # No fileno(): pytest capture / StringIO. A one-character seekable
        # probe is safe and restores the original position.
        try:
            if not stream.seekable():
                return False
            pos = stream.tell()
            probe = stream.read(1)
            stream.seek(pos)
            return bool(probe)
        except (OSError, ValueError, AttributeError):
            return False

    if not readable:
        return False

    # Readable may still mean EOF: peek without consuming. BufferedReader.peek
    # performs at most one raw read, which select() has promised returns
    # immediately (bytes or b'').
    buffer = getattr(stream, "buffer", stream)
    peek = getattr(buffer, "peek", None)
    if peek is not None:
        try:
            return bool(peek(1))
        except (OSError, ValueError):
            return False
    return True
