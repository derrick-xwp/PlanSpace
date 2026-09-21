"""Verified, selected archived outputs illustrating family matching decisions."""
from pathlib import Path
import json,sys,hashlib,re
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan
from planspace.partial_order import dependency_edges,matches_partial_order
PAPER=ROOT/'paper'

def esc(s):return s.replace('_',r'\_').replace('&',r'\&')
def obj(s):return esc(re.sub(r'\.n\.\d+','',s).replace('_',' '))
def desc(a):
    p=a.split('::')
    if p[0]=='transfer':
        x,y=p[2].split('->');rx,x=x.split(':');ry,y=y.split(':')
        return obj(p[1])+': '+rx+' '+obj(x)+r' $\rightarrow$ '+ry+' '+obj(y)
    return p[0].replace('_',' ').title()+' '+obj(p[1])
def graph(ids,edges,mapping,red_edges=(),extra=()):
    rank=[0]*len(ids)
    for i in range(len(ids)):rank[i]=max([rank[u]+1 for u,v in edges if v==i]or[0])
    layers={k:[i for i,r in enumerate(rank) if r==k] for k in set(rank)}
    lines=[r'\begin{tikzpicture}[x=1cm,y=1cm]']
    for i,a in enumerate(ids):
        layer=layers[rank[i]]
        x=5*rank[i]/max(max(rank),1);y=.56*((len(layer)-1)/2-layer.index(i))
        style='psdag/extra' if a in extra else 'psdag/node'
        lines.append(r'\node['+style+'] (n%d) at (%.3f,%.3f) {$%s$};'%(i,x,y,mapping[a]))
    for u,v in edges:
        style='psdag/conflict' if (u,v) in red_edges else 'psdag/edge'
        lines.append(r'\draw['+style+'] (n%d)--(n%d);'%(u,v))
    return '\n'.join(lines+[r'\end{tikzpicture}'])

specs=[
 ('mistral_7b','Mistral-7B','packing_bags_or_suitcase-0',3,'dag:packing-match',
 'Reordering preserves family membership',
 r'The six packing actions can be reordered, while moving the backpack remains last. Sample 3 (one-based) reproduces the reference exactly; sample 4 instead starts with the two garments. Both satisfy the same reference DAG and reach the goal. This illustrates the gap between exact matching and family acceptance in Section~\ref{sec:results}.'),
 ('qwen3_14b','Qwen3-14B','clean_up_your_desk-0',0,'dag:desk-mismatch',
 'A conservative edge rejects a successful ordering',
 r'The reference requires moving the laptop ($a_8$) before closing it ($a_{10}$). The submitted sequence closes it first and then moves it; the red dashed edge shows the reversed dependency. Its action multiset is unchanged. Replay accepts this ordering under the frozen task semantics, but none of the recorded reference DAGs accepts it. Sample 2 moves the laptop before closing it and does match. This is a concrete same-multiset case from the family-sensitivity analysis, rather than a new action composition.'),
 ('qwen3_4b','Qwen3-4B','storing_food-0',3,'dag:food-extra',
 'An additional action changes the family membership',
 r'The candidate opens an additional cabinet ($b_1$), then executes the selected reference sequence. All nine reference actions are preserved. The additional occurrence prevents a match to any recorded family, while replay still reaches the goal. The raw cabinet symbol with a star denotes a distinct compiled object identifier; it is preserved in the legend. This illustrates a successful different-multiset output in the family-sensitivity analysis.')]
lines=[r'\clearpage\section{Matching and Non-matching DAG Cases}',r'\label{app:dag-matching-cases}',
 r'These selected archived model outputs connect the method to the score decomposition in Section~\ref{sec:results}. Nodes use the same rounded rectangles as Figure~\ref{fig:evaluation-example}. The same node label always denotes the same grounded action within a case. Red dashed arrows mark a reversed reference dependency; a red node marks an additional action. All other edges retain the conservative dependency rule.',
 r'Family acceptance compares the submitted action sequence with every known reference DAG, testing action identities and precedence. The candidate DAG visualizes the recorded order and its dependencies. The selected cases illustrate reordering, conservative-edge conflicts, and additional actions.']
