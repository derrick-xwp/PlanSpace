"""Measure each replay budget in a fresh, sequential local process."""
from pathlib import Path
import hashlib,json,os,platform,re,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919/cap_resource_by_budget_v1'

def main():
    OUT.mkdir(exist_ok=False)
    rows=[]
    config={'caps':[100,500,1000,2000],'execution':'sequential fresh processes',
            'platform':platform.platform(),'machine':platform.machine(),
            'scope':'Full 171-task scan, construction of 1403 representatives, and validation of the 1034 representatives reaching the original 1000-order cap. Wall time includes process startup and report writing. No model generation or simulation.'}
    (OUT/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    for cap in config['caps']:
        target=OUT/f'cap_{cap}.json'
        cmd=['/usr/bin/time','-l',sys.executable,'scripts/analyze_partial_order_cap_sensitivity.py',
             'artifacts/action_semantics_supported_queue_171_context_v0_1.json',
             'tmp/automation_v05_authoritative_etWEL0/frozen_source','--caps',str(cap),'--output',str(target)]
        print(f'Starting independent cap {cap}',flush=True)
        with (OUT/f'cap_{cap}.log').open('w') as log,(OUT/f'cap_{cap}.resources').open('w') as res:
            subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},stdout=log,stderr=res,check=True)
        raw=(OUT/f'cap_{cap}.resources').read_text()
        timing=re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys',raw)
        rss=re.search(r'(\d+)\s+maximum resident set size',raw)
        assert timing and rss,raw
        result=json.loads(target.read_text())
        assert result['summary']['unique_goal_plan_representative_count']==1403
        assert len(result['representatives'])==1034
        checks=[r['cap_results'][0] for r in result['representatives']]
        assert all(r['cap']==cap and r['all_valid'] and r['valid']==r['checked'] for r in checks)
        rows.append({'cap':cap,'wall_seconds':float(timing[1]),'user_seconds':float(timing[2]),
                     'system_seconds':float(timing[3]),'max_rss_bytes':int(rss[1]),
                     'checked_orders':sum(r['checked'] for r in checks),'valid_orders':sum(r['valid'] for r in checks),
                     'report_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
        (OUT/'progress.json').write_text(json.dumps({'completed':rows,'config':config},indent=2)+'\n')
        print(json.dumps(rows[-1]),flush=True)
    (OUT/'summary.json').write_text(json.dumps({'status':'complete','config':config,'rows':rows},indent=2)+'\n')

if __name__=='__main__':main()
