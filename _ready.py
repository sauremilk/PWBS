import json, pathlib
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
for stream in ['STREAM-PHASE3','STREAM-PHASE4','STREAM-PHASE5','STREAM-DSGVO-QA']:
    ready = [tid for tid, t in d['tasks'].items() if t.get('stream') == stream and t.get('status') == 'ready']
    if ready:
        print(f'{stream}: {sorted(ready)}')