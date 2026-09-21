"""Score corrected outputs under frozen reference-count and dependency variants."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import hashlib,json,random
from planspace.partial_order import matches_partial_order

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919'

def main():
    construction=OUT/'family_construction_v1.json'
    graph=json.loads(construction.read_text());tasks={t['task']:t for t in graph['tasks']}
    inputs=json.loads((OUT/'fireplace_repair_verification.json').read_text())['models']
    allrows=[];models=[]
    for item in inputs:
        path=ROOT/item['corrected_artifact'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        data=json.loads(path.read_text());count=Counter();variants=Counter()
        for task in data['tasks']:
            refs=tasks[task['activity']]['references']
            selections={}
            for seed in (7,19,41):
                order=list(range(len(refs)));random.Random(seed).shuffle(order)
                for k in (1,3,5):selections[f'k{k}_seed{seed}']=set(order[:k])
            plans=[[SimpleNamespace(action_id=a) for a in r['action_ids']] for r in refs]
            for sample in task['samples']:
                parsed=sample['parse_error'] is None;ids=sample['parsed_plan'] or []
                con=[i for i,r in enumerate(refs) if parsed and matches_partial_order(ids,plans[i],frozenset(map(tuple,r['conservative_edges'])))]
                rel=[i for i,r in enumerate(refs) if parsed and matches_partial_order(ids,plans[i],frozenset(map(tuple,r['relaxed_edges'])))]
                multi=parsed and any(Counter(ids)==Counter(r['action_ids']) for r in refs)
                valid=bool((sample.get('execution') or {}).get('valid'))
                assert bool(con)==sample['partial_order_match'],(task['activity'],item['model'])
                assert not con or rel
                assert not rel or valid,(task['activity'],item['model'],'relaxed invalid')
                row={'model':item['model'],'task':task['activity'],'sample_index':sample['sample_index'],
                     'valid':valid,'exact':sample['exact_match'],'multiset':multi,'conservative_family':bool(con),
                     'relaxed_family':bool(rel),'conservative_indices':con,'relaxed_indices':rel}
                for key in ['valid','exact','multiset','conservative_family','relaxed_family']:count[key]+=int(row[key])
                count['valid_same_multiset_outside_conservative']+=int(valid and multi and not con)
                count['valid_same_multiset_outside_relaxed']+=int(valid and multi and not rel)
                count['valid_different_multiset']+=int(valid and not multi)
                count['invalid_multiset']+=int(multi and not valid)
                row['reference_selection']={name:{'conservative':bool(set(con)&selected),'relaxed':bool(set(rel)&selected)} for name,selected in selections.items()}
                for name,scores in row['reference_selection'].items():
                    for variant,v in scores.items():variants[name+'_'+variant]+=int(v)
                allrows.append(row)
        models.append({'model':item['model'],'n':855,'counts':dict(count),'reference_selection_counts':dict(variants)})
    report={'config':{'reference_counts':[1,3,5],'selection_seeds':[7,19,41],'natural_output_count':5130,
                       'construction_sha256':hashlib.sha256(construction.read_bytes()).hexdigest(),
                       'boundary':'Conservative/relaxed coverage is diagnostic, never a replacement for goal replay. Bounded relaxation retains unproven edges.'},
            'models':models,'rows':allrows}
    target=OUT/'family_sensitivity_v1.json';assert not target.exists()
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{'model':m['model'],**m['counts']} for m in models],indent=2))

if __name__=='__main__':main()
