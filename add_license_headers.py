#!/usr/bin/env python3
"""
Script to add Apache 2.0 license headers to Python files.
"""

import os
from pathlib import Path

LICENSE_HEADER = '''# Copyright 2025 MonitorX Team
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

'''

def should_add_header(file_path: Path) -> bool:
    """Check if file should have a license header added."""
    # Skip __init__.py files that are just imports
    if file_path.name == '__init__.py':
        content = file_path.read_text()
        # Only add if file has substantial content
        lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
        if len(lines) < 5:
            return False

    # Check if header already exists
    content = file_path.read_text()
    if 'Apache License' in content or 'Copyright 2025 MonitorX Team' in content:
        return False

    return True

def add_header(file_path: Path):
    """Add license header to a Python file."""
    content = file_path.read_text()

    # Handle files with shebang
    if content.startswith('#!'):
        lines = content.split('\n', 1)
        new_content = lines[0] + '\n' + LICENSE_HEADER + (lines[1] if len(lines) > 1 else '')
    else:
        # Handle files with docstrings
        if content.startswith('"""') or content.startswith("'''"):
            # Find end of docstring
            quote = '"""' if content.startswith('"""') else "'''"
            end_idx = content.find(quote, 3)
            if end_idx != -1:
                end_idx += 3
                new_content = LICENSE_HEADER + content
            else:
                new_content = LICENSE_HEADER + content
        else:
            new_content = LICENSE_HEADER + content

    file_path.write_text(new_content)
    print(f"✅ Added header to: {file_path}")

def main():
    """Add license headers to all Python files."""
    src_dir = Path('src/monitorx')
    test_dir = Path('tests')

    py_files = []

    # Collect Python files
    for directory in [src_dir, test_dir]:
        if directory.exists():
            py_files.extend(directory.rglob('*.py'))

    # Filter and process
    added = 0
    skipped = 0

    for py_file in py_files:
        if should_add_header(py_file):
            add_header(py_file)
            added += 1
        else:
            print(f"⏭️  Skipped: {py_file}")
            skipped += 1

    print(f"\n{'='*60}")
    print(f"License headers added: {added}")
    print(f"Files skipped: {skipped}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
