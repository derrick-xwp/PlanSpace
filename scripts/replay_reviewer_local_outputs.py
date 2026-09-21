"""Re-run frozen semantics on every parsed archived output; no model generation."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import time

from planspace.bddl_parser import parse_problem_file
from planspace.domain_registry import get_generic_domain

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source_root',type=Path)
    args=parser.parse_args()
    freeze=json.loads((ROOT/'artifacts/reviewer_revision_20260919/input_freeze.json').read_text())
    rows, mismatches, cache=[],[],{}
    for entry in freeze['inputs']:
        p=ROOT/entry['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
        data=json.loads(p.read_text());domain=get_generic_domain(data['generic_domain_version'])
        for task in data['tasks']:
            key=(data['generic_domain_version'],task['source_path'])
            if key not in cache:
                src=args.source_root/task['source_path']
                assert hashlib.sha256(src.read_bytes()).hexdigest()==task['source_sha256'],src
                problem=domain.generic_household_problem(parse_problem_file(src))
                cache[key]=(problem,{a.action_id:a for a in problem.actions})
            problem,actions=cache[key]
            for sample in task['samples']:
                plan=sample['parsed_plan']
                parsed=plan is not None and sample['parse_error'] is None
                unknown=[a for a in (plan or []) if a not in actions]
                start=time.perf_counter()
                result=domain.execute_plan(problem,[actions[a] for a in plan]) if parsed and not unknown else None
                valid=bool(result and result.valid)
                archived=bool((sample.get('execution') or {}).get('valid'))
                multiset=parsed and any(Counter(plan)==Counter(d['action_ids']) for d in task['reference_plan_dags'])
                row={'model':data['model_id'],'task':task['activity'],'sample_index':sample['sample_index'],
                     'parsed':parsed,'unknown_actions':unknown,'valid':valid,'archived_valid':archived,
                     'family':sample['partial_order_match'],'multiset':multiset,
                     'failure_step':result.failure_step if result else None,
                     'constraint_violations':list(result.constraint_violations) if result else [],
                     'elapsed_seconds':time.perf_counter()-start}
                rows.append(row)
                if valid!=archived:
                    mismatches.append(row)
        print(data['model_id'],len(rows),flush=True)
    summary={'outputs':len(rows),'tasks':len(cache),'validity_mismatches':len(mismatches),
             'family_validity_counterexamples':sum(r['family'] and not r['valid'] for r in rows),
             'valid_same_multiset_outside_family':sum(r['valid'] and r['multiset'] and not r['family'] for r in rows),
             'boundary':'Fresh replay of pinned local semantics, not external verification of semantics.',
             'source_code_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/planspace/core.py',ROOT/'src/planspace/generic_domain.py']}}
    out=ROOT/'artifacts/reviewer_revision_20260919/local_replay.json'
    if out.exists():
        raise RuntimeError('Do not overwrite existing replay; use explicit new version')
    out.write_text(json.dumps({'summary':summary,'mismatches':mismatches,'rows':rows},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
