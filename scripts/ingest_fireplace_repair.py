"""Verify repair outputs and create a new mixed-runtime, task-consistent track."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan
from planspace.model_protocol import render_context_fit_model_prompt,prompt_sha256

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    returned=OUT/'fireplace_repair_return'
    assert json.loads((returned/'COMPLETED.json').read_text())['expected_samples']==30
    inputs=json.loads((OUT/'input_freeze.json').read_text())['inputs']
    config=json.loads((OUT/'fireplace_repair_bundle/configs/repair.json').read_text())
    source_root=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'
    records=[];target=OUT/'corrected_matrix_v1';target.mkdir(exist_ok=False)
    for model in config['models']:
        old_path=ROOT/'artifacts'/f"{model['slug']}_queue_171_enriched_v0_9_context171_six.json"
        assert digest(old_path)==next(e['sha256'] for e in inputs if e['path']==str(old_path.relative_to(ROOT)))
        new_path=returned/'results'/f"{model['slug']}_queue_1_sampling_reviewer_fireplace_repair.json"
        old=json.loads(old_path.read_text());new=json.loads(new_path.read_text())
        assert new['model_id']==old['model_id'] and new['model_revision']==old['model_revision']
        assert new['decoding']==old['decoding']
        assert len(new['tasks'])==1 and len(new['tasks'][0]['samples'])==5
        task=new['tasks'][0];prior=next(t for t in old['tasks'] if t['source_path']==task['source_path'])
        assert task['source_path']=='putting_wood_in_fireplace/problem0.bddl'
        source=source_root/task['source_path'];assert digest(source)==task['source_sha256']
        problem=generic_household_problem(parse_problem_file(source));actions={a.action_id:a for a in problem.actions}
        assert task['prompt_sha256']==prompt_sha256(render_context_fit_model_prompt(problem))
        assert task['prompt_sha256']!=prior['prompt_sha256']
        assert [s['seed'] for s in task['samples']]==[s['seed'] for s in prior['samples']]
        for sample in task['samples']:
            plan=sample['parsed_plan'];result=None
            if sample['parse_error'] is None:
                result=execute_plan(problem,[actions[a] for a in plan])
            assert bool(result and result.valid)==bool((sample.get('execution') or {}).get('valid'))
        combined=copy.deepcopy(old)
        combined['tasks']=[task if t['source_path']==task['source_path'] else t for t in old['tasks']]
        combined['evidence_status']='post_audit_task_consistent_mixed_runtime_repair'
        combined['repair_provenance']={'legacy_sha256':digest(old_path),'replacement_sha256':digest(new_path),
              'runtime_provenance_sha256':digest(returned/'runtime_provenance.json'),
              'boundary':'Only fireplace regenerated after goal correction; remaining 170 tasks retain historical outputs. Different runtime/hardware, same model revisions and seed policy.'}
        samples=[s for t in combined['tasks'] for s in t['samples']]
        for key,field in [('parse_success_rate','parse'),('executable_rate','executable'),('goal_valid_rate','valid'),('exact_match_rate','exact')]:
            count=sum(s['parse_error'] is None if field=='parse' else s['exact_match'] if field=='exact' else bool((s.get('execution') or {}).get(field)) for s in samples)
            combined['summary'][key]=count/len(samples)
        raw=target/(model['slug']+'_merged.json');raw.write_text(json.dumps(combined,indent=2)+'\n')
        enriched=target/(model['slug']+'_enriched.json')
        subprocess.run([sys.executable,str(ROOT/'scripts/enrich_partial_order_metrics.py'),str(raw),str(source_root),
            '--output',str(enriched),'--generic-domain-version',new['generic_domain_version']],check=True,cwd=ROOT)
        records.append({'model':model['model_id'],'repair_valid':sum(bool((s.get('execution') or {}).get('valid')) for s in task['samples']),
                        'n':5,'corrected_artifact':str(enriched.relative_to(ROOT)),'sha256':digest(enriched),
                        'old_prompt':prior['prompt_sha256'],'corrected_prompt':task['prompt_sha256']})
    (OUT/'fireplace_repair_verification.json').write_text(json.dumps({'models':records,'outputs':30,
        'archive_sha256':digest(OUT/'repair_results.tgz'),'boundary':'Task-consistent corrected track; not a hardware-controlled rerun.'},indent=2)+'\n')
    print(json.dumps(records,indent=2))

if __name__=='__main__':main()
