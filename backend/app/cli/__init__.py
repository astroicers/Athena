"""Athena backend CLI tools (SPEC-054+).

These modules are intended to be invoked as ``python -m app.cli.<name>``
from inside the backend container — they read ``settings`` from the
standard ``.env`` + ``Settings`` pipeline and write text output to
stdout or stderr. No daemon/server state is involved.
"""
