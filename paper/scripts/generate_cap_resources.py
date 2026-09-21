"""Generate appendix resource rows only from the completed per-budget audit."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'artifacts/reviewer_revision_20260919/cap_resource_by_budget_v1/summary.json'
data=json.loads(source.read_text())
assert data['status']=='complete'
assert [r['cap'] for r in data['rows']]==[100,500,1000,2000]
lines=[r'\begin{table}[t]',r'\centering\small',
       r'\caption{Replay-cap resources on macOS arm64. Each row is one fresh, sequential process scanning 171 tasks and constructing 1,403 representatives, then checking the 1,034 originally capped representatives. All checked orders are valid. Wall time includes process startup and report writing; RSS is peak resident memory.}',
       r'\label{tab:cap-resources}',r'\begin{tabular}{rrrrr}',r'\toprule',
       r'Cap & Checked orders & Wall (s) & CPU (s) & RSS (MiB) \\',r'\midrule']
for r in data['rows']:
    assert r['checked_orders']==r['valid_orders']
    lines.append(f"{r['cap']:,} & {r['checked_orders']:,} & {r['wall_seconds']:.2f} & {r['user_seconds']+r['system_seconds']:.2f} & {r['max_rss_bytes']/2**20:.2f} "+r'\\')
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}']
(ROOT/'paper/generated_cap_resources.tex').write_text('\n'.join(lines)+'\n')
(ROOT/'paper/data/cap_resources_manifest.json').write_text(json.dumps({'source':str(source.relative_to(ROOT)),
    'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':data['rows']},indent=2)+'\n')
print('Generated four independently measured cap rows.')
