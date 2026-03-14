import json, pathlib
from collections import Counter
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
statuses = Counter()
for tid, t in d['tasks'].items():
    statuses[t.get('status','unknown')] += 1
print('Status counts:', dict(statuses))
for tid, t in d['tasks'].items():
    s = t.get('status')
    if s not in ('done',):
        stream = t.get('stream','?')
        blocked = t.get('blocked_by','[]')
        print(f'  {tid}: stream={stream}, status={s}, blocked_by={blocked}')