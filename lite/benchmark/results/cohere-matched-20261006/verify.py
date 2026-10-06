from pathlib import Path
import json,csv,math
out=Path(__file__).parent
frozen=json.loads((out/'frozen.json').read_text())
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
validation=json.loads((out/'validation-summary.json').read_text())
for r in validation:
 prefix=out/'validation'/f"validation-{r['mode']}-{r['budget']}.csv"
 values=sorted(float(t['latency_us']) for t in read(Path(str(prefix)+'.api.csv.latencies.csv')))
 assert len(values)==300
 assert abs(values[149]-float(r['search_p50_us']))<1e-5
 assert abs(values[296]-float(r['search_p99_us']))<1e-5
 assert int(r['configured_ef_search'])==128 and int(r['query_ef_search'])==r['budget']
 assert abs(sum(int(t['hits']) for t in read(prefix))/3000-float(r['recall_at_k']))<1e-6
for mode in ['default','diverse']:
 assert min(r['budget'] for r in validation if r['mode']==mode and float(r['recall_at_k'])>=frozen['selection_floor'])==frozen['budgets'][mode]
for r in json.loads((out/'final-summary.json').read_text()):
 assert int(r['initial']['configured_ef_search'])==128
 assert int(r['initial']['query_ef_search'])==frozen['budgets'][r['mode']]
 prefix=out/'final'/f"final-every{r['query_every']}-rep{r['repeat']}-{r['mode']}.csv"
 assert abs(sum(int(t['hits']) for t in read(prefix))/6000-float(r['initial']['recall_at_k']))<1e-6
print('Validation percentiles/counts, fixed budgets, minimal passing selection and all scalar/API aggregate recalls passed.')
