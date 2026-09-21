"""Freeze revision inputs and recompute archived structural labels, not replay validity."""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import hashlib
import json
import subprocess

from planspace.partial_order import matches_partial_order

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/reviewer_revision_20260919'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    paths = sorted((ROOT / 'artifacts').glob('*_queue_171_enriched_v0_9_context171_six.json'))
    assert len(paths) == 6
    models, records, inputs = [], [], []
    shared = None
    for path in paths:
        data = json.loads(path.read_text())
        tasks = data['tasks']
        ids = {t['activity'] for t in tasks}
        assert len(tasks) == len(ids) == 171
        if shared is None:
            shared = ids
        assert ids == shared
        inputs.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path)})
        counts = Counter()
        for task in tasks:
            assert len(task['samples']) == 5
            dags = task['reference_plan_dags']
            for sample in task['samples']:
                candidate = sample['parsed_plan']
                parsed = candidate is not None and sample.get('parse_error') is None
                multiset = parsed and any(Counter(candidate) == Counter(d['action_ids']) for d in dags)
                family = parsed and any(matches_partial_order(candidate,
                    [SimpleNamespace(action_id=a) for a in d['action_ids']],
                    frozenset(map(tuple, d['partial_order_edges']))) for d in dags)
                exact = parsed and candidate == task['reference_plan']
                assert family == sample['partial_order_match'], (path, task['activity'])
                assert exact == sample['exact_match'], (path, task['activity'])
                valid = bool((sample.get('execution') or {}).get('valid'))
                row = {'model': data['model_id'], 'task': task['activity'],
                       'sample_index': sample['sample_index'], 'seed': sample['seed'],
                       'parsed': parsed, 'exact': exact, 'multiset': multiset,
                       'family': family, 'archived_goal_valid': valid}
                records.append(row)
                for key in ('parsed', 'exact', 'multiset', 'family', 'archived_goal_valid'):
                    counts[key] += int(row[key])
                counts['valid_outside_family'] += int(valid and not family)
                counts['multiset_not_family'] += int(multiset and not family)
                counts['family_not_valid'] += int(family and not valid)
                counts['valid_multiset_not_family'] += int(valid and multiset and not family)
        models.append({'model': data['model_id'], 'n': 855, 'counts': dict(counts)})
    external = ROOT / 'external/LLMs-Planning-review-20260919'
    commit = subprocess.check_output(['git', '-C', str(external), 'rev-parse', 'HEAD'], text=True).strip()
    manifest = {'status': 'execution_started', 'plan_sha256': digest(ROOT / 'docs/REVIEWER_EXPERIMENT_PLAN_20260919.md'),
                'inputs': inputs, 'external_repo': 'https://github.com/karthikv792/LLMs-Planning',
                'external_commit': commit, 'task_count': 171, 'output_count': len(records),
                'development_tasks': sorted(t for t in shared if int(hashlib.sha256(t.encode()).hexdigest(),16)%5==0),
                'heldout_tasks': sorted(t for t in shared if int(hashlib.sha256(t.encode()).hexdigest(),16)%5!=0),
                'split_rule': 'sha256(task_id) modulo 5 == 0 is development; freeze before designing perturbations',
                'boundary': 'Structural labels recomputed; goal validity reused from archive, not independently validated.'}
    outputs = {'input_freeze.json':manifest, 'e3a_structural_summary.json': {'models':models, 'boundary':manifest['boundary']},
               'e3a_structural_rows.json': records}
    for name, data in outputs.items():
        dest=OUT/name
        payload=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if dest.exists() and dest.read_text()!=payload:
            raise RuntimeError(f'Refusing to replace frozen revision artifact: {dest}')
        dest.write_text(payload)
    print(json.dumps({'models':models,'development':len(manifest['development_tasks']),
                      'heldout':len(manifest['heldout_tasks']),'external_commit':commit},indent=2))


if __name__ == '__main__':
    main()
