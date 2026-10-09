# Exact graph build reservation: GIST100k confirmation

Production e7dc151 versus frozen3242489 control. Old/new Lite, not Full. Same method as the adjacent10k report, but GIST100k and queryef512. Three alternating pairs per FP32/FP16, three fresh loads each, CPU0, degree16/construction128,k10,100queries.

| Storage | Peak RSS control/candidate KiB | Reduction | Build ms control/candidate | Recall |
| --- | ---: | ---: | ---: | ---: |
| FP32 |1316288/1215700|7.64%|30445.429/30091.798|.860|
| FP16 |1070580/994264|7.13%|29922.727/30028.261|.865|

All six snapshot hashes and ordered neighbor exports are identical. Snapshot size is unchanged (398400064 FP32;206400064 FP16). Loaded RSS and warm load latency are unchanged. Build time is effectively flat and no speedup is claimed.
The smaller percentage at100k is expected: exact reserve removes vector growth slack and transient reallocation, but transactional BuildGraph still retains the full BruteForce source until success. Further reduction requires a separately designed recoverable ownership transfer, not premature source destruction.

Recall is below the research quality floor at this fixed construction/query budget.100 historical queries do not establish production P99. Page cache is warm/uncontrolled; host is not isolated. This confirms peak-memory behavior, not final100k quality, cold-start, or lasting CRUD acceptance.
Use ../graph-build-reserve-20261009/verify.py for offline verification.
