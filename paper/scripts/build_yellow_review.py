"""Mechanically mark editorially selected spans in a separate LaTeX review copy."""
from pathlib import Path
import re
import json
import zipfile
import subprocess
import shutil
import hashlib

base = Path(__file__).resolve().parents[2]
out = base / 'release/yellow_review_20260919'
source_zip = base / 'release/syg_revision_20260919/PlanSpace_ICLR2027_LaTeX.zip'
root_name = 'PlanSpace_ICLR2027_LaTeX'
source = out / root_name
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(source_zip) as z:
    z.extractall(out)

# Exact human-selected start/end anchors, with whitespace ignored in matching.
# Categories are editorial labels, not recommendations to delete the passages.
spans = []
def mark(category, start, end=None, file='main.tex'):
    spans.append((file, category, start, end or start))

mark('scope', 'Our primary evaluation concerns symbolic planning;', 'stops being sufficient.')
mark('scope', 'In \\method, partial orders serve as evaluation', 'rather than a new planning algorithm.')
mark('limitation', 'Direct goal replay remains necessary', 'contain every solution.')
mark('limitation', 'Because some DAGs exceed the replay cap,', 'exhaustive execution certificate.')
mark('limitation', 'A low family score with high goal validity', 'omit successful plans.')
mark('defensive', 'Every plan set is labeled complete, bounded, or sampled', 'the full solution space.')
mark('limitation', 'Reading a source file does not establish', 'represented by the action model.')
mark('scope', 'Thus, a model chooses and orders high-level skills;', 'grasp poses or motion trajectories.')
mark('limitation', 'and 13 representatives reach its 1,000-order cap.', 'tasks reach the same cap.')
mark('defensive', 'Because the constructor produces these controls,', 'validate the existence of alternatives.')
mark('limitation', 'The prompt lists admissible actions and operator names;', 'not included in the compact catalog.')
mark('scope', 'The additional credit is tied to goal achievement under the symbolic model.')
mark('limitation', 'Because \\IndependentBoundedTaskCount{} tasks hit a search or solution bound,', 'independently validate the shared action semantics.')
mark('defensive', "Here ``minimum'' refers to", 'not a certified global optimum.')
mark('negative_result', 'Operator-composition tasks instead have the lowest goal validity', 'their size limits broader inference.')
mark('scope', 'Because the additional tasks pass the same semantic and shared-context feasibility filters,', 'across all BEHAVIOR-1K activities.')
mark('negative_result', 'Phi-4-mini and OLMo-2 instead lose', '13.8\\% parse failures and 5.4\\% failed actions.')
mark('defensive', 'No actions are generated or replanned in this test.')
mark('negative_result', 'In contrast, OLMo-2 retains all 706', 'the underlying cause.')
mark('defensive', 'The strict scores remain the primary results.')
mark('defensive', 'This sensitivity analysis is not a replacement leaderboard condition.')
mark('ai_use_and_boundary', 'We also compare the automatic metrics with blinded AI judgments', 'for the natural output distribution.')
mark('negative_result', 'More draws recover successes without broadly expanding family coverage.')
mark('negative_result', 'Known-family coverage changes little for the stronger checkpoints.', 'additional known solution families.')
mark('defensive', 'This comparison concerns a five-draw budget;', 'repairs any particular earlier output.')
mark('negative_result_and_boundary', 'The archived audit reports 31/108 passes', 'failed in the preceding diagnostic.')
mark('scope', 'Each destination setting has one native PhysX demonstration,', 'without fixed grasp constraints.')
mark('defensive', 'The images render synchronously recorded', 'without trajectory interpolation.')
mark('scope', 'They do not test equivalence in the original BEHAVIOR cabinet activity', 'excluded from the 108-rollout audit.')
mark('limitation', 'valid, although it does not exhaust the largest DAGs.', 'within the declared semantics.')
mark('defensive', 'Keeping these questions separate avoids', 'the wrong evaluation layer.')
mark('limitation', 'Even goal validity alone is insufficient for diagnosis', 'never pass the parser.')
mark('limitation', 'although the fidelity of that model still needs its own audit.')
mark('limitation', 'Our conclusions concern a high-level symbolic action model', 'robot reliability across the benchmark.')
mark('limitation', 'The \\VTwoTaskCount{} tasks pass both compiler-support', 'omits explicit preconditions and effects.')
mark('limitation_and_ai_use', 'The constructed families need not cover every valid composition,', 'not measure physical path length, energy, or risk.')
mark('ai_use', 'AI use statement')
mark('ai_use', 'Generative AI tools assisted with implementation,', 'final content and submission.')
mark('scope', 'Its scores describe behavior within the declared task model', 'evidence of safe physical deployment.')
mark('scope', 'The documented task and abstraction choices also delimit', 'household practices represented by the benchmark.')
mark('defensive', 'Because the archived comparisons do not hold every execution condition fixed,', 'a causal serialization effect.')
mark('defensive', 'as a cross-run sensitivity measurement rather than', 'a hardware-controlled serialization experiment.')
mark('negative_result', 'The largest goal-validity shift is an', 'for \\PromptEffectLargestGoalModel{}.')
mark('defensive', 'but sample seeds need not coincide throughout.', 'not a same-seed confirmatory experiment.')
mark('ai_use', 'AI-assisted metric audit.')
mark('ai_use_and_boundary', 'Two isolated Codex roles reviewed a blinded, category-stratified sample', 'not population validity.')
mark('ai_use', 'Metric discrimination against blinded two-role AI judgments', 'third-role disagreement adjudication.')
mark('limitation', 'this is a lower bound because', 'semantic correctness as a separate question.')
mark('limitation', 'The largest DAG has \\CapSensitiveMaxOrderCount{} orders,', 'most of that family untested.')
mark('defensive', 'The cap controls the amount of replay evidence,', 'Its goal validity is then checked by replay of that output.')
mark('defensive', 'The archived table permits tracing earlier results', 'mixing semantic versions in the primary comparison.')
mark('scope', 'No tool calls, retries, or execution feedback are supplied during generation.')
mark('scope', 'Thus, generation receives no opportunity', 'revise a plan in response to execution.')
mark('ai_use_and_boundary', 'To review the translation, we supplied two isolated Codex CLI roles', 'not independent human validation.')
mark('ai_use_and_boundary', 'Two isolated roles review every case;', 'the natural output distribution.')
mark('defensive', 'It was conducted after the symbolic outcomes', 'separately from the preregistered pilot.')
mark('defensive', 'Adding these 12 passes', 'not a pooled task-success rate.')
mark('negative_result_and_boundary', 'An amended three-task replication', 'rather than a preregistered estimate.')
mark('negative_result', 'because the headless Isaac viewport failed during capture,', 'rendered offline in Blender 4.2.9.')
mark('defensive', 'Camera, lighting, background, and presentation materials changed;', 'not the frequency of successful execution.')
mark('scope', 'Each setting is run once with Lula inverse kinematics', 'Isaac Sim 4.5/PhysX.')
mark('limitation', 'We set battery mass to 23\\,g', 'using engineering estimates.')
mark('defensive', 'No fixed grasp constraint or runtime object-pose teleport is used.')
mark('scope', 'The task is adapted battery sorting:', 'or language-model-generated plans.')
mark('negative_result', 'An initial one-battery pilot lifted the object but dropped it', 'reducing the commanded closure temporarily.')
mark('negative_result_and_boundary', 'The failed pilot remains in the archive.', 'not six independent reliability trials.')
mark('limitation', 'Sleeping bodies may stop emitting contact events;', 'retained in the logs.')
mark('defensive', 'The result is an offline rendering of a native trial,', 'not a simulator-camera screenshot.')
mark('scope', 'These demonstrations are excluded', '108-rollout physical-audit denominator.')
mark('defensive', 'Metrics such as regret are computed on their declared conditional subsets', 'for, full-denominator validity.')
mark('scope', 'one native PhysX trial per destination.', file='figures/native_home_contact.tex')
mark('defensive', 'Offline renders use synchronized recorded body poses', 'rather than fixed constraints.', file='figures/native_home_contact.tex')
mark('scope', 'These selected cases show physical realization in the adapted task,', 'repeated-trial success rates.', file='figures/native_home_contact.tex')
mark('defensive', 'Seed matches are reported explicitly;', 'not a same-seed confirmatory experiment.', file='generated_cross_run_v09.tex')
mark('scope', 'The fixed assignment priority separates task structures', 'not population difficulty.', file='results_v02_tables.tex')
mark('defensive', 'Early OLMo outputs motivated this secondary analysis.', file='results_v02_tables.tex')

