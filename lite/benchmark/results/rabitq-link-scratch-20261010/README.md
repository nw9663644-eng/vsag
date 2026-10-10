# Rejected RaBitQ bounded link-ranking scratch (2026-10-10)

Personal experiment/lite-rabitq-next-20260926, measured parent
cd8e91edfefd7c57c8aee870a7efe14a22dedcf1. Production candidate REJECTED.
src/lite/rabitq_graph_state.h was restored byte-exact to parent. Keep the new
degree64/tied-code saturation regression and this negative evidence; PR2904/2926
are unchanged. No production speedup or completed project acceptance is claimed.

## Source evidence, candidate and exclusions

Floating src/lite/graph_backend.cpp::link already uses
std::array<Candidate,K_MAX_DEGREE+1> for ranking a saturated row.
RaBitQ MutableGraphState constructor enforces degree2..64, but link allocated a
temporary vector on every saturated pruning. The isolated candidate used the
same bounded scratch pattern, initialized65 Candidate entries, filled/sorted only
the active prefix, and shared a named64 degree limit with its constructor.
Distances,comparator,ties,pruning,protection,transactions,model and stored format
were unchanged. No query/graph budget or API changed. The candidate adds roughly
1040 bytes of local Candidate storage; no measured latency benefit was established.
Do not infer a specific CPU cause from the negative timing alone.

Public policy is NONE in BOTH timed variants. This is not the previous protected
policy or a native Full comparison. The internal incoming protection remains
experimental/default-disabled. Remaining CRUD recall failures are not solved.

## Frozen three-pair protocol

10k GIST/Cohere,600 historical observed queries each,k10,degree16,
construction/maintenance128,query512,CPU0,one thread. Three full-ID real changed-vector
Update/Remove/Add passes,90000 mutations per builder. Three alternating pairs per
dataset,12 fresh builders total; variant order reverses by dataset/repeat.
No concurrent builds/tests or benchmark reruns.

Both adapters use identical public NONE behavior. A leading -I RAM overlay with
lite/rabitq_graph_state.h binds control to the exact parent header and candidate
to the modified header. -MM receipts were recorded BEFORE timing,including the
actual overlay path and header SHA. Full adapters/compile/link/ldd/argv are archived.

| dataset | variant | CRUD median ms | final Recall | query median P50/P99 us | median peak KiB |
| --- | --- | ---: | ---: | ---: | ---: |
| GIST | parent | 25718.252616 | .811167 | 413.931/475.000 | 219528 |
| GIST | bounded scratch | 26172.748829 | .811167 | 414.382/475.719 | 219504 |
| Cohere | parent | 22525.060306 | .908167 | 405.221/454.350 | 176700 |
| Cohere | bounded scratch | 22764.976541 | .908167 | 425.112/474.650 | 176712 |

CRUD median changes+1.77%/+1.07%; paired individual changes:
GIST+2.0589%,+1.1895%,-1.4013%; Cohere+.7592%,+1.0651%,-1.9839%.
The direction changes across pairs; this is no stable improvement,not proof of
universal regression or statistical significance. No meaningful memory advantage. Peak is whole-builder RSS including input,build,
CRUD,query and persistence,not index-only or load-only memory.
Do not adopt a micro-optimization solely because a temporary allocation disappeared.

Every pair's initial/final hits,ordered ID/hex-distance CSVs and full snapshot SHA
are identical. Snapshot bytes11284416/9363552 remain unchanged. Every builder
natively Save/Loads its own final ordered query results exactly.
These NONE recalls still fail study floors.90/.95 (not official OSPP numeric rules),
and must not be confused with previous guarded .855167/.924500 results.
Candidate performance failure cannot be concealed by raising degree or ef.

## Validation and rollback

Candidate Release6/6 and internally protected ASan/UBSan5/5 passed.
After restoring production,Release6/6,default ASan/UBSan5/5,fresh Coverage5/5,
RaBitQ-disabled4/4,clang-format/tidy15 passed. Candidate was formatted with15 before
timing; no separate candidate tidy or candidate coverage claim.
The final new test uses65 records,degree64,17 dimensions,tied codes,saturated
Add/Update,reverse adjacency on/off,full ordered Save/Load and Remove.

6000 allocation positions per SAN configuration,three storages/four operations:
candidate guarded RaBitQ actual failures Add47/Update68/Remove39/Build192;
restored NONE Add44/Update65/Remove38/Build192. Both had zero changed-after-failure,
invalid snapshot or escaped exception. The policies differ,so these two failure
totals are not an apples-to-apples allocation/performance comparison.

Fresh RESTORED-production coverage: Lite2850/2995=95.1586%,shared instantiated
SIMD233/249=93.5743%,combined3083/3244=95.0370%; excludes tests,not whole Full.
Node documentation checker and Full entire suite were not run.
Restored default Release SHA1a18379a28b8e7d276b054b3a1a323cc28ecfae2a8d7b5ba965539ddd67be22f.

## Evidence and replay

raw.tar.gz:187 members,11534958 bytes,including full old/candidate/final header,
candidate.patch,measured runner,validation script,sources,compact inputs/truth,
operation/query CSVs,compile binding receipts and successful logs.
Fresh raw gcov is separate. verify.py audits1080000 mutations,14400 truth intersections,
all paired snapshots/ordered results,raw quantiles/throughput/comparison medians,
12 validation exits,restored header hash and fresh coverage/hash manifests.

The first offline audit incorrectly expected repository /src/lite/ dependency
paths; actual recorded paths are RAM /lite/ overlays as designed. The verifier
was corrected to assert identity-bound overlay paths; no benchmark or product test
was repeated. Production restoration is deliberate; timed candidate and final
source identities are distinct in validation.json.

Large replacements are reconstructed from preserved base+recipe/SHA,not archived.
New RAM snapshots were natively loaded and SHA-recorded before guarded deletion;
offline audit cannot reread them or independently rerun full exhaustive GT.
No old sources,data,raw evidence or objects were removed.19 verified generated
gcda counters were cleared for fresh coverage. RAM libraries are not claimed
to survive the session.

Copy run-host.py into a NEW empty result directory,run from this matching final
repo with preserved host datasets/compile objects. It reads the exact rejected
candidate header from this committed raw archive,not restored production HEAD.
The original executed runner is raw/measured-run-host.py; final replay adaptation
is not a new timing run. Never overwrite original rows/results.
Next prioritize stage measurement of decode_query,incoming-row scan and neighbor
scoring before proposing another production optimization. Remaining route-quality,
100k persistent/interleaved CRUD,fresh Full config/SIMD matching and cold I/O
acceptance still need work.
