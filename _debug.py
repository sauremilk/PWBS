import json, pathlib
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
t123 = d['tasks'].get('TASK-123', {})
print('TASK-123:', t123)
print('Status:', repr(t123.get('status')))
print('Blocked by:', t123.get('blocked_by'))
for b in t123.get('blocked_by', []):
    bt = d['tasks'].get(b, {})
    print(f'  Blocker {b}: status={repr(bt.get("status"))}')