def pattern(s):
    return re.compile(r'\s+'.join(re.escape(x) for x in s.split()))

grouped = {}
records = []
for file, category, start, end in spans:
    text = (source / file).read_text()
    starts = list(pattern(start).finditer(text))
    assert len(starts) == 1, (file, start, len(starts))
    begin = starts[0].start()
    stop = starts[0].end() if start == end else pattern(end).search(text, starts[0].end()).end()
    chosen = text[begin:stop]
    assert '\n\n' not in chosen, (start, 'crosses a paragraph')
    assert chosen.count('{') == chosen.count('}'), (start, 'unbalanced braces')
    grouped.setdefault(file, []).append((begin, stop, chosen))
    records.append({'id': len(records)+1, 'file': file, 'category': category,
                    'line': text[:begin].count('\n')+1, 'text': chosen})

commands = set()
for file, edits in grouped.items():
    text = (source / file).read_text()
    original = text
    last = len(text)+1
    for begin, stop, chosen in sorted(edits, reverse=True):
        assert stop <= last, ('overlap', file, chosen)
        last = begin
        commands.update(re.findall(r'\\([A-Z][A-Za-z]+)', chosen))
        text = text[:begin] + r'\reviewhl{' + chosen + '}' + text[stop:]
    # Mechanical inverse check before introducing the preamble.
    check = text
    for _, _, chosen in edits:
        check = check.replace(r'\reviewhl{'+chosen+'}', chosen, 1)
    assert check == original, ('content changed', file)
    (source / file).write_text(text)

