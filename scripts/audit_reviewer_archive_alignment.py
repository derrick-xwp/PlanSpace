"""Freeze task-aligned external archives without selecting on outcomes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def statement(text):
    return ' '.join(text.split('[STATEMENT]')[-1].split())


def main():
    repo = ROOT / 'external/LLMs-Planning-review-20260919/llm_planning_analysis'
    rows, sources, summary = [], [], []
    for domain in ('blocksworld', 'logistics'):
        paths = [repo / 'results' / domain / 'gpt-4_chat' / ('task_1_plan_generation'+suffix+'.json')
                 for suffix in ('', '_backprompting')]
        direct, feedback = [json.loads(p.read_text()) for p in paths]
        for p in paths:
            sources.append({'path': str(p.relative_to(ROOT)), 'sha256': digest(p)})
        a = {r['instance_id']: r for r in direct['instances']}
        b = {r['instance_id']: r for r in feedback['instances']}
        assert len(a) == len(direct['instances']) and len(b) == len(feedback['instances'])
        common = sorted(a.keys() & b.keys())
        # E1 direct sample fixed by ID, independent of model score; E2 uses all paired archives.
        selected = sorted(a)[:100]
        mismatches = []
        for task_id in sorted(set(selected) | set(common)):
            problem = repo / 'instances' / domain / 'generated_basic' / f'instance-{task_id}.pddl'
            assert problem.is_file(), problem
            initial_message = b[task_id]['messages'][1]['content'] if task_id in b else None
            aligned = statement(a[task_id]['query']) == statement(initial_message) if initial_message else None
            if aligned is False:
                mismatches.append(task_id)
            rows.append({'domain':domain,'instance_id':task_id,
                         'problem':str(problem.relative_to(ROOT)),'problem_sha256':digest(problem),
                         'in_e1_direct_100':task_id in selected,'in_e2_common':task_id in common,
                         'same_task_statement':aligned,
                         'direct_prompt_sha256':hashlib.sha256(a[task_id]['query'].encode()).hexdigest(),
                         'feedback_initial_prompt_sha256':hashlib.sha256(initial_message.encode()).hexdigest() if initial_message else None})
        summary.append({'domain':domain,'direct_count':len(a),'feedback_count':len(b),
                        'common_count':len(common),'statement_mismatches':mismatches,
                        'e1_direct_ids':selected,'e2_paired_ids':common,
                        'engine':direct['engine'],'prompt_type':[direct['prompt_type'],feedback['prompt_type']]})
    data={'source_files':sources,'domains':summary,'task_rows':rows,
          'selection':'E1 lowest 100 direct IDs per domain; E2 every shared ID; no score-based selection',
          'boundary':'Task-statement equality is verified, not full prompt/budget/checkpoint equality. gpt-4_chat is an archive label, not a pinned API revision. E2 has 100 paired tasks, not the target 200.'}
    dest=ROOT/'artifacts/reviewer_revision_20260919/external_archive_freeze.json'
    payload=json.dumps(data,indent=2)+'\n'
    if dest.exists() and dest.read_text()!=payload:
        raise RuntimeError('Frozen archive alignment differs; write a new version explicitly')
    dest.write_text(payload)
    print(json.dumps({'domains':[{k:v for k,v in r.items() if not k.endswith('_ids')} for r in summary], 'boundary':data['boundary']},indent=2))


if __name__=='__main__':
    main()
