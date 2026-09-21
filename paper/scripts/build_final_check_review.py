"""Build yellow review of the current editorial release using audited anchors."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
import sys

base = Path(__file__).resolve().parents[2]
out = base / 'release' / (sys.argv[2] if len(sys.argv)>2 else 'final_check_20260919')
archive = base / 'release' / (sys.argv[1] if len(sys.argv)>1 else 'final_check_clean_20260919') / 'PlanSpace_ICLR2027_LaTeX.zip'
root_name = 'PlanSpace_ICLR2027_LaTeX'
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as z:
    z.extractall(out)
    names = z.namelist()
source = out / root_name
specs = []
# Reuse editorial selections, not the older builder's paths or transformations.
tree = ast.parse((base / 'paper/scripts/build_yellow_review.py').read_text())
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id == 'mark':
            args = [ast.literal_eval(a) for a in call.args]
            kwargs = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
            specs.append((kwargs.get('file', 'main.tex'), args[0], args[1], args[-1]))

def add(cat, start, end, file='main.tex'):
    specs.append((file, cat, start, end))

add('limit', 'Because the dependency rules are conservative,', 'new action composition.')
add('limit', 'Because some DAGs exceed the replay cap,', 'exhaustive execution certificate.')
add('limit', 'The constructor yields reproducible solutions,', 'unexplored.')
add('performance', 'Operator-composition tasks instead have the lowest goal validity', 'selected reference.')
add('AI_and_limit', 'Blinded AI judgments on 120 stratified archived outputs', 'prevalence estimate.')
add('limit', 'This task-consistent track combines historical and repair runtimes;', '(Appendix~\\ref{app:reviewer-verification}).')
add('performance', 'Known-family coverage changes little', 'five-draw budget.')
add('limit', 'Our conclusions concern a high-level symbolic action model', 'reliability across the benchmark.')
add('limit', 'The \\VTwoTaskCount{} tasks pass both compiler-support', 'omits explicit preconditions and effects.')
add('limit_and_AI', 'The constructed families need not cover every valid ordering or composition,', 'and audit boundaries.')
add('limit', 'These checks cover the target objects,', 'repeated execution reliability.')
add('limit', 'This checks execution correspondence under shared semantics,', '(Appendix~\\ref{app:reviewer-verification}).', 'reviewer_results.tex')
add('limit', 'The original benchmark already used goal verification:', 'its conclusion.', 'reviewer_results.tex')
add('performance', 'A held-out skill-outage selection test establishes no incremental', 'tested budget of three.', 'reviewer_results.tex')
add('limit', 'Runtime and hardware comparisons must not treat this as', 'a homogeneous regeneration.', 'reviewer_appendix.tex')
add('performance', 'Phi and OLMo each yield none.', 'Phi and OLMo each yield none.', 'reviewer_appendix.tex')
add('limit', 'The common direct/feedback intersection contains only', 'initially targeted 200 pairs.', 'reviewer_appendix.tex')
add('limit', 'This is independent execution of a shared formalization,', 'physical execution.', 'reviewer_appendix.tex')
add('limit', 'Two additional Logistics direct outputs', 'all failure stages as identical.', 'reviewer_appendix.tex')
add('limit', 'These CPU verification measurements exclude', 'cross-platform speed or memory superiority.', 'reviewer_appendix.tex')
add('limit', 'However, the current same-ID direct archive', 'identified causal effect of feedback.', 'reviewer_appendix.tex')
add('limit', 'These intervals describe the selected archive,', 'preregistered population comparison.', 'reviewer_appendix.tex')
add('limit', 'The bounds prevent a claim', 'coverage.', 'reviewer_appendix.tex')
add('performance', 'Action-multiset agreement alone', 'substitute for replay either.', 'reviewer_appendix.tex')
add('limit', 'This is symbolic skill availability,', 'physical robustness or a repair algorithm.', 'reviewer_appendix.tex')
add('performance', 'Family-minus-random task-macro differences', 'outside these candidate pools.', 'reviewer_appendix.tex')

def pattern(s):
    return re.compile(r'\s+'.join(re.escape(x) for x in s.split()))

edits, unmatched = {}, []
for file, category, start, end in specs:
    text = (source/file).read_text()
    matches = list(pattern(start).finditer(text))
    stop = None
    if len(matches) == 1:
        stop = matches[0] if start == end else pattern(end).search(text, matches[0].end())
    if stop is None:
        unmatched.append({'file': file, 'category': category, 'start': start})
        continue
    begin, finish = matches[0].start(), stop.end()
    chosen = text[begin:finish]
    if '\n\n' in chosen or chosen.count('{') != chosen.count('}'):
        raise ValueError((file, start, 'unsafe span'))
    edits.setdefault(file, []).append([begin, finish, {category}])

records, commands = [], set()
for file, intervals in edits.items():
    text = (source/file).read_text()
    merged = []
    for begin, end, cats in sorted(intervals):
        if merged and begin < merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
            merged[-1][2].update(cats)
        else:
            merged.append([begin, end, cats])
    original = text
    for begin, end, cats in reversed(merged):
        chosen = original[begin:end]
        commands.update(re.findall(r'\\([A-Z][A-Za-z]+)', chosen))
        records.append({'file': file, 'line': original[:begin].count('\n')+1,
                        'categories': sorted(cats), 'text': chosen})
        text = text[:begin] + r'\reviewhl{' + chosen + '}' + text[end:]
    # Highlighting must be mechanically reversible, including overlapping selections.
    check = text
    for begin, end, _ in merged:
        chosen = original[begin:end]
        check = check.replace(r'\reviewhl{'+chosen+'}', chosen, 1)
    assert check == original, file
    (source/file).write_text(text)

preamble = r'''
% Yellow editorial marks: see EDITORIAL_FINAL_CHECK.md and highlight_manifest.json.
\usepackage{soul}
\newif\ifreviewhighlight
\reviewhighlighttrue
\sethlcolor{yellow}
\DeclareRobustCommand{\reviewhl}[1]{\ifreviewhighlight\hl{#1}\else#1\fi}
\soulregister\ref7
\soulregister\method0
\pdfstringdefDisableCommands{\def\reviewhl#1{#1}}
'''
for command in sorted(commands):
    preamble += '\\expandafter\\soulregister\\csname '+command+'\\endcsname0\n'
main = source/'main.tex'
main.write_text(main.read_text().replace(r'\begin{document}', preamble+'\n'+r'\begin{document}', 1))
records.sort(key=lambda r: (r['file'], r['line']))
(source/'highlight_manifest.json').write_text(json.dumps(records, indent=2)+'\n')
(out/'unmatched_legacy_anchors.json').write_text(json.dumps(unmatched, indent=2)+'\n')
with (out/'compile.log').open('w') as log:
    subprocess.run(['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','main.tex'],
                   cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
pdf = out/'PlanSpace_FinalCheck.pdf'
shutil.copy2(source/'main.pdf', pdf)
with zipfile.ZipFile(out/'PlanSpace_FinalCheck_LaTeX.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:
        z.write(out/name, name)
    z.write(source/'highlight_manifest.json', root_name+'/highlight_manifest.json')
print(json.dumps({'highlights':len(records), 'unmatched':len(unmatched), 'output':str(out)}))
