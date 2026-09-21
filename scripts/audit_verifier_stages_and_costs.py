"""Audit earliest failure positions and separately measure verifier resources."""
from pathlib import Path
import hashlib, json, platform, re, subprocess, time
from planspace.core import execute_plan
from planspace.strips_adapter import StripsAdapter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919'
REPO=ROOT/'external/LLMs-Planning-review-20260919'

def val_step(text):
    match=re.search(r'Checking next happening \(time (\d+)\)\s*Plan failed because of unsatisfied precondition',text)
    return int(match[1])-1 if match else None

def stats(values):
    x=sorted(values)
    def quantile(q):
        p=(len(x)-1)*q; i=int(p)
        return x[i]+(x[min(i+1,len(x)-1)]-x[i])*(p-i)
    return {'n':len(x),'p50':quantile(.5),'p95':quantile(.95),'max':max(x),'sum':sum(x)}

def main():
    external=json.loads((OUT/'external_replay_v1.json').read_text())
    local=json.loads((OUT/'local_static_val_v1.json').read_text())
    models=json.loads((OUT/'fireplace_repair_verification.json').read_text())['models']
    lookup={}
    for item in models:
        path=ROOT/item['corrected_artifact'];data=json.loads(path.read_text())
        for task in data['tasks']:
            for sample in task['samples']:
                lookup[(item['model'],task['activity'],sample['sample_index'])]=(path.stem,sample)
    rows=[]
    for r in external['rows']:
        log=OUT/'external_val_run_v1'/f"{r['domain']}_{r['instance_id']}_{r['setting']}.val.txt"
        rows.append({'track':'external','task':str(r['instance_id']),'model':r['setting'],
                     'local_step':r['failure_step'],'val_step':val_step(log.read_text())})
    for r in local['rows']:
        if r['status']!='validated': continue
        stem,sample=lookup[(r['model'],r['task'],r['sample'])]
        log=OUT/'local_static_val_v1'/r['task']/f"{stem}_{r['sample']}.val.txt"
        rows.append({'track':'local','task':r['task'],'model':r['model'],'sample':r['sample'],
                     'local_step':sample['execution']['failure_step'],'val_step':val_step(log.read_text())})
    disagreements=[r for r in rows if r['local_step']!=r['val_step']]
    freeze=json.loads((OUT/'external_archive_freeze.json').read_text())
    problems={(r['domain'],r['instance_id']):ROOT/r['problem'] for r in freeze['task_rows']}
    selected=sorted(external['rows'],key=lambda r:hashlib.sha256(f"{r['domain']}:{r['instance_id']}:{r['setting']}".encode()).hexdigest())[:50]
    resources=[]
    for r in selected:
        domain=REPO/'llm_planning_analysis/instances'/r['domain']/'generated_domain.pddl'
        problem=problems[r['domain'],r['instance_id']]
        adapter=StripsAdapter.parse(domain.read_text(),problem.read_text())
        actions=[adapter.action(a) for a in r['plan']]
        start=time.perf_counter()
        for _ in range(100):result=execute_plan(adapter.problem,actions)
        duration=(time.perf_counter()-start)/100
        assert result.valid==r['val_goal']
        plan=OUT/'external_val_run_v1'/f"{r['domain']}_{r['instance_id']}_{r['setting']}.plan"
        proc=subprocess.run(['/usr/bin/time','-l',str(REPO/'planner_tools/VAL/validate'),'-v',str(domain),str(problem),str(plan)],capture_output=True,text=True,timeout=10)
        rss=re.search(r'(\d+)\s+maximum resident set size',proc.stderr)
        cpu=re.search(r'([\d.]+)\s+real\s+([\d.]+)\s+user\s+([\d.]+)\s+sys',proc.stderr)
        assert rss and cpu,proc.stderr
        assert ('Plan valid' in proc.stdout)==r['val_goal']
        resources.append({'domain':r['domain'],'task':r['instance_id'],'setting':r['setting'],
            'adapter_replay_seconds_mean_100':duration,'val_peak_rss_bytes':int(rss[1]),
            'val_user_cpu_seconds':float(cpu[2]),'val_system_cpu_seconds':float(cpu[3]),
            'val_real_seconds_rounded':float(cpu[1])})
    report={'host':platform.platform(),'machine':platform.machine(),
        'first_failure':{'checked_plans':len(rows),'precondition_failures':sum(r['local_step'] is not None for r in rows),
                         'disagreements':disagreements,'rows':rows},
        'historical_val_wall_seconds':{'external':stats([r['val_elapsed_seconds'] for r in external['rows']]),
                                      'local':stats([r['seconds'] for r in local['rows'] if r['status']=='validated'])},
        'remeasurement':{'sample_count':50,'val_peak_rss_bytes':stats([r['val_peak_rss_bytes'] for r in resources]),
             'adapter_replay_seconds':stats([r['adapter_replay_seconds_mean_100'] for r in resources]),'rows':resources},
        'boundary':'Archive wall timers include subprocess overhead; separate 50-output resource audit uses macOS time -l (RSS bytes). Replay microtimings exclude parsing/grounding; rounded CPU times do not imply zero CPU cost. Neither RSS nor runtime is a cross-model generation comparison.'}
    dest=OUT/'verifier_stages_costs_v1.json';assert not dest.exists()
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['first_failure','remeasurement']},indent=2))
    print('failure positions',len(rows),'disagreements',len(disagreements),'precondition',report['first_failure']['precondition_failures'])
    print('RSS',report['remeasurement']['val_peak_rss_bytes'])

if __name__=='__main__':main()
