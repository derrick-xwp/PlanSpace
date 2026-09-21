"""Render archived reference DAGs with source/replay/edge verification."""
from pathlib import Path
import json, re, hashlib, sys
from collections import Counter
from functools import lru_cache
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.core import execute_plan
from planspace.partial_order import dependency_edges
PAPER=ROOT/'paper'
OUT=ROOT/'release/compact_dag_atlas_20260920'
OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'artifacts/reviewer_revision_20260919/family_construction_v1.json').read_text())

def esc(s):
    return s.replace('_',r'\_').replace('&',r'\&').replace('%',r'\%').replace('#',r'\#')

def obj(s):
    return esc(re.sub(r'\.n\.\d+', '', s).replace('_',' '))

def describe(a):
    p=a.split('::')
    if p[0]=='transfer':
        src,dst=p[2].split('->')
        rel1,o1=src.split(':');rel2,o2=dst.split(':')
        return 'Transfer '+obj(p[1])+': '+rel1+' '+obj(o1)+r' $\rightarrow$ '+rel2+' '+obj(o2)
    return esc(p[0].replace('_',' ').title())+' '+obj(p[1])

def stats(r):
    n=len(r['action_ids']); edges=r['conservative_edges']
    ranks=[0]*n
    for i in range(n):
        ranks[i]=max([ranks[u]+1 for u,v in edges if v==i] or [0])
    out=Counter(u for u,v in edges);inc=Counter(v for u,v in edges)
    return ranks,sum(x>1 for x in out.values()),sum(x>1 for x in inc.values())

def ordercount(n,edges):
    pred=[sum(1<<u for u,v in edges if v==i) for i in range(n)]
    @lru_cache(None)
    def f(mask):
        if mask==(1<<n)-1:return 1
        return sum(f(mask|(1<<i)) for i in range(n) if not mask>>i&1 and pred[i]&mask==pred[i])
    return f(0)

def panel(t,ri,index):
    r=t['references'][ri];ids=r['action_ids'];edges=r['conservative_edges']
    ranks,forks,joins=stats(r);depth=max(ranks)
    layers={k:[i for i,x in enumerate(ranks) if x==k] for k in set(ranks)}
    lines=[r'\noindent\begin{minipage}{\linewidth}\footnotesize',
      r'\textbf{'+esc(f"G{index:03d}. "+t['task'].replace('_',' '))+r'}\label{dag:task-'+str(index)+r'}\par',
      f"Reference {ri+1}/{len(t['references'])}; {len(ids)} nodes, {len(edges)} edges; "+f"{ordercount(len(ids),edges):,} admitted orders."+r'\par\smallskip',
      r'\centering\begin{tikzpicture}[x=1cm,y=1cm]']
    positions={}
    for i,a in enumerate(ids):
        layer=layers[ranks[i]];x=.5+(11.8*ranks[i]/max(depth,1));y=.57*((len(layer)-1)/2-layer.index(i))
        positions[i]=(x,y)
        lines.append(r'\node[psdag/node] (n%d) at (%.3f,%.3f) {$a_{%d}$};'%(i,x,y,i+1))
    for u,v in edges:
        xu,yu=positions[u];xv,yv=positions[v]
        obstructed=any(xu<x<xv and abs(y-(yu+(yv-yu)*(x-xu)/(xv-xu)))<.27
                       for k,(x,y) in positions.items() if k not in (u,v))
        if obstructed:
            roof=max(y for x,y in positions.values())+.45
            lines.append(r'\draw[psdag/edge,rounded corners=3pt] (n%d.north east) -- (%.3f,%.3f) -- (%.3f,%.3f) -- (n%d.north west);'%(u,xu+.4,roof,xv-.4,roof,v))
        else:
            lines.append(r'\draw[psdag/edge] (n%d) -- (n%d);'%(u,v))
    lines += [r'\end{tikzpicture}\par\smallskip\raggedright',
      r'\begin{tabular}{@{}rp{.425\linewidth}rp{.425\linewidth}@{}}']
    half=(len(ids)+1)//2
    for i in range(half):
        j=i+half
        right=(f'$a_{{{j+1}}}$ & '+describe(ids[j])) if j<len(ids) else ' & '
        lines.append(f'$a_{{{i+1}}}$ & '+describe(ids[i])+' & '+right+r' \\[1pt]')
    lines += [r'\end{tabular}\end{minipage}\par']
    return '\n'.join(lines)+'\n'

