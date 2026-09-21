"""Replay frozen public plans with PLANSPACE STRIPS and independent VAL.

Archival scoring fields are retained for disagreement analysis. No model calls.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,time
import yaml
from planspace.core import execute_plan
from planspace.partial_order import dependency_edges,matches_partial_order
from planspace.strips_adapter import StripsAdapter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919'
REPO=ROOT/'external/LLMs-Planning-review-20260919'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def parse_plan(raw,aliases):
    if raw is None:return None
    if isinstance(raw,list):lines=raw
    elif isinstance(raw,str):lines=[x.strip() for x in raw.splitlines() if x.strip()]
    else:raise ValueError('Unknown plan representation')
    result=[]
    for line in lines:
        if not re.fullmatch(r'\([^()]+\)',line.strip()):raise ValueError('Non-action line in extracted plan')
        tokens=line.strip()[1:-1].lower().split()
        result.append('('+' '.join([tokens[0]]+[aliases.get(x,x) for x in tokens[1:]])+')')
    return result

def main():
    freeze=json.loads((OUT/'external_archive_freeze.json').read_text())
    for item in freeze['source_files']:assert digest(ROOT/item['path'])==item['sha256']
    binary=REPO/'planner_tools/VAL/validate';rows=[];domains={}
    run=OUT/'external_val_run_v1';run.mkdir(exist_ok=False)
    for dom in ('blocksworld','logistics'):
        root=REPO/'llm_planning_analysis'
        direct=json.loads((root/'results'/dom/'gpt-4_chat/task_1_plan_generation.json').read_text())
        feedback=json.loads((root/'results'/dom/'gpt-4_chat/task_1_plan_generation_backprompting.json').read_text())
        cfg_path=root/'configs'/f'{dom}.yaml';cfg=yaml.safe_load(cfg_path.read_text())
        aliases={v:k for k,v in cfg.get('encoded_objects_compact',{}).items()}
        domains[dom]={'config_sha256':digest(cfg_path),'alias_mapping':aliases}
        a={r['instance_id']:r for r in direct['instances']};b={r['instance_id']:r for r in feedback['instances']}
        domain_file=root/'instances'/dom/'generated_domain.pddl'
        for task in [r for r in freeze['task_rows'] if r['domain']==dom]:
            task_id=task['instance_id'];problem_file=ROOT/task['problem']
            assert digest(problem_file)==task['problem_sha256']
            adapter=StripsAdapter.parse(domain_file.read_text(),problem_file.read_text())
            ref=parse_plan(a[task_id]['ground_truth_plan'],{})
            reference=[adapter.action(x) for x in ref]
            reference_valid=execute_plan(adapter.problem,reference).valid
            edges=dependency_edges(reference)
            for setting,record in [('direct',a[task_id])]+([('feedback',b[task_id])] if task['in_e2_common'] else []):
                raw=record.get('extracted_llm_plan');error=None
                try:plan=parse_plan(raw,aliases if setting=='feedback' else {})
                except ValueError as e:plan=None;error=str(e)
                result=None
                try:
                    if plan is not None:result=execute_plan(adapter.problem,[adapter.action(x) for x in plan])
                except ValueError as e:error=str(e)
                key=f'{dom}_{task_id}_{setting}'
                val_result=None;val_output='not run: no parseable extracted plan';seconds=None
                if plan is not None:
                    planfile=run/(key+'.plan');planfile.write_text('\n'.join(plan)+'\n')
                    start=time.perf_counter()
                    try:
                        proc=subprocess.run([str(binary),'-v',str(domain_file),str(problem_file),str(planfile)],capture_output=True,text=True,timeout=10)
                        val_output=proc.stdout+proc.stderr
                        if 'Plan valid' in val_output:val_result=True
                        elif 'Plan invalid' in val_output or 'Plan failed to execute' in val_output:val_result=False
                        else:raise RuntimeError(f'Unclassified VAL output {key}: {val_output}')
                    except subprocess.TimeoutExpired:val_output='TIMEOUT';val_result=None
                    seconds=time.perf_counter()-start
                (run/(key+'.val.txt')).write_text(val_output)
                goal=bool(result and result.valid)
                rows.append({'domain':dom,'instance_id':task_id,'setting':setting,
                    'in_e1':setting=='direct' and task['in_e1_direct_100'],'in_e2':task['in_e2_common'],
                    'official_correct':record.get('correct'),'adapter_goal':goal,'val_goal':val_result,
                    'parse_or_action_error':error,'plan_available':plan is not None,
                    'failure_step':result.failure_step if result else None,
                    'reference_valid':reference_valid,'exact':plan==ref,
                    'multiset':plan is not None and Counter(plan)==Counter(ref),
                    'family':plan is not None and matches_partial_order(plan,reference,edges),
                    'plan_length':len(plan) if plan is not None else None,'reference_length':len(ref),
                    'feedback_steps':record.get('steps'),'context_window_hit':record.get('context_window_hit'),
                    'source_statement_equal':task['same_task_statement'],
                    'val_elapsed_seconds':seconds,'plan':plan})
    summary={'rows':len(rows),'e1_rows':sum(r['in_e1'] for r in rows),'e2_rows':sum(r['in_e2'] for r in rows),
             'val_unavailable':sum(r['val_goal'] is None for r in rows),
             'val_adapter_disagreements':[r for r in rows if r['val_goal'] is not None and r['val_goal']!=r['adapter_goal']],
             'official_adapter_disagreements':[r for r in rows if r['official_correct']!=r['adapter_goal']],
             'invalid_references':sum(not r['reference_valid'] for r in rows)}
    report={'summary':summary,'provenance':{'external_freeze_sha256':digest(OUT/'external_archive_freeze.json'),
        'val_binary_sha256':digest(binary),'val_parser_sha256':digest(REPO/'planner_tools/VAL/src/pddl+.cpp'),
        'val_patch':'t_func_decl integer NULL assignment replaced by nullptr for Clang compatibility',
        'adapter_sha256':digest(ROOT/'src/planspace/strips_adapter.py'),'domain_aliases':domains},'rows':rows}
    (OUT/'external_replay_v1.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in summary.items()},indent=2))

if __name__=='__main__':main()
