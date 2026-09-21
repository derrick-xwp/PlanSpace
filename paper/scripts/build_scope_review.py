"""Build a content-preserving yellow review from the current clean source zip."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

base = Path(__file__).resolve().parents[2]
release = base / 'release' / sys.argv[1]
out = release / 'yellow_review'
archive = release / 'PlanSpace_ICLR2027_LaTeX.zip'
root_name = 'PlanSpace_ICLR2027_LaTeX'
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as z:
    z.extractall(out)
    names = z.namelist()
source = out / root_name
specs = []


def mark(category, start, end=None, file='main.tex'):
    specs.append((file, category, start, end or start))


mark('scope', 'The dependency rule is conservative:', 'exclude a successful sequence.')
mark('scope', 'To check the orders that the graph', 'been replayed.')
mark('scope', 'The prompt lists admissible actions and operator names;', 'not included in the compact catalog.')
mark('scope', 'This task-consistent track contains 170 tasks', '(Appendix~\\ref{app:reviewer-verification}).')
mark('scope', 'Because \\IndependentBoundedTaskCount{} tasks hit', 'as the evaluator.')
mark('negative_result', 'Operator-composition tasks instead have the lowest', 'selected reference.')
mark('negative_result', 'Phi-4-mini and OLMo-2 instead lose', '5.4\\% failed actions.')
mark('negative_result', 'In contrast, OLMo-2 retains all 706', 'catalog mismatches unchanged.')
mark('AI_use', 'Blinded AI judgments on 120 stratified archived outputs', 'AI-labeled cases.')
mark('negative_result', 'Known-family coverage changes', 'five-draw budget.')
mark('scope', 'The evaluation covers a fixed set', 'selected controllers and scenes.')
mark('scope_and_AI_use', 'Reference families have bounded coverage,', 'broader task sampling and physical evaluation.')
mark('AI_use', 'Generative AI tools assisted with implementation,', 'final content and submission.')
mark('scope', 'Physical deployment requires additional safety and controller validation.')
mark('scope', 'The archived comparisons include hardware and seed differences', 'recorded settings.')
mark('scope', 'tasks, with seed agreement reported per checkpoint.', 'post-hoc diagnostic.')
mark('AI_use', 'Two isolated Codex roles reviewed a blinded, category-stratified sample', 'category-balanced audit sample.')
mark('AI_use', 'Metric discrimination against blinded two-role AI judgments with', 'third-role disagreement adjudication.')
mark('scope', 'For the largest DAG, the audit replays 2,000', 'orders.')
mark('AI_use', 'To review the translation, we supplied two isolated Codex CLI roles', 'approve, revise, or reject decisions.')
mark('AI_use', 'Two isolated roles review every case;', 'both original judgments.')
mark('scope', 'It was conducted after', 'separately from the preregistered pilot.')
mark('negative_result_and_scope', 'Thus, 12/36 deletion checks pass', 'observing the symbolic outcomes.')
mark('scope', 'Each setting is run once', 'Isaac Sim 4.5/PhysX.')
mark('scope', 'The task is adapted battery sorting:', 'language-model-generated plans.')
mark('negative_result', 'An initial one-battery pilot lifted the object but dropped it', 'reducing the commanded closure temporarily.')
mark('scope', 'The six placements are nested within', 'this controller correction.')
mark('scope', 'Sleeping bodies may stop emitting contact events;', 'retained in the logs.')
mark('scope', 'The demonstrations form a separate two-trial set,', '108-rollout physical audit.')
mark('scope', '39 tasks are explicitly outside the export\'s support.', file='reviewer_results.tex')
mark('negative_result', '117 remain outside. Another 125 valid outputs use different multisets.', file='reviewer_results.tex')
mark('negative_result', 'A held-out skill-outage selection test establishes no incremental', 'tested budget of three.', file='reviewer_results.tex')
mark('negative_result', 'Phi and OLMo each yield none.', file='reviewer_appendix.tex')
mark('scope', 'so the matrix combines historical and updated runtime conditions.', file='reviewer_appendix.tex')
mark('scope', 'Of 171 tasks, 132 pass this gate and 39 are unsupported.', file='reviewer_appendix.tex')
mark('scope', 'The current same-ID direct archive has 11 successful Logistics', 'original failed starting responses.', file='reviewer_appendix.tex')
mark('negative_result', 'Action-multiset agreement alone also admits invalid outputs.', file='reviewer_appendix.tex')
mark('negative_result', 'Family-minus-random task-macro differences', 'fixed five-draw candidate pools.', file='reviewer_appendix.tex')


def pattern(s):
    return re.compile(r'\s+'.join(re.escape(word) for word in s.split()))


edits, records, commands = {}, [], set()
for file, category, start, end in specs:
    text = (source / file).read_text()
    starts = list(pattern(start).finditer(text))
    assert len(starts) == 1, (file, start, len(starts))
    begin = starts[0].start()
    stop_match = starts[0] if start == end else pattern(end).search(text, starts[0].end())
    assert stop_match is not None, (file, end)
    stop = stop_match.end()
    chosen = text[begin:stop]
    assert '\n\n' not in chosen and chosen.count('{') == chosen.count('}'), start
    edits.setdefault(file, []).append((begin, stop, chosen))
    records.append({'file': file, 'category': category,
                    'line': text[:begin].count('\n') + 1, 'text': chosen})

for file, selections in edits.items():
    text = original = (source / file).read_text()
    boundary = len(text)
    for begin, stop, chosen in sorted(selections, reverse=True):
        assert stop <= boundary, ('overlap', file, chosen)
        boundary = begin
        commands.update(re.findall(r'\\([A-Z][A-Za-z]+)', chosen))
        text = text[:begin] + r'\reviewhl{' + chosen + '}' + text[stop:]
    inverse = text
    for _, _, chosen in selections:
        inverse = inverse.replace(r'\reviewhl{' + chosen + '}', chosen, 1)
    assert inverse == original, ('content changed', file)
    (source / file).write_text(text)

preamble = r'''
% Editorial review only. Set \reviewhighlightfalse to hide the marks.
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
    preamble += '\\expandafter\\soulregister\\csname ' + command + '\\endcsname0\n'
main = source / 'main.tex'
main.write_text(main.read_text().replace(r'\begin{document}', preamble + '\n' + r'\begin{document}', 1))
(source / 'highlight_manifest.json').write_text(json.dumps(records, indent=2) + '\n')
with (out / 'compile.log').open('w') as log:
    subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
                   cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
pdf = out / 'PlanSpace_YellowReview.pdf'
shutil.copy2(source / 'main.pdf', pdf)
review_zip = out / 'PlanSpace_YellowReview_LaTeX.zip'
with zipfile.ZipFile(review_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in names:
        z.write(out / name, name)
    z.write(source / 'highlight_manifest.json', root_name + '/highlight_manifest.json')
for path in (pdf, review_zip):
    path.with_suffix(path.suffix + '.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n')
print(json.dumps({'highlighted_spans': len(records), 'output': str(out)}))
