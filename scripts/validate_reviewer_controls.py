"""Four predeclared mutations on 50 output-independent external task IDs."""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess
from planspace.strips_adapter import StripsAdapter
from planspace.core import execute_plan

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/reviewer_revision_20260919'

def main():
    freeze=json.loads((OUT/'external_archive_freeze.json').read_text());repo=ROOT/'external/LLMs-Planning-review-20260919'
    selected=sorted([r for r in freeze['task_rows'] if r['in_e1_direct_100']],key=lambda r:hashlib.sha256(f"{r['domain']}:{r['instance_id']}".encode()).hexdigest())[:50]
    folder=OUT/'external_controls_v1';folder.mkdir(exist_ok=False)
    (folder/'selected_tasks.json').write_text(json.dumps(selected,indent=2)+'\n');rows=[]
    for task in selected:
        dom=task['domain'];tid=task['instance_id'];root=repo/'llm_planning_analysis'
        archive=json.loads((root/'results'/dom/'gpt-4_chat/task_1_plan_generation.json').read_text())
        ref=next(r['ground_truth_plan'] for r in archive['instances'] if r['instance_id']==tid)
        domain=root/'instances'/dom/'generated_domain.pddl';problem=ROOT/task['problem']
        adapter=StripsAdapter.parse(domain.read_text(),problem.read_text());assert execute_plan(adapter.problem,[adapter.action(a) for a in ref]).valid
        words=ref[0][1:-1].split();words[-1]='nonexistent-object'
        variants={'illegal_parameter':['('+' '.join(words)+')']+ref[1:],
                  'precondition_probe':[ref[0]]+ref,'goal_deletion':ref[:-1],'repeat_final':ref+[ref[-1]]}
        for name,plan in variants.items():
            try:
                result=execute_plan(adapter.problem,[adapter.action(a) for a in plan]);valid=result.valid
                stage='valid' if valid else 'precondition' if not result.executable else 'goal_miss'
            except ValueError:valid=False;stage='invalid_action'
            p=folder/f'{dom}_{tid}_{name}.plan';p.write_text('\n'.join(plan)+'\n')
            proc=subprocess.run([str(repo/'planner_tools/VAL/validate'),'-v',str(domain),str(problem),str(p)],capture_output=True,text=True,timeout=10)
            text=proc.stdout+proc.stderr;p.with_suffix('.val.txt').write_text(text)
            if 'Plan valid' in text:val=True;valstage='valid'
            elif 'Plan invalid' in text or 'Plan failed to execute' in text:
                val=False;valstage='execution_or_goal_rejection'
            elif any(s in text for s in ['Bad plan','Type checking','type checking','Undefined','undeclared','Unknown','unknown']):
                val=False;valstage='invalid_action_or_type'
            else:val=None;valstage='unclassified'
            rows.append({'domain':dom,'task':tid,'mutation':name,'adapter':valid,'adapter_stage':stage,
                         'val':val,'val_stage':valstage,'returncode':proc.returncode})
    summary={'tasks':len(selected),'controls':len(rows),'adapter_stages':dict(Counter(r['adapter_stage'] for r in rows)),
             'unclassified':[r for r in rows if r['val'] is None],
             'disagreements':[r for r in rows if r['val'] is not None and r['val']!=r['adapter']]}
    (OUT/'external_controls_v1.json').write_text(json.dumps({'summary':summary,'rows':rows,
        'boundary':'Constructed verification probes, not naturally occurring error rates. Duplicate mutations are not assumed invalid; actual replay determines outcome.'},indent=2)+'\n')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in summary.items()},indent=2))

if __name__=='__main__':main()
