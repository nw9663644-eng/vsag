# Isolated RaBitQ Update incoming-protection candidate: NOT default

Source evidence: floating GraphBackend::ensure_incoming protects an orphan target
by replacing a locally farthest edge whose displaced target has indegree>1.
The prototype adapts that rule to RaBitQ decoded-source/complete-code estimates.
After Update repair, it considers only the changed slot and old outgoing neighbors.
One temporary indegree table is counted from all edges; no permanent reverse index.
Changed rows are remembered before replacement, sync_incoming maintains optional
reverse metadata, and the existing Update journal rolls back allocation failures.
Degree/query budget/model/API/serialization are unchanged; default source restored.

| Dataset | Final Recall control/candidate | Mutation block ms control/candidate | Change |
| --- | --- | --- | --- |
| GIST | .858667/.897667 |14156.706/18884.981|+33.40%|
| Cohere | .935500/.951500 |11971.429/15982.726|+33.51%|

Single paired process per dataset; GIST control first,Cohere candidate first.
Same three full-ID passes,30000 genuine Update operations;600 old observed queries,
degree16/construction128/query512/k10/CPU0/one BLAS/OMP thread,no diagnostic scans.
ldd/library/source hashes bind each process to the correct isolated/control library.
Initial ordered results are byte-exact. Each final SaveLoad preserves all ordered
IDs and float distances. Final topology is intentionally different, not byte-equivalent.

Positive quality signal on both distributions, but GIST remains below .90 study
floor and cost grows ~one third. No statistical/generalization claim from this
single pair; neither threshold is an official OSPP numerical requirement.
Not adopted. Next candidate needs cheaper degree accounting and stronger local
connectivity selection, plus repeated/100k/mixed validation. Do not increase ef
to conceal the original failure, or call the prototype a complete graph-quality fix.

Candidate Release tool fixture passed; candidate instrumented library SAN CTest5/5,
including allocation rollback, passed. Candidate format/tidy15 header checks passed;
default header restored and default SAN5/5 rerun passed. No new candidate coverage,
OFF-build or Full-suite acceptance claimed. Prototype header/patch/build commands
and all raw records/logs preserved. Actual formatted header is the exact build
source; candidate.patch is the pre-format semantic patch, run format15 after apply.
Existing Release default library never overwritten; isolated library remains on host.
Default source,source/data/raw preserved; only new RAM snapshots hashed/load-checked
then guard-deleted. Published verifier lives in adjacent model-ceiling directory.
