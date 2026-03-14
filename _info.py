import json, pathlib
p = pathlib.Path(r'c:\Users\mickg\PWBS\docs\orchestration\task-state.json')
d = json.loads(p.read_text(encoding='utf-8'))
for tid in ['TASK-123', 'TASK-131', 'TASK-144']:
    t = d['tasks'][tid]
    print(f"\n{tid}: {t['title']}")
    print(f"  Priority: {t['priority']}, Effort: {t['effort']}, Area: {t['area']}")