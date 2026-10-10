# Rejected grouped mutation membership scan (2026-10-10)

The candidate is rejected. Production header and tests are restored byte-exact to
194bf868b4197e0f4b60a4e7c84648dd5c5fed21, including the retained Batch4 maintenance optimization.
No new production gain, quality repair, query improvement or Full comparison is claimed.

## Source evidence / minimal candidate

MutableGraphState::UpdatePrepared and Remove<skip_unchanged> scan outgoing rows
to locate references to the changed slot (or removed and last slots).
The existing reverse-adjacency option avoids that scan, but its transactions
copy the entire state; enabling it alone is not a proven default optimization.
The tried helper row_references_slot groups four integer equality tests with
bitwise OR, then handles tails. It only gates the ORIGINAL erase/rewrites/journal;
no persistent cache, extra graph memory, SIMD ISA/kernel, topology policy,
model, distance, degree/ef, API, snapshot or rollback change.
This grouped comparator is our adaptation of the existing scalar gate,
not a claimed newly discovered official SIMD kernel.
The new golden test checks lengths0..129, every position, absent/present,
duplicates, equal two-target arguments and uint64 maximum values.
Initial test-only lambda capture compile error and incorrect background-value
expectation were repaired before measurement; both original logs are retained.
No product behavior or performance code was changed by those repairs.

## Frozen paired workload and decision

Both public adapters NONE. GIST/Cohere10k,600 historical observed queries,k10,
degree16,maintenance128/query512,CPU0 and BLAS/OMP/MKL1.
Three alternating pairs per dataset, each builder three full-ID true changed-value
Update/Remove/Add passes (90000 operations). Twelve builders total.
No compilation/testing ran concurrently with timing.

| Dataset | Control CRUD median ms | Candidate median ms | Change |
| --- | ---: | ---: | ---: |
| gist10k600 | 25347.658511 | 28262.974059 | +11.501% |
| cohere10k600 | 22040.128327 | 25136.849029 | +14.050% |


All six paired total times regress. Do not retain this candidate merely because
the source looks more grouped/vectorizable. These are workload observations,
not statistical/universal regression or proof of a specific CPU cause.
Initial/final ordered IDs, hex distances and hits are paired byte-exact;
all snapshot SHAs match, with native exact Save/Load in every builder.
Recall remains .811167/.908167. The known quality deficit is unchanged.

## Validation, evidence and limits

Candidate Release6 and ASan/UBSan5 passed; restored Release6 and ASan/UBSan5
passed, including allocation rollback. Final restored format/tidy15 passed.
Candidate was formatted15 before timing; no independent candidate tidy claim.
No fresh coverage/OFF/whole Full/Node checker run here; inherited unchanged
Lite coverage95.18% is the parent's scoped result, not new coverage.
Restored default library SHA is a2d6d97feec56d7b05c68319566d659111d6413543ec8314796a575dff8c24b7.
Source/header/test restoration, 1080000 operations,14400 truth intersections,
raw quantiles/throughput, dependency binding and file hashes are independently audited.

raw.tar.gz contains actual measured runner, complete old/new headers and test,
patch, commands, compile/link receipts, loader binding, actual queries/truth,
operation and search latencies, initial/final ordered results/hits, validation logs.
Large replacements regenerate from preserved base/recipe with SHA receipts;
they are not falsely claimed archived. summary.json contains per-operation
P50/P99 and whole CRUD throughput. Snapshot files were only removed from new
RAM paths after exact Load and SHA checks; original data/source/raw are preserved.

After timing, an idle old Full static archive1301968226 bytes was removed,
not Full shared libraries. Before removal all219 missing objects' compiler recipes,
source files, include directories and compiler executable were verified.
Objects were ALREADY absent; no claim that they were preserved or that rebuilding
is byte-identical. raw/cleanup.json preserves target/hash/manifest/recipes.
Rebuild: cmake --build build-full-comparison-library --target vsag_static.
The first conservative object-existence check stopped before deletion;
the stronger source/dependency checks established reconstructibility.
No old dataset/source/raw/shared library deletion or coverage counter cleanup here.

On the recorded host run python3 PATH/verify.py for offline audit.
For host replay, use the recorded base checkout, measured Release tool/compiler
and preserved dataset/dependency paths, copy run-host.py to a NEW empty result
directory and execute from repository root with TMPDIR=/dev/shm.
The helper pins the archived rejected candidate instead of restored HEAD;
it is syntax-checked only, not rerun. raw/measured-run-host.py is the script actually run.
SHA256SUMS binds canonical files.
Future work should avoid replaying this negative experiment: evaluate reverse-row
journaling/local affected-source maintenance with explicit memory costs, not
simply switch on full-copy reverse transactions. 100k, interleaved changed-value
CRUD, fresh aligned native Full, cold I/O and complete package acceptance remain open.
