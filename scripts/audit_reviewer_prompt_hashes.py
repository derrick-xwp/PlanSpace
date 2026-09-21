"""Check actual generated-prompt provenance against the frozen task source."""
import hashlib,json
from pathlib import Path
from planspace.bddl_parser import parse_problem_file
from planspace.domain_registry import get_generic_domain
from planspace.model_protocol import render_context_fit_model_prompt,prompt_sha256

ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'artifacts/reviewer_revision_20260919'
    freeze=json.loads((out/'input_freeze.json').read_text());rows=[];cache={}
    for entry in freeze['inputs']:
        p=ROOT/entry['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
        d=json.loads(p.read_text());domain=get_generic_domain(d['generic_domain_version'])
        for t in d['tasks']:
            key=(d['generic_domain_version'],t['source_path'])
            if key not in cache:
                src=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/t['source_path']
                assert hashlib.sha256(src.read_bytes()).hexdigest()==t['source_sha256']
                problem=domain.generic_household_problem(parse_problem_file(src))
                prompt=render_context_fit_model_prompt(problem)
                cache[key]=prompt_sha256(prompt)
            rows.append({'model':d['model_id'],'task':t['activity'],'archived_prompt_sha256':t['prompt_sha256'],
                         'rebuilt_prompt_sha256':cache[key],'matches':t['prompt_sha256']==cache[key]})
    report={'task_model_pairs':len(rows),'mismatches':[r for r in rows if not r['matches']],
            'unique_mismatched_tasks':sorted({r['task'] for r in rows if not r['matches']}),'rows':rows}
    dest=out/'prompt_hash_audit.json';assert not dest.exists()
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
