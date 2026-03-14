import json, pathlib, datetime
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now(datetime.UTC).isoformat()
claims = [('TASK-123','ORCH-J'),('TASK-131','ORCH-K'),('TASK-144','ORCH-L')]
for tid, orch in claims:
    d['tasks'][tid]['status'] = 'in_progress'
    d['tasks'][tid]['claimed_by'] = orch
    d['tasks'][tid]['claimed_at'] = now
p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8')
print('Claimed:', [c[0] for c in claims])