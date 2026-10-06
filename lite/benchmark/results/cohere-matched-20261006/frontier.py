import pathlib,json,subprocess,csv,hashlib
root=pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-matched-20261006')
pilot=root.with_name('vsag-lite-cohere-normalized-20261006')
protocol=json.loads((root/'protocol.json').read_text())
commands=[]; summary=[]; selected={}
for mode in ['default','diverse']:
 build='build-lite-fragment-release' if mode=='default' else 'build-lite-online-diverse-release'
 for budget in protocol[mode+'_budgets']:
  output=root/f'validation-{mode}-{budget}.csv'
  cmd=['taskset','-c','0',build+'/lite_graph_route_probe',str(pilot/f'cohere-100000-{mode}.snapshot'),str(root/'validation/scale-100000'),str(output),str(budget),'uniform','preserve','1']
  commands.append(cmd)
  (root/'validation-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  with output.with_suffix('.log').open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  with pathlib.Path(str(output)+'.api.csv').open() as f: row=next(csv.DictReader(f))
  row.update(mode=mode,budget=budget); summary.append(row)
  print(mode,budget,row['recall_at_k'],flush=True)
  if float(row['recall_at_k'])>=protocol['selection_floor'] and mode not in selected:selected[mode]=budget
(root/'validation-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if len(selected)!=2:raise RuntimeError('No passing point for both modes; final must not run')
frozen={'budgets':selected,'selection_floor':protocol['selection_floor'],'final_floor':protocol['final_floor'],'validation_rows':protocol['validation_rows'],'final_rows':protocol['final_rows'],'protocol_sha256':hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest(),'validation_sha256':hashlib.sha256((root/'validation-summary.json').read_bytes()).hexdigest()}
(root/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n')
print('Frozen',selected,hashlib.sha256((root/'frozen.json').read_bytes()).hexdigest(),flush=True)
