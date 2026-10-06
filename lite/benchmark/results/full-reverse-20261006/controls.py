import json,resource,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
records=[]
for mode in ['remove','update-remove','last-remove','restored']:
 for repeat in range(3):
  cmd=['taskset','-c','0',str(root/'delete_reproducer'),mode]
  result=subprocess.run(cmd,capture_output=True,text=True)
  (root/f'control-{mode}-{repeat}.log').write_text(result.stdout+result.stderr)
  records.append({'mode':mode,'repeat':repeat,'command':cmd,'returncode':result.returncode})
(root/'controls.json').write_text(json.dumps(records,indent=2)+'\n')
print(records)
