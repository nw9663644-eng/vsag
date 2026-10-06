# Acceptance consolidation verification

Run from any directory:

```text
python3 PATH/lite/benchmark/results/acceptance-20261006/verify.py
```

Requires Python3 standard library only. Checks five existing evidence manifests
(491 artifacts), local report links, summary-derived workload CPU medians/changes,
quality floors, corrected Full pass/short-result flags, and load-only medians.
Writes audit.json with the report hash and derived workload values. This checks
published summaries and hashes; it does not independently rerun raw truth audits,
experiments, library tests or coverage. Existing raw audit results remain linked
from each study. The parent acceptance report records measured-version boundaries.