preamble = r'''
% Editorial review copy. Set \reviewhighlightfalse to hide the yellow marks.
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
main = source / 'main.tex'
text = main.read_text()
# Register generated numerical macros after they have been loaded.
text = text.replace(r'\begin{document}', preamble+'\n'+r'\begin{document}', 1)
main.write_text(text)
(out / 'highlight_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
(source / 'HIGHLIGHT_REVIEW_README.txt').write_text(
    'Yellow marks identify AI use disclosures, negative/limited outcomes, and '
    'scope or defensive qualifications selected for editorial review. '
    'Highlighting is not a recommendation to delete a statement. '
    'No original wording, numerical result, citation or figure was removed.\n'
    'Compile with latexmk -pdf main.tex. Set \\reviewhighlightfalse in main.tex '
    'to hide the marks. The clean SYG release remains unchanged.\n')
print(f'Selected {len(records)} spans in {len(grouped)} files.', flush=True)
with (out / 'compile.log').open('w') as log:
    subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
                   cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
pdf = out / 'PlanSpace_ICLR2027_YellowReview.pdf'
shutil.copy2(source / 'main.pdf', pdf)
with zipfile.ZipFile(source_zip) as z:
    names = z.namelist()
archive = out / 'PlanSpace_ICLR2027_YellowReview_LaTeX.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in names:
        z.write(out / name, name)
    z.write(source / 'HIGHLIGHT_REVIEW_README.txt', root_name+'/HIGHLIGHT_REVIEW_README.txt')
    z.write(out / 'highlight_manifest.json', root_name+'/highlight_manifest.json')
for path in (pdf, archive):
    path.with_suffix(path.suffix+'.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
print(out, flush=True)
