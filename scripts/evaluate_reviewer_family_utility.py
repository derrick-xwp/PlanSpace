"""Frozen equal-budget plan selection under symbolic skill availability changes."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,hashlib,json,random
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/reviewer_revision_20260919'

def choose(samples,groups,seed,budget):
    order=list(samples);random.Random(seed).shuffle(order)
    if groups is None:return order[:budget]
    selected=[];seen=set()
    for i in order:
        if groups[i] not in seen:
            selected.append(i);seen.add(groups[i])
            if len(selected)==budget:return selected
    return (selected+[i for i in order if i not in selected])[:budget]

def scenarios(task,actions):
    types={name:{} for name in ['transfer','destination','open','toggle']}
    for a in actions:
        if a.operator=='TRANSFER':
            types['transfer'][a.action_id]={a.action_id}
            types['destination'].setdefault(a.args[-1],set()).add(a.action_id)
        if a.operator=='OPEN':types['open'][a.action_id]={a.action_id}
        if a.operator in {'TOGGLE_ON','TOGGLE_OFF'}:types['toggle'][a.action_id]={a.action_id}
    result={}
    for name,options in types.items():
        if not options:result[name]=None;continue
        key=min(options,key=lambda x:hashlib.sha256((task+'|'+name+'|'+x).encode()).hexdigest())
        result[name]=options[key]
    return result

def ci(values):
    if not values:return None
    rng=random.Random(20260919);n=len(values)
    draws=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [draws[249],draws[9749]]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--split',choices=['development','heldout'],required=True);args=ap.parse_args()
    cfgpath=ROOT/'configs/reviewer_family_utility_v1.json';cfg=json.loads(cfgpath.read_text());cfgsha=hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    if args.split=='heldout':
        dev=json.loads((OUT/'family_utility_development_v1.json').read_text())
        assert dev['config_sha256']==cfgsha and dev['sanity_checks_passed']
    selected_tasks=set(json.loads((ROOT/cfg['source_split']).read_text())[args.split+'_tasks'])
    sensitivity=json.loads((OUT/'family_sensitivity_v1.json').read_text())
    labels={(r['model'],r['task'],r['sample_index']):r for r in sensitivity['rows']}
    inputs=json.loads((ROOT/cfg['source_matrix']).read_text())['models']
    rows=[];coverage={};cache={}
    for entry in inputs:
        path=ROOT/entry['corrected_artifact'];assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        data=json.loads(path.read_text())
        for t in data['tasks']:
            task=t['activity']
            if task not in selected_tasks:continue
            if task not in cache:
                src=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/t['source_path']
                assert hashlib.sha256(src.read_bytes()).hexdigest()==t['source_sha256']
                problem=generic_household_problem(parse_problem_file(src))
                cache[task]=(problem,scenarios(task,problem.actions))
            problem,perturbations=cache[task];actions={a.action_id:a for a in problem.actions}
            coverage[task]={k:sorted(v) if v is not None else None for k,v in perturbations.items()}
            samples={s['sample_index']:s for s in t['samples'] if bool((s.get('execution') or {}).get('valid'))}
            for s in samples.values():assert execute_plan(problem,[actions[a] for a in s['parsed_plan']]).valid
            grouping={'random':None,
                'exact_diversity':{i:tuple(s['parsed_plan']) for i,s in samples.items()},
                'action_multiset_diversity':{i:tuple(sorted(Counter(s['parsed_plan']).items())) for i,s in samples.items()},
                'known_relaxed_family_diversity':{i:tuple(labels[(entry['model'],task,i)]['relaxed_indices']) for i in samples}}
            for seed in cfg['selection_seeds']:
                for method,groups in grouping.items():
                    chosen=choose(samples,groups,seed,cfg['selection_budget'])
                    assert len(chosen)==min(len(samples),3) and len(set(chosen))==len(chosen)
                    plans=[samples[i]['parsed_plan'] for i in chosen]
                    for kind,blocked in perturbations.items():
                        if blocked is None:continue
                        survived=[p for p in plans if not(set(p)&blocked)]
                        rows.append({'model':entry['model'],'task':task,'seed':seed,'method':method,'scenario':kind,
                            'selected_indices':chosen,'candidate_count':len(samples),'success':bool(survived),
                            'distinct_survivors':len({tuple(p) for p in survived}),
                            'mean_selected_action_count':sum(map(len,plans))/len(plans) if plans else None})
    summaries=[]
    for entry in inputs:
        for method in cfg['methods']:
            modelrows=[r for r in rows if r['model']==entry['model'] and r['method']==method]
            per_task=defaultdict(list);baseline={}
            for r in rows:
                if r['model']==entry['model'] and r['method']=='random':baseline[(r['task'],r['seed'],r['scenario'])]=r['success']
            for r in modelrows:per_task[r['task']].append(int(r['success'])-int(baseline[(r['task'],r['seed'],r['scenario'])]))
            deltas=[sum(v)/len(v) for v in per_task.values()]
            # Equal weight per task; all model/seed/scenario records cluster within it.
            rates=defaultdict(list)
            for r in modelrows:rates[r['task']].append(int(r['success']))
            summaries.append({'model':entry['model'],'method':method,'applicable_tasks':len(rates),
                'task_macro_survival':sum(sum(v)/len(v) for v in rates.values())/len(rates),
                'delta_to_random':sum(deltas)/len(deltas),'delta_ci95':ci(deltas)})
    report={'config_sha256':cfgsha,'split':args.split,'task_count':len(selected_tasks),
            'sanity_checks_passed':True,'coverage':coverage,'summary':summaries,'rows':rows,
            'boundary':cfg['boundary']}
    dest=OUT/f'family_utility_{args.split}_v1.json';assert not dest.exists()
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'split':args.split,'tasks':len(selected_tasks),'rows':len(rows),'summary':summaries},indent=2))

if __name__=='__main__':main()
