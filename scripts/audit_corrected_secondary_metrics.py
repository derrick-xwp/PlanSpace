"""Check whether the task-consistent repair changes manuscript scoring inputs."""
import hashlib
import json
from pathlib import Path
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan
from planspace.model_protocol import parse_model_plan_action_prefix_sensitivity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/reviewer_revision_20260919'

def main():
    rows = []
    for item in json.loads((OUT/'fireplace_repair_verification.json').read_text())['models']:
        path = ROOT/item['corrected_artifact']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        slug = path.stem.removesuffix('_enriched')
        new = json.loads(path.read_text())
        old = json.loads((ROOT/f'artifacts/{slug}_queue_171_enriched_v0_9_context171_six.json').read_text())
        prefix = json.loads((ROOT/f'artifacts/{slug}_action_prefix_sensitivity_v0_9_context171_six.json').read_text())
        prior_prefix = {t['source_path']:t for t in prefix['tasks']}
        diffs = []; prefix_diffs = []
        for before, after in zip(old['tasks'], new['tasks']):
            assert before['source_path'] == after['source_path']
            if before['activity'] != 'putting_wood_in_fireplace-0':
                assert before['samples'] == after['samples']
            problem = generic_household_problem(parse_problem_file(ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/after['source_path']))
            actions = {a.action_id:a for a in problem.actions}
            for a,b,p in zip(before['samples'], after['samples'], prior_prefix[after['source_path']]['samples']):
                fields = ['exact_match','partial_order_match','normalized_cost_regret','matched_reference_family_indices']
                for key in fields:
                    if a[key] != b[key]: diffs.append([after['activity'],b['sample_index'],key,a[key],b[key]])
                for key in ['valid','executable','goal_satisfied']:
                    if bool((a.get('execution') or {}).get(key)) != bool((b.get('execution') or {}).get(key)):
                        diffs.append([after['activity'],b['sample_index'],key])
                try:
                    plan = parse_model_plan_action_prefix_sensitivity(b['raw_output'],set(actions))
                    result = execute_plan(problem,[actions[x] for x in plan])
                    score = (True,result.valid,tuple(plan)==tuple(after['reference_plan']))
                except Exception:
                    score = (False,False,False)
                previous = tuple(p[k] for k in ['normalized_parse_success','normalized_goal_valid','normalized_exact_match'])
                if score != previous: prefix_diffs.append([after['activity'],b['sample_index'],list(previous),list(score)])
        rows.append({'model':item['model'],'scoring_field_differences':diffs,'prefix_scoring_differences':prefix_diffs,
                     'corrected_sha256':item['sha256'],
                     'generation_seconds_recomputed':sum(s['elapsed_seconds'] for t in new['tasks'] for s in t['samples']),
                     'legacy_generation_seconds_in_summary':new['summary']['generation_seconds_total']})
    dest=OUT/'corrected_secondary_metric_audit_v1.json'
    assert not dest.exists()
    dest.write_text(json.dumps({'models':rows,'boundary':'Scoring equality does not establish equal runtime. Cost is symbolic action count, not GPU time.'},indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__ == '__main__': main()