records=[]
for ci,(model,name,task,si,label,title,explanation) in enumerate(specs,1):
    path=ROOT/f'artifacts/reviewer_revision_20260919/corrected_matrix_v1/{model}_enriched.json'
    data=json.loads(path.read_text());t=next(t for t in data['tasks'] if t['activity']==task);s=t['samples'][si]
    source=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/t['source_path']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==t['source_sha256']
    problem=generic_household_problem(parse_problem_file(source));lookup={a.action_id:a for a in problem.actions}
    ref=t['reference_plan'];cand=s['parsed_plan']
    rp=[lookup[x] for x in ref];cp=[lookup[x] for x in cand]
    re_edges=sorted(dependency_edges(rp));ce_edges=sorted(dependency_edges(cp))
    matches=[i for i,r in enumerate(t['reference_plan_dags']) if matches_partial_order(cand,[lookup[x] for x in r['action_ids']],frozenset(tuple(e) for e in r['partial_order_edges']))]
    valid=execute_plan(problem,cp).valid
    assert valid==s['execution']['valid'] and bool(matches)==s['partial_order_match']
    assert (cand==ref)==s['exact_match']
    assert len(set(ref))==len(ref) and len(set(cand))==len(cand)
    mapping={a:'a_{%d}'%(i+1) for i,a in enumerate(ref)}
    extra=[a for a in cand if a not in mapping]
    mapping.update({a:'b_{%d}'%(i+1) for i,a in enumerate(extra)})
    pos={a:i for i,a in enumerate(cand)}
    reversed_edges=[(u,v) for u,v in re_edges if ref[u] in pos and ref[v] in pos and pos[ref[u]]>pos[ref[v]]]
    reverse_pairs={(ref[v],ref[u]) for u,v in reversed_edges}
    red_c=[(u,v) for u,v in ce_edges if (cand[u],cand[v]) in reverse_pairs]
    status='Exact: '+('yes' if cand==ref else 'no')+'; known family: '+('yes' if matches else 'no')+'; goal replay: '+('yes' if valid else 'no')
    seq=lambda ids:'$'+r'\;'.join(mapping[a] for a in ids)+'$'
    lines += [r'\clearpage\subsection{'+title+'}',r'\label{'+label+'}',
      r'\noindent\textbf{'+esc(task.replace('_',' '))+r'.} '+name+f', sample {si+1}, seed {s["seed"]}.'+r'\par\smallskip',
      r'\noindent\textbf{'+status+r'.}\par\medskip',
      r'\noindent\begin{minipage}[t]{.49\linewidth}\centering\textbf{Selected reference DAG}\par\medskip',
      graph(ref,re_edges,mapping,reversed_edges),r'\end{minipage}\hfill\begin{minipage}[t]{.49\linewidth}\centering\textbf{Submitted-plan DAG}\par\medskip',
      graph(cand,ce_edges,mapping,red_c,extra),r'\end{minipage}\par\medskip',
      r'\noindent Reference order: '+seq(ref)+r'.\par',
      r'\noindent Submitted order: '+seq(cand)+r'.\par\medskip',
      explanation+r'\par\medskip',r'\noindent\footnotesize\begin{tabular}{@{}lp{.88\linewidth}@{}}']
    lines += ['$'+mapping[a]+'$ & '+desc(a)+r' \\[2pt]' for a in ref+extra]
    lines += [r'\end{tabular}\normalsize']
    records.append({'task':task,'model':model,'sample_index':si,'seed':s['seed'],'reference':ref,'candidate':cand,'reference_edges':re_edges,'candidate_edges':ce_edges,'matched_reference_family_indices':matches,'goal_valid':valid,'source_file':str(path.relative_to(ROOT))})
    if ci==1:assert t['samples'][2]['exact_match'] and t['samples'][2]['execution']['valid']
    if ci==2:assert t['samples'][1]['partial_order_match'] and t['samples'][1]['execution']['valid']
(PAPER/'dag_matching_cases.tex').write_text('\n'.join(lines)+'\n')
(PAPER/'data/dag_matching_cases.json').write_text(json.dumps(records,indent=2)+'\n')
print('Verified and generated 3 reference/output DAG comparisons.')
