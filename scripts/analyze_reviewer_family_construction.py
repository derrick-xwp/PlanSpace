"""Output-blind reference reconstruction and exhaustively gated DAG relaxation.

No edge is removed on the strength of sampled orders. Resource bounds retain
the conservative graph and are reported, not interpreted as completeness.
"""
from pathlib import Path
from collections import Counter
from itertools import islice
import hashlib,json,random,time
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem,construct_goal_plan
from planspace.core import execute_plan,action_ids
from planspace.partial_order import dependency_edges,topological_orders,matches_partial_order

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919'
MAX_ORDERS=2000
TASK_SECONDS=20

def relax(problem,plan,edges,deadline):
    edges=set(edges);attempts=[]
    for edge in sorted(edges):
        if time.monotonic()>deadline:
            attempts.append({'edge':edge,'status':'task_time_bound'});break
        candidate=frozenset(edges-{edge})
        orders=list(topological_orders(len(plan),candidate,limit=MAX_ORDERS+1))
        if len(orders)>MAX_ORDERS:
            attempts.append({'edge':edge,'status':'order_bound','checked':0});continue
        valid=True;checked=0
        for order in orders:
            if time.monotonic()>deadline:
                valid=False;break
            checked+=1
            if not execute_plan(problem,[plan[i] for i in order]).valid:
                valid=False;break
        accepted=valid and checked==len(orders)
        if accepted:edges.remove(edge)
        attempts.append({'edge':edge,'status':'removed_exhaustively_valid' if accepted else
                         ('task_time_bound' if checked<len(orders) and time.monotonic()>deadline else 'invalid_order'),
                         'checked':checked,'orders':len(orders)})
    return frozenset(edges),attempts

def main():
    out=OUT/'family_construction_v1.json'
    assert not out.exists()
    base=json.loads((ROOT/'artifacts/qwen3_4b_queue_171_enriched_v0_9_context171_six.json').read_text())
    tasks=[]
    for task in base['tasks']:
        path=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/task['source_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==task['source_sha256']
        problem=generic_household_problem(parse_problem_file(path));unique={}
        for goal in problem.goal_alternatives:
            plan=construct_goal_plan(problem,goal)
            assert execute_plan(problem,plan).valid
            unique.setdefault(tuple(action_ids(plan)),plan)
        start=time.monotonic();deadline=start+TASK_SECONDS;refs=[]
        for ids,plan in sorted(unique.items()):
            edges=dependency_edges(plan)
            relaxed,attempts=relax(problem,plan,edges,deadline)
            refs.append({'action_ids':ids,'conservative_edges':sorted(edges),'relaxed_edges':sorted(relaxed),
                         'attempts':attempts})
        tasks.append({'task':task['activity'],'source_path':task['source_path'],
                      'source_sha256':task['source_sha256'],'references':refs,'seconds':time.monotonic()-start})
        print(task['activity'],len(refs),sum(len(r['conservative_edges'])-len(r['relaxed_edges']) for r in refs),flush=True)
    data={'config':{'max_new_orders':MAX_ORDERS,'task_relax_seconds':TASK_SECONDS,
                    'selection':'lexicographically sorted unique constructed goal representatives; no model outputs used',
                    'edge_policy':'lexical greedy removal only after exhaustive replay of all newly admitted orders'},
          'tasks':tasks,'summary':{'tasks':len(tasks),'references':sum(len(t['references']) for t in tasks),
                    'edges_removed':sum(len(r['conservative_edges'])-len(r['relaxed_edges']) for t in tasks for r in t['references'])}}
    out.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data['summary']))

if __name__=='__main__':main()
