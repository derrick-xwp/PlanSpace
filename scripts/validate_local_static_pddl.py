"""Independent VAL replay for the proved-exportable local semantic subset."""
from pathlib import Path
import hashlib,json,subprocess,time
from planspace.bddl_parser import parse_problem_file
from planspace.generic_domain import generic_household_problem
from planspace.static_pddl_export import compile_static

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/reviewer_revision_20260919'

def main():
    run=OUT/'local_static_val_v1';run.mkdir(exist_ok=False)
    inputs=json.loads((OUT/'fireplace_repair_verification.json').read_text())['models']
    binary=ROOT/'external/LLMs-Planning-review-20260919/planner_tools/VAL/validate'
    supported={};unsupported={};rows=[]
    for item in inputs:
        source=ROOT/item['corrected_artifact'];assert hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256']
        data=json.loads(source.read_text())
        for task in data['tasks']:
            key=task['activity']
            if key not in supported and key not in unsupported:
                src=ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/task['source_path']
                assert hashlib.sha256(src.read_bytes()).hexdigest()==task['source_sha256']
                p=generic_household_problem(parse_problem_file(src))
                try:domain,problem,amap,meta=compile_static(p)
                except ValueError as error:unsupported[key]=str(error);continue
                folder=run/key;folder.mkdir()
                (folder/'domain.pddl').write_text(domain);(folder/'problem.pddl').write_text(problem)
                (folder/'mapping.json').write_text(json.dumps(meta,indent=2)+'\n');supported[key]=(folder,amap)
            if key in unsupported:continue
            folder,amap=supported[key]
            for s in task['samples']:
                if s['parse_error'] is not None:
                    rows.append({'model':item['model'],'task':key,'sample':s['sample_index'],'status':'interface_failure_no_plan','val':None});continue
                plan=s['parsed_plan'];assert all(a in amap for a in plan)
                slug=source.stem;dest=folder/f"{slug}_{s['sample_index']}.plan"
                dest.write_text('\n'.join('('+amap[a]+')' for a in plan)+'\n')
                t=time.perf_counter()
                proc=subprocess.run([str(binary),'-v',str(folder/'domain.pddl'),str(folder/'problem.pddl'),str(dest)],capture_output=True,text=True,timeout=10)
                output=proc.stdout+proc.stderr;dest.with_suffix('.val.txt').write_text(output)
                if 'Plan valid' in output:val=True
                elif 'Plan invalid' in output or 'Plan failed to execute' in output:val=False
                else:raise RuntimeError(output)
                rows.append({'model':item['model'],'task':key,'sample':s['sample_index'],'status':'validated','val':val,
                             'local':bool((s.get('execution') or {}).get('valid')),'seconds':time.perf_counter()-t})
        print(item['model'],len(rows),flush=True)
    mismatches=[r for r in rows if r['status']=='validated' and r['val']!=r['local']]
    report={'supported_tasks':sorted(supported),'unsupported_tasks':unsupported,'rows':rows,'mismatches':mismatches,
            'val_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'exporter_sha256':hashlib.sha256((ROOT/'src/planspace/static_pddl_export.py').read_bytes()).hexdigest(),
            'boundary':'Independent execution of a conservatively supported semantics export; not external validation of task abstraction or physical fidelity.'}
    (OUT/'local_static_val_v1.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'supported':len(supported),'unsupported':len(unsupported),'validated':sum(r['status']=='validated' for r in rows),'mismatches':len(mismatches)}))

if __name__=='__main__':main()
