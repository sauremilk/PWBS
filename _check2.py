import json, pathlib
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
blockers = set()
for tid, t in d['tasks'].items():
    if t.get('status') == 'open':
        for b in t.get('blocked_by', []):
            blockers.add(b)
for b in sorted(blockers):
    bt = d['tasks'].get(b, {})
    s = bt.get('status', 'MISSING')
    print(b, s)
