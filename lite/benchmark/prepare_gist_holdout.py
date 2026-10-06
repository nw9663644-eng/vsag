#!/usr/bin/env python3
"""Select held-out GIST query rows, then reuse lite_prepare_gist for exact truth."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preparer', type=Path)
    parser.add_argument('base', type=Path)
    parser.add_argument('queries', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--base-count', type=int, default=100000)
    parser.add_argument('--offset', type=int, default=100)
    parser.add_argument('--count', type=int, default=300)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    with args.queries.open('rb') as source:
        header = source.read(8)
        if len(header) != 8:
            parser.error('truncated query header')
        count, dim = struct.unpack('<II', header)
        if dim != 960 or args.offset < 100 or args.count <= 0:
            parser.error('expected 960D queries, offset>=100 and positive count')
        if args.offset > count or args.count > count - args.offset:
            parser.error('holdout range exceeds source queries')
        if args.queries.stat().st_size != 8 + count * dim * 4:
            parser.error('invalid query payload size')
        source.seek(8 + args.offset * dim * 4)
        selected = source.read(args.count * dim * 4)
    with tempfile.TemporaryDirectory() as temp:
        query_path = Path(temp) / 'selected.fbin'
        query_path.write_bytes(struct.pack('<II', args.count, dim) + selected)
        subprocess.run([str(args.preparer.resolve()), str(args.base.resolve()),
                        str(query_path), str(args.output.resolve()),
                        str(args.base_count), str(args.count)], check=True)
    manifest = {
        'query_source_sha256': sha256(args.queries),
        'base_source_sha256': sha256(args.base),
        'query_offset_zero_based': args.offset,
        'query_count': args.count,
        'previous_tuning_rows': [0, 100],
        'selected_rows_half_open': [args.offset, args.offset + args.count],
        'groundtruth': 'existing lite_prepare_gist exact squared-L2, ascending ID ties',
        'preparer_sha256': sha256(args.preparer),
        'outputs_sha256': {
            str(path.relative_to(args.output)): sha256(path)
            for path in sorted(args.output.rglob('*')) if path.is_file()
        },
    }
    (args.output / 'holdout-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
