# RaBitQ construction scratch: GIST100k confirmation

Controlb0434c8, candidatecbaea1f with entry error fixadae3a8. Same frozen libraries as the adjacent10k report. Both include prior exact floating-graph reservation. Three alternating pairs,degree16,construction128,queryef512,CPU0,k10,100queries,three fresh loads each,single BLAS/OMP/MKL thread.

Median external build peak1688177’1307480KiB(-22.55%). Bulk build33919.079’33340.713ms(-1.71%,small host variation). P50 query1235.813’1077.297us,P99 1566.397’1473.798us, but query code is unchanged and mixed10k timing prevents attributing a general speedup. Retain all per-trial samples.
Recall .859 in every process; this fixed-budget100k quality is below the research floor. All three snapshot hashes and ordered neighbor exports agree. Snapshot112804416bytes unchanged. Loaded RSS121660/121620KiB,warm load71.810/71.698ms effectively unchanged.

The training FP32 copy no longer overlaps temporary graph construction; the temporary graph no longer overlaps final mutable state construction. The original source is retained until commit. Cross-platform allocator behavior may differ. This is build peak memory evidence, not matched-quality native Full comparison or lasting CRUD acceptance.
identity/rows/summary/raw/checksums retain all evidence. Source diff was captured atb0434c8 before production commits, matching measured library hashes. Run ../rabitq-build-lifetimes-20261009/verify.py.
Warm/uncontrolled cache,100queries,non-isolated host. Full/current quality comparison,other100k repeats,long changed-value real-dataCRUD,cold load,larger queries,fresh Full and package closure remain pending.
