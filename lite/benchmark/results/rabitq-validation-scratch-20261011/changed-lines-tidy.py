import json
import subprocess
from pathlib import Path

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
files = ['src/lite/rabitq_backend.cpp', 'src/lite/rabitq_backend_test.cpp']
line_filter = [dict(name='rabitq_graph_state.h', lines=[[657, 708], [1355, 1385]]),
               dict(name='rabitq_backend_test.cpp', lines=[[1350, 1450]])]
result = subprocess.run(['clang-tidy-15', '-p', 'build-lite-fp16-simd-release', *files,
    '--header-filter=.*/src/lite/.*', '--line-filter=' + json.dumps(line_filter)],
    cwd=repo, capture_output=True, text=True)
Path('/home/ubuntu/project/vsag-validate-scoped-tidy-20261011.log').write_text(
    result.stdout + result.stderr)
print('changed-line tidy exit:', result.returncode)
raise SystemExit(result.returncode)
