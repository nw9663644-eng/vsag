import pathlib,json,subprocess,csv
root=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-matched-20261006')
inputs=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-online-20261006')
protocol={'source_commit':'fd67861a7f91a9eef4a42a3978d10375d0682230','validation_rows':[100,400],'final_rows':[400,700],'target_recall':0.95,'selection_floor':0.955,'default_budgets':[64,96,128,160,192,256],'diverse_budgets':[32,48,64,96,128,192],'selection':'smallest tested budget reaching selection floor on validation; freeze before final preparation','maintenance_budget':128,'degree':16,'cpu':0,'cycles':2000,'query_every':[1,10],'replicates':3,'queries':'previously unmeasured SIFT source ranges; no retuning after final'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[]; chosen={}
for mode in ['default','diverse']:
 build='build-lite-fragment-release' if mode=='default' else 'build-lite-online-diverse-release'
 for budget in protocol[mode+'_budgets']:
  output=root/f'validation-{mode}-{budget}.csv'
  cmd=['taskset','-c','0',build+'/lite_graph_route_probe',str(inputs/(mode+'.snapshot')),str(root/'validation/scale-100000'),str(output),str(budget),'uniform','preserve','1']
  commands.append(cmd)
  with (root/f'validation-{mode}-{budget}.log').open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  with pathlib.Path(str(output)+'.api.csv').open() as f: row=next(csv.DictReader(f))
  recall=float(row['recall_at_k']); print(mode,budget,recall,flush=True)
  if recall>=protocol['selection_floor'] and mode not in chosen: chosen[mode]=budget
(root/'commands-frontier.json').write_text(json.dumps(commands,indent=2)+'\n')
assert len(chosen)==2
(root/'frozen.json').write_text(json.dumps(chosen,indent=2)+'\n')
print('FROZEN',chosen,flush=True)
