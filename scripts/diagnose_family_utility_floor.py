"""Report stress-test floor and selection opportunity, without changing selection."""
from pathlib import Path
from collections import defaultdict
import hashlib,json

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/reviewer_revision_20260919'

def main():
    source=OUT/'family_utility_heldout_v1.json';data=json.loads(source.read_text())
    inputs=json.loads((OUT/'fireplace_repair_verification.json').read_text())['models'];report=[]
    for model in inputs:
        p=ROOT/model['corrected_artifact'];assert hashlib.sha256(p.read_bytes()).hexdigest()==model['sha256']
        matrix=json.loads(p.read_text());oracle=defaultdict(list);rows=[];eligible=0;nonempty=0;unique_four=0
        for task in matrix['tasks']:
            if task['activity'] not in data['coverage']:continue
            plans=[s['parsed_plan'] for s in task['samples'] if bool((s.get('execution') or {}).get('valid'))]
            nonempty+=bool(plans);eligible+=len(plans)>3;unique_four+=len({tuple(p) for p in plans})>3
            for kind,blocked in data['coverage'][task['activity']].items():
                if blocked is None:continue
                survived=sum(not(set(p)&set(blocked)) for p in plans)
                oracle[task['activity']].append(int(survived>0))
                rows.append({'task':task['activity'],'scenario':kind,'valid_candidates':len(plans),'surviving_candidates':survived})
        rate=sum(sum(v)/len(v) for v in oracle.values())/len(oracle)
        method_rates={r['method']:r['task_macro_survival'] for r in data['summary'] if r['model']==model['model']}
        assert all(v<=rate+1e-12 for v in method_rates.values())
        report.append({'model':model['model'],'heldout_tasks':135,'tasks_with_valid_pool':nonempty,
            'tasks_with_more_than_budget_valid_samples':eligible,'tasks_with_more_than_budget_distinct_plans':unique_four,
            'all_five_draw_pool_oracle_macro_survival':rate,'method_macro_survival':method_rates,'scenarios':rows})
    dest=OUT/'family_utility_floor_diagnostic_v1.json';assert not dest.exists()
    dest.write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'models':report,
        'boundary':'Oracle uses only the original five-draw pool. A floor may reflect missing alternatives or unavailable mandatory skills; it is not a proof that perturbed tasks are globally unsolvable. No new samples, tuning, or selection changes.'},indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='scenarios'} for r in report],indent=2))

if __name__=='__main__':main()
