"""Task-paired descriptive uncertainty; no causal claim from selected archives."""
from pathlib import Path
import hashlib,json,random

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/reviewer_revision_20260919'

def interval(values,seed):
    rng=random.Random(seed);n=len(values)
    reps=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [reps[249],reps[9749]]

def analyze(rows,exclude_polluted=False):
    result=[]
    for domain in ['blocksworld','logistics']:
        for setting in ['direct','feedback']:
            subset=[r for r in rows if r['in_e2'] and r['domain']==domain and r['setting']==setting
                    and not(exclude_polluted and domain=='blocksworld' and r['instance_id']==12)]
            n=len(subset)
            rates={key:sum(r[key] for r in subset)/n for key in ['adapter_goal','exact','family','multiset']}
            gap=[int(r['adapter_goal'])-int(r['exact']) for r in subset]
            result.append({'domain':domain,'setting':setting,'n':n,'rates':rates,
                 'goal_minus_exact_ci95':interval(gap,20260919),
                 'goal_outside_family':sum(r['adapter_goal'] and not r['family'] for r in subset),
                 'goal_same_multiset_outside_family':sum(r['adapter_goal'] and r['multiset'] and not r['family'] for r in subset),
                 'observed_feedback_steps':sorted({r['feedback_steps'] for r in subset if r['feedback_steps'] is not None})})
    return result

def main():
    source=OUT/'external_replay_v1.json';data=json.loads(source.read_text());rows=data['rows']
    assert data['summary']['val_adapter_disagreements']==[]
    assert data['summary']['official_adapter_disagreements']==[]
    report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'all_selected':analyze(rows),'exclude_blocksworld12':analyze(rows,True),
      'bootstrap':{'unit':'task within domain and setting, paired metrics','trials':10000,'seed':20260919,
                   'interpretation':'descriptive conditional intervals, not preregistered population inference'},
      'source_publication':'https://papers.nips.cc/paper_files/paper/2023/file/efb2072a358cefb75886a315a6fcf880-Paper-Conference.pdf',
      'source_section':'5.2, Table 4',
      'boundaries':['Original feedback cohort was selected from 50 failed one-shot tasks per domain with at most 15 rounds.',
        'Feedback counts reproduce the published 41/50 Blocksworld and 35/50 Logistics.',
        'Current same-ID direct archive includes 11 successful Logistics plans; it is not established as the initial responses that selected the historical feedback cohort.',
        'No causal repair-gain estimate or full-benchmark ranking is supported by this cross-run pairing.',
        'Exact and family are new counterfactual diagnostics; official goal-replay conclusions are reproduced, not overturned.',
        'Blocksworld 12 direct query includes appended responses; exclusions are sensitivity analysis, not silent cleaning.',
        'Intervals describe frozen selected tasks only; no confirmatory p-values or significance claims are made.']}
    dest=OUT/'external_statistics_v1.json';assert not dest.exists()
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['all_selected'],indent=2))

if __name__=='__main__':main()
