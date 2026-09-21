"""Recompute central revision claims from frozen plans, without model calls."""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import hashlib,json,re
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan
from planspace.partial_order import matches_partial_order
from planspace.strips_adapter import StripsAdapter

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/reviewer_revision_20260919'

def main():
    optional=ROOT/'REVIEWER_BUNDLE_MANIFEST.json'
    if optional.exists():
        for name,sha in json.loads(optional.read_text()).items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    graph={t['task']:t for t in json.loads((OUT/'family_construction_v1.json').read_text())['tasks']}
    rows=json.loads((OUT/'family_sensitivity_v1.json').read_text())
    expected={(r['model'],r['task'],r['sample_index']):r for r in rows['rows']}
    models=json.loads((OUT/'fireplace_repair_verification.json').read_text())['models']
    counts=Counter();cache={}
    for item in models:
        path=ROOT/item['corrected_artifact'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        matrix=json.loads(path.read_text());assert len(matrix['tasks'])==171
        for t in matrix['tasks']:
            if t['activity'] not in cache:
                src=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/t['source_path']
                assert hashlib.sha256(src.read_bytes()).hexdigest()==t['source_sha256']
                p=generic_household_problem(parse_problem_file(src));cache[t['activity']]=(p,{a.action_id:a for a in p.actions})
            problem,actions=cache[t['activity']]
            refs=graph[t['activity']]['references']
            for s in t['samples']:
                parsed=s['parse_error'] is None; plan=s['parsed_plan'] or []
                valid=parsed and execute_plan(problem,[actions[a] for a in plan]).valid
                assert valid==bool((s.get('execution') or {}).get('valid'))
                scores={'valid':valid,'exact':parsed and plan==t['reference_plan']}
                scores['multiset']=parsed and any(Counter(plan)==Counter(r['action_ids']) for r in refs)
                for variant in ['conservative','relaxed']:
                    scores[variant+'_family']=parsed and any(matches_partial_order(plan,[SimpleNamespace(action_id=a) for a in r['action_ids']],frozenset(map(tuple,r[variant+'_edges']))) for r in refs)
                record=expected[item['model'],t['activity'],s['sample_index']]
                for key,value in scores.items():assert value==record[key],(item['model'],t['activity'],key)
                assert not scores['relaxed_family'] or valid
                counts['outputs']+=1;counts['valid']+=int(valid)
                counts['same_multiset_outside_conservative']+=int(valid and scores['multiset'] and not scores['conservative_family'])
                counts['same_multiset_outside_relaxed']+=int(valid and scores['multiset'] and not scores['relaxed_family'])
                counts['different_multiset_valid']+=int(valid and not scores['multiset'])
    assert dict(counts)=={'outputs':5130,'valid':3069,'same_multiset_outside_conservative':234,'same_multiset_outside_relaxed':117,'different_multiset_valid':125},counts
    freeze=json.loads((OUT/'external_archive_freeze.json').read_text())
    paths={(r['domain'],r['instance_id']):ROOT/r['problem'] for r in freeze['task_rows']}
    external=json.loads((OUT/'external_replay_v1.json').read_text())
    for r in external['rows']:
        domain=ROOT/'external/LLMs-Planning-review-20260919/llm_planning_analysis/instances'/r['domain']/'generated_domain.pddl'
        adapter=StripsAdapter.parse(domain.read_text(),paths[r['domain'],r['instance_id']].read_text())
        try:valid=execute_plan(adapter.problem,[adapter.action(a) for a in r['plan']]).valid
        except ValueError:valid=False
        assert valid==r['adapter_goal']==r['val_goal']==r['official_correct']
    stages=json.loads((OUT/'verifier_stages_costs_v1.json').read_text())['first_failure']
    assert len(stages['disagreements'])==2
    assert {(r['track'],r['task'],r['model']) for r in stages['disagreements']}=={('external','23','direct'),('external','29','direct')}
    utility=json.loads((OUT/'family_utility_floor_diagnostic_v1.json').read_text())
    assert all(m['tasks_with_more_than_budget_distinct_plans']==0 for m in utility['models'])
    assert all(abs(m['method_macro_survival']['exact_diversity']-m['all_five_draw_pool_oracle_macro_survival'])<1e-12 for m in utility['models'])
    probes=json.loads((OUT/'independent_family_probes_v1.json').read_text())
    assert probes['source_sha256']==hashlib.sha256((ROOT/'artifacts/independent_state_search_v0_1.json').read_bytes()).hexdigest()
    assert probes['construction_sha256']==hashlib.sha256((OUT/'family_construction_v1.json').read_bytes()).hexdigest()
    source_graph={t['source_path']:t for t in graph.values()}
    probe_counts=Counter()
    for r in probes['rows']:
        problem=generic_household_problem(parse_problem_file(ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/r['task']))
        actions={a.action_id:a for a in problem.actions}
        assert execute_plan(problem,[actions[a] for a in r['plan']]).valid
        probe_counts['valid']+=1
        for v in ['conservative','relaxed']:
            actual=any(matches_partial_order(r['plan'],[SimpleNamespace(action_id=a) for a in ref['action_ids']],frozenset(map(tuple,ref[v+'_edges']))) for ref in source_graph[r['task']]['references'])
            assert actual==r[v]
            probe_counts[v]+=int(actual)
    assert dict(probe_counts)=={'valid':591,'conservative':468,'relaxed':534}
    cap=json.loads((OUT/'cap_resource_recheck_v1.json').read_text())
    assert cap['caps']==[100,500,1000,2000]
    assert cap['summary']['unique_goal_plan_representative_count']==1403
    assert len(cap['representatives'])==1034
    assert len({r['source_path'] for r in cap['representatives']})==24
    assert all(c['checked']==c['valid'] and c['all_valid'] for r in cap['representatives'] for c in r['cap_results'])
    per_budget=OUT/'cap_resource_by_budget_v1'
    budgets=json.loads((per_budget/'summary.json').read_text())
    assert budgets['status']=='complete'
    assert [r['cap'] for r in budgets['rows']]==[100,500,1000,2000]
    for budget in budgets['rows']:
        path=per_budget/f"cap_{budget['cap']}.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest()==budget['report_sha256']
        report=json.loads(path.read_text())
        assert report['summary']['unique_goal_plan_representative_count']==1403
        assert len(report['representatives'])==1034
        entries=[r['cap_results'][0] for r in report['representatives']]
        assert all(r['cap']==budget['cap'] and r['all_valid'] and r['checked']==r['valid'] for r in entries)
        assert sum(r['checked'] for r in entries)==budget['checked_orders']==budget['valid_orders']
        assert budget['wall_seconds']>0 and budget['max_rss_bytes']>0
        raw=(per_budget/f"cap_{budget['cap']}.resources").read_text()
        timing=re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys',raw)
        rss=re.search(r'(\d+)\s+maximum resident set size',raw)
        assert timing and rss
        assert [float(timing[i]) for i in [1,2,3]]==[budget['wall_seconds'],budget['user_seconds'],budget['system_seconds']]
        assert int(rss[1])==budget['max_rss_bytes']
    print(json.dumps({'status':'PASS','recomputed':dict(counts),'external_outputs':len(external['rows']),
        'known_stage_priority_differences':2,'utility_floor_confirmed':True,
        'independent_search_probes_recomputed':dict(probe_counts),'cap_report_consistent':True,
        'separate_cap_budgets_verified':4},indent=2))

if __name__=='__main__':main()
