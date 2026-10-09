# RaBitQ row training: Cohere100k confirmation

Control ed39fa2, candidate11eb5e0, frozen matching libraries as adjacent10k report. Cohere normalized100k(dim768), three alternating pairs, CPU0,degree16,construction128,query512,k10,100queries,single BLAS/OMP/MKL thread,three fresh loads each,warm/uncontrolled page cache.

Median external peak1063716/1063712KiB: no peak-memory gain. Bulk build32653.892/33266.948ms(+1.88%). QueryP50 1170.064/1113.045us(-4.87%),P99 1397.690/1327.881us. Query implementation is unchanged;10k timings are mixed, so no general speedup claim.
Snapshot93603552bytes,Recall.937 in every process, all three snapshot hashes and ordered ID/distance exports identical. Warmload64.215/63.199ms andloadedRSS102904/102868KiB are approximately flat.

The allocation probe establishes removal of N*D*4 training bytes requested, but dominant temporary floating graph storage keeps the overall peak unchanged. This distinction is essential to interpreting the optimization. Current fixed query budget remains below the desired100k recall floor.100 historical queries are insufficient for robustP99; host is not isolated; zero-roundCRUD is not online mutation throughput.
identity captured ed39fa2 with measured dirty production patch; sources committed11eb5e0 during run without modifying binaries. raw/rows/summary/SHA and ../rabitq-row-training-20261009/verify.py preserve and independently check evidence.
Next work: borrow source rows in topology-only floating construction, then matched-quality nativeFull/all-data100k,lasting real changed-valueCRUD,cold cache,larger cohorts,freshFull/package closure.
