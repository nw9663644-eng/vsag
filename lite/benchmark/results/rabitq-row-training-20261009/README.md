# RaBitQ training directly from source rows

Production11eb5e0dff58622e81cf1543b4b513419fa539fc; control ed39fa213534b97b2e6251880f399b811d311341. This old/new Lite comparison isolates training-matrix removal; both already release temporary scratch at last use.

train_rows consumes source.VectorAt rows immediately. The finite-value pass precedes the centroid accumulation pass, both preserve row order. Matrix train remains a wrapper of the same algorithm. No assumption of contiguous Backend storage; reusable row scratch is tested at dimensions1/17/128. Finite/centroid/transform checks, seed47 and encoding remain. The source is retained until successful publication.
The test compares model/encoded results for a reused row buffer, rejectsNaN/Inf, and continues the6000 allocation fault positions for build/Add/Update/Remove. Build failures128/143/196 forFP32/FP16/Rabi all preserve source snapshots and allow retry; no escaped errors.

Three alternating pairs per dataset/storage,CPU0,degree16,construction/queryef128,k10,100queries,no warmup,single BLAS/OMP/MKL thread,three fresh loads each. All nine snapshot hashes and ordered neighbor CSVs agree; Recall .978/.914/.961 remains.

| Dataset | Peak RSS control/candidate KiB | Build ms control/candidate | P50 us control/candidate |
| --- | ---: | ---: | ---: |
| SIFT10k |29076/28908|617.319/626.475|87.908/86.900|
| GIST10k |135028/134820|1791.146/1825.540|172.236/183.606|
| Cohere10k |110400/110536|1782.516/1789.801|182.897/180.997|

Overall peak is effectively unchanged: the previous lifetime optimization had already separated training scratch from the dominant temporary graph peak. Build timings are slightly worse in these cells, query timing is mixed (GIST P50+6.60%). No end-to-end memory or latency improvement is claimed from these medians. The concrete benefit is eliminating a full training matrix allocation/copy and its stage-specific footprint.

Independent ordinary-new allocation diagnostic (synthetic2048rows):
| Dim | Requests control/candidate | Requested bytes control/candidate | Removed bytes |
| --- | ---: | ---: | ---: |
|128|103088/103087|47547115/46498539|1048576|
|768|103087/103086|67208747/60917291|6291456|

Exactly one ordinary allocation and N*D*4 requested bytes disappear. Matrix-size requests fall3’1: the floating graph still owns one full FP32 matrix. These are intercepted ordinary new requests, not aligned allocations, allocator-reserved capacity, RSS or formal latency.
Probe source lite/benchmark/rabitq_build_allocation_probe.cpp SHA2561bf8559b1f16435eeb9df965942ea7149796fe16813309554d7a7fc52da765c8; binary181bd034d60eb34b8fe97a01ccb7f02d2976a2f9c31d0b091dda58eb4dde0858.
Compile c++ -O3 -DNDEBUG -std=c++17 -Iinclude lite/benchmark/rabitq_build_allocation_probe.cpp -Lbuild-lite-fp16-simd-release -Wl,-rpath,$PWD/build-lite-fp16-simd-release -lvsag-lite -o NEW_PROBE.
Run NEW_PROBE2048 DIM twice selecting control/candidate directories via LD_LIBRARY_PATH. stdout is a CSV. Invalid/out-of-range shapes fail.

Validation Release6/6,ASan/UBSan8/8,coverage6/6,default-off4/4; production Lite2623/2763=94.9330%. format15/tidy15/diffcheck pass. Early new-test exception-type assertion and pre-existing test tidy diagnostics were corrected, then all affected suites rerun.
Control library0d3482f1d8795d41308f1c8e55a9f89f02b084382951f3e943c7666fdf1eb4a5; candidate28bbe034658e0dfc29c635946348986c80162314d829b0da767cf3f20e409096. identity captured ed39fa2 plus exact dirty patch; commit11eb5e0 was made while experiments ran, without changing measured binaries.

raw/identity/rows/summary/SHA preserve inputs,commands,neighbors,quantiles,peaks and the allocation/fault diagnostic. Run python3 verify.py with the adjacent Cohere100k archive. Reproduce driver arguments from identity with matching libraries. Warm/uncontrolled cache,non-isolated host,100queries and zero measured CRUD rounds limit conclusions. All-data100k final quality,matched native Full,long changed-valueCRUD,cold loading,larger queries,fresh Full/package closure remain pending.
The next peak target is temporary floating graph vector ownership during RaBitQ topology construction; a borrowed read-only source path needs independent failure and topology validation.
