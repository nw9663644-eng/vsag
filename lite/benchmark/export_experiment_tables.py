# Copyright 2026 The VSAG Authors. Licensed under the Apache License, Version 2.0.
"""Export recorded experiment tables; never rerun or infer acceptance metrics."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin


def tables(text):
    found, fenced, i = [], False, 0
    lines = text.splitlines()
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(("```", "~~~")):
            fenced = not fenced
        if not fenced and line.startswith("|") and i + 1 < len(lines):
            header = [x.strip() for x in line.strip("|").split("|")]
            divider = [x.strip() for x in lines[i+1].strip().strip("|").split("|")]
            if len(divider) == len(header) and all(re.fullmatch(r":?-{3,}:?", x) for x in divider):
                start, rows = i, []
                i += 2
                while i < len(lines) and lines[i].strip().startswith("|"):
                    row = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                    if len(row) != len(header):
                        raise ValueError(f"Malformed table at line {i+1}")
                    rows.append(row)
                    i += 1
                found.append(dict(header=header, rows=rows))
                continue
        i += 1
    return found


def collect(root):
    paths = sorted((root/'results').glob('*/README.md'))
    if not paths:
        raise ValueError('No result reports')
    paths += [root/'FINAL_REPORT.md', root/'ACCEPTANCE_REPORT_20261006.md']
    reports = []
    for path in paths:
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        reports.append(dict(path=path.relative_to(root).as_posix(), text=text,
                            sha256=hashlib.sha256(raw).hexdigest(), tables=tables(text)))
    return reports


def escape(value):
    return value.replace('|', '&#124;').replace(chr(10), ' ')


def export(root, output, revision):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Expected full Git SHA')
    if (root/'results').resolve() in (output.resolve(), *output.resolve().parents):
        raise ValueError('Output must be outside results')
    reports = collect(root)
    base = f'https://github.com/nw9663644-eng/vsag/blob/{revision}/lite/benchmark/'
    lines = ['# All recorded Lite experiments / Lite全部实验数据表', '',
             'Existing evidence only: no new benchmark, raw-data verification or project-wide acceptance.',
             '仅汇总已有证据；不重跑实验、不校验原始制品、不推算吞吐、不补缺项、不判定全项目达标。', '',
             f'Source revision / 资料提交: `{revision}`. Measured versions remain in each source.',
             '每次实验的被测提交、参数和单位仍以来源为准，不拼接为最新版最优结果。', '',
             '## Inventory / 报告索引', '', '| Report | Tables | Rows | SHA256 |', '|---|---:|---:|---|']
    for r in reports:
        count = sum(len(t['rows']) for t in r['tables'])
        lines.append(f"| [{r['path']}]({base}{r['path']}) | {len(r['tables'])} | {count} | {r['sha256']} |")
    lines += ['', '## All table rows together / 全部数据行连续总表', '',
              'Different studies retain their original column names and units. Do not rank unlike workloads.', '',
              '| Report | Table | First column / 配置或指标 | Remaining columns / 原始数值 |', '|---|---:|---|---|']
    for r in reports:
        for number,t in enumerate(r['tables'],1):
            for row in t['rows']:
                metrics = '; '.join(f'{k}={v}' for k,v in zip(t['header'][1:],row[1:]))
                lines.append(f"| [{r['path']}]({base}{r['path']}) | {number} | {escape(row[0])} | {escape(metrics)} |")
    lines += ['', '## Original protocols and limitations / 完整协议与限制', '',
              'Includes prose-only historical measurements and reports without tables.', '']
    for r in reports:
        url = base+r['path']
        body = re.sub(r'^#{1,6} +(.+)$', r'#### \1', r['text'], flags=re.M)
        body = re.sub(r'\[([^\]\n]+)\]\(([^\s)]+)\)', lambda m:f'[{m[1]}]({urljoin(url,m[2])})',body)
        lines += [f"### {r['path']}", '', f'[Source]({url})', '', body.rstrip(), '']
    metadata = dict(scope='Published summaries only; not a raw-data/performance rerun',
                    source_revision=revision, report_count=len(reports),
                    table_count=sum(len(r['tables']) for r in reports),
                    row_count=sum(len(t['rows']) for r in reports for t in r['tables']),
                    sources=[{k:r[k] for k in ('path','sha256','tables')} for r in reports])
    output.mkdir(parents=True,exist_ok=False)
    (output/'ALL_EXPERIMENTS.md').write_text(chr(10).join(lines)+chr(10),encoding='utf-8')
    (output/'tables.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,help='New directory outside results')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    revision = subprocess.check_output(['git','-C',str(root.parents[1]),'rev-parse','HEAD'],text=True).strip()
    result = export(root,args.output,revision)
    print(json.dumps({k:result[k] for k in ('source_revision','report_count','table_count','row_count')}))


if __name__ == '__main__':
    main()
