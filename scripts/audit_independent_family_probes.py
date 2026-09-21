"""Replay archived search examples against frozen corrected family graphs."""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import hashlib,json
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan
from planspace.partial_order import matches_partial_order

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/reviewer_revision_20260919'

def main():
    src=ROOT/'artifacts/independent_state_search_v0_1.json'
    archive=json.loads(src.read_text())
    graphfile=OUT/'family_construction_v1.json'
    graphs={t['source_path']:t for t in json.loads(graphfile.read_text())['tasks']}
    matrix=json.loads((OUT/'corrected_matrix_v1/qwen3_4b_enriched.json').read_text())
    selected={t['source_path']:t['reference_plan'] for t in matrix['tasks']}
    rows=[];counts=Counter()
    for task in archive['tasks']:
        path=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/task['source_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==task['source_sha256']
        problem=generic_household_problem(parse_problem_file(path));actions={a.action_id:a for a in problem.actions}
        refs=graphs[task['source_path']]['references']
        for index,plan in enumerate(task['nonreference_examples']):
            valid=execute_plan(problem,[actions[a] for a in plan]).valid
            scores={'valid':valid,'exact_current':plan==selected[task['source_path']],
                    'multiset':any(Counter(plan)==Counter(r['action_ids']) for r in refs)}
            for v in ['conservative','relaxed']:
                scores[v]=any(matches_partial_order(plan,[SimpleNamespace(action_id=a) for a in r['action_ids']],frozenset(map(tuple,r[v+'_edges']))) for r in refs)
            assert valid,(task['source_path'],index)
            assert not scores['conservative'] or scores['relaxed']
            row={'task':task['source_path'],'archived_example_index':index,'plan':plan,**scores}
            rows.append(row)
            counts['examples']+=1
            for k,v in scores.items():counts[k]+=int(v)
            counts['same_multiset_outside_conservative']+=int(scores['multiset'] and not scores['conservative'])
            counts['same_multiset_outside_relaxed']+=int(scores['multiset'] and not scores['relaxed'])
    assert len(rows)==591
    result={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
      'construction_sha256':hashlib.sha256(graphfile.read_bytes()).hexdigest(),
      'summary':dict(counts),'tasks_with_examples':len({r['task'] for r in rows}),
      'boundary':'The existing search archive retains only the first at most five nonreference examples per task, 591 examples total, not all 1939 discovered nonreference plans. Examples are search-generated without references, but this retained subset is postselected relative to the historical reference. Current exact labels are recomputed against the corrected track. These are construction-external probes sharing symbolic semantics, not natural-output prevalence or external semantic validation.',
      'rows':rows}
    out=OUT/'independent_family_probes_v1.json';assert not out.exists()
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
