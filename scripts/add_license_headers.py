#!/usr/bin/env python3
"""Add Apache 2.0 license headers to all Python source files."""

import pathlib
import sys

PY_HEADER = """\
# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""

TS_HEADER = """\
// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"""

SENTINEL = "Licensed under the Apache License"


def add_headers(root: pathlib.Path, extensions: list[str], header: str) -> int:
    count = 0
    for ext in extensions:
        for f in sorted(root.rglob(f"*{ext}")):
            content = f.read_text(encoding="utf-8")
            if SENTINEL in content:
                continue
            f.write_text(header + content, encoding="utf-8")
            count += 1
            print(f"  + {f}")
    return count


def main():
    project = pathlib.Path(__file__).resolve().parent.parent

    print("=== Adding Python license headers ===")
    py_count = add_headers(project / "backend" / "app", [".py"], PY_HEADER)
    print(f"  Python files updated: {py_count}")

    print("\n=== Adding TypeScript license headers ===")
    ts_count = add_headers(project / "frontend" / "src", [".ts", ".tsx"], TS_HEADER)
    print(f"  TypeScript files updated: {ts_count}")

    print(f"\nTotal: {py_count + ts_count} files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
