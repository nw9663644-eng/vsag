# Bounded routing changed-vector differential regression

Standalone tool: lite/benchmark/graph_heap_regression.cpp. Candidate production sources624252f; control4fc5191. Raw stdout CSVs encode ordered IDs and hexfloat distances. Snapshot ledgers concatenate each snapshot with a native uint64 length prefix (diagnostic x86_64 artifact, not a new public format).

For each of FP32/FP16/RABITQ8, dimensions1,17,128,96nodes, nonmonotonic negative IDs including INT64_MIN and repeated initial vectors. Build degree4/construction16. Seventeen states per dimension (initial +16epochs). Each epoch performs four whole-vector changed Updates and one Remove/reAdd, maintaining expected input values. Every state Save/Loads and compares every ordered ID/distance before/after loading.
Eight queries x three query budgets4,16,96 x k1,10 x unfiltered/partial/all-rejected filters.
Totals:153 snapshot states,576 whole-vector Updates,144 Removes,144 Adds,22032 query-state combinations, each also verified after reload.

Control/candidate CSVs and ledgers compare byte-for-byte in all three storages, including after mutation. This protects the nearest-search path used by graph mutation. This is bounded synthetic correctness, NOT measured online throughput, prolonged real-data acceptance, or a claim of global exact ANN results.

Compile in the remote repository:
c++ -O3 -DNDEBUG -std=c++17 -Iinclude lite/benchmark/graph_heap_regression.cpp -Lbuild-lite-fp16-simd-release -Wl,-rpath,$PWD/build-lite-fp16-simd-release -lvsag-lite -o /dev/shm/graph_heap_regression

Run each storage twice with LD_LIBRARY_PATH selecting the frozen control or candidate library; argv2 must name a new ledger path. Redirect stdout to a new CSV. Raw artifacts preserve the completed pairs. Their content hashes are independently verifiable via SHA256SUMS and the adjacent performance verify.py. No production instrumentation.
