#!/usr/bin/env python3
"""Replace Apache 2.0 license headers with BSL 1.1 headers in all source files."""

import pathlib
import re
import sys

PY_HEADER = """\
# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""

TS_HEADER = """\
// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"""

SENTINEL = "Business Source License"
OLD_SENTINEL = "Licensed under the Apache License"

# Regex to match old Apache 2.0 header block (Python: # comments)
# Matches both full 14-line headers and short 2-line headers
OLD_PY_HEADER_RE = re.compile(
    r"^# Copyright 2026 Athena Contributors\n"
    r"(?:#[^\n]*\n)*"
    r"(?:# limitations under the License\.\n|# Licensed under the Apache License[^\n]*\n)"
    r"\n?",
    re.MULTILINE,
)

# Regex to match old Apache 2.0 header block (TypeScript: // comments)
OLD_TS_HEADER_RE = re.compile(
    r"^(// Copyright 2026 Athena Contributors\n"
    r"(?://[^\n]*\n)*"
    r"// limitations under the License\.\n)"
    r"\n?",
    re.MULTILINE,
)


def update_headers(
    root: pathlib.Path,
    extensions: list[str],
    new_header: str,
    old_header_re: re.Pattern,
) -> int:
    count = 0
    for ext in extensions:
        for f in sorted(root.rglob(f"*{ext}")):
            content = f.read_text(encoding="utf-8")
            if SENTINEL in content:
                continue
            if OLD_SENTINEL in content:
                new_content = old_header_re.sub("", content, count=1)
                f.write_text(new_header + new_content, encoding="utf-8")
                count += 1
                print(f"  ~ {f} (replaced)")
            else:
                f.write_text(new_header + content, encoding="utf-8")
                count += 1
                print(f"  + {f} (added)")
    return count


def main():
    project = pathlib.Path(__file__).resolve().parent.parent

    print("=== Updating Python license headers ===")
    py_count = 0
    for d in ["backend/app", "backend/tests"]:
        py_count += update_headers(
            project / d, [".py"], PY_HEADER, OLD_PY_HEADER_RE
        )
    print(f"  Python files updated: {py_count}")

    print("\n=== Updating TypeScript license headers ===")
    ts_count = update_headers(
        project / "frontend" / "src", [".ts", ".tsx"], TS_HEADER, OLD_TS_HEADER_RE
    )
    print(f"  TypeScript files updated: {ts_count}")

    print(f"\nTotal: {py_count + ts_count} files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
