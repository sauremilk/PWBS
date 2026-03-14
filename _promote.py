import json, pathlib
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
promoted = []
for tid, t in d['tasks'].items():
    if t.get('status') == 'open':
        blockers = t.get('blocked_by', [])
        all_done = all(d['tasks'].get(b, {}).get('status') == 'done' for b in blockers)
        if all_done:
            t['status'] = 'ready'
            promoted.append(tid)
p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'Promoted {len(promoted)} tasks to ready: {sorted(promoted)}')