selected=[];records=[]
for t in data['tasks']:
    ri=max(range(len(t['references'])),key=lambda i:(sum(stats(t['references'][i])[1:]),len(t['references'][i]['action_ids']),len(t['references'][i]['conservative_edges']),-i))
    r=t['references'][ri]
    path=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/t['source_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==t['source_sha256']
    problem=generic_household_problem(parse_problem_file(path));lookup={a.action_id:a for a in problem.actions}
    plan=[lookup[x] for x in r['action_ids']]
    assert execute_plan(problem,plan).valid,t['task']
    assert sorted(dependency_edges(plan))==[tuple(e) for e in r['conservative_edges']],t['task']
    selected.append((t,ri))
    records.append({'task':t['task'],'reference_index':ri,'action_ids':r['action_ids'],'edges':r['conservative_edges'],'source_sha256':t['source_sha256'],'replay_valid':True})
selected.sort(key=lambda x:(-sum(stats(x[0]['references'][x[1]])[1:]),-len(x[0]['references'][x[1]]['action_ids']),x[0]['task']))
intro=r'''\section{DAG Gallery from Experimental Tasks}
\label{app:real-dag-gallery}
These graphs are extracted from the archived reference-family construction
for 171 evaluated tasks, which contains 1,403 reference DAGs. Each node is an
action occurrence, and each arrow is a retained precedence constraint.
For each task we select the representative with the largest total number of
fork and join nodes, then the largest node and edge counts, breaking remaining
ties by archive order. Tasks are ordered by fork/join count, node count, and
name. This structural selection uses no model success scores.
Object labels retain instance numbers; the manifest maps them to full action
identifiers. These graphs represent constructed reference plans for benchmark
tasks. Every displayed representative was replayed
against its frozen source and its edges checked against the dependency builder.
The gallery contains one representative for every task. White rectangular
nodes and arrows follow the method figure's style. Each $a_i$ maps to the
action legend below its graph. Edge constraints are conservative; the number
of admitted orders is a graph count, while replay validation may be bounded.
Matching examples in Appendix~\ref{app:dag-matching-cases} explain how a
submitted sequence is compared with these graphs.
'''
def pages():
    # Keep each graph and its legend together, but let TeX fill each page.
    # Short tasks should not consume the same space as long-horizon tasks.
    result=[r'\clearpage']
    for i,(t,ri) in enumerate(selected):
        if i:
            result.append(r'\par\penalty0\vskip6mm')
        result.append(panel(t,ri,i+1))
    return '\n'.join(result)
gallery=pages()
(PAPER/'real_dag_gallery.tex').write_text(intro+gallery)
(PAPER/'data/real_dag_manifest.json').write_text(json.dumps({'total_tasks':171,'total_references':1403,'displayed_in_paper':[t['task'] for t,ri in selected],'verified_representatives':records},indent=2))
atlas=r'''\documentclass[10pt]{article}
\usepackage[a4paper,margin=20mm]{geometry}
\usepackage{tikz,xcolor,hyperref,times}
\setlength{\parindent}{0pt}
\begin{document}
\begin{center}\Large PlanSpace: Real Task DAG Atlas\end{center}
'''+intro.replace(r'Appendix~\ref{app:dag-matching-cases}', 'the paper appendix')+gallery+r'\end{document}'
atlas=atlas.replace(r'\begin{document}',(PAPER/'dag_style.tex').read_text()+'\n'+r'\begin{document}')
(OUT/'Real_Task_DAG_Atlas.tex').write_text(atlas)
print(json.dumps({'tasks':len(selected),'references':data['summary']['references'],'paper_panels':len(selected),'verified':len(records)}))
