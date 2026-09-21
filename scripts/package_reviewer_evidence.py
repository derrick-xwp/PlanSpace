"""Package frozen reviewer evidence without modifying the shared manuscript."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,zipfile

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/reviewer_revision_20260919'
OUT=ROOT/'release/reviewer_revision_20260919'
SCRIPTS=['verify_reviewer_revision_release.py','package_reviewer_evidence.py',
 'evaluate_external_reviewer_archive.py','analyze_external_reviewer_statistics.py',
 'validate_local_static_pddl.py','validate_reviewer_controls.py',
 'analyze_reviewer_family_construction.py','evaluate_reviewer_family_sensitivity.py',
 'evaluate_reviewer_family_utility.py','diagnose_family_utility_floor.py',
 'audit_corrected_secondary_metrics.py','analyze_action_prefix_sensitivity.py',
 'analyze_catalog_projection_sensitivity.py','audit_verifier_stages_and_costs.py',
 'enrich_partial_order_metrics.py','analyze_model_queue.py',
 'audit_independent_family_probes.py','analyze_partial_order_cap_sensitivity.py',
 'measure_cap_budgets.py']
DOCS=['REVIEWER_EXPERIMENT_PLAN_20260919.md','VERIFICATION_COMPARISON_20260919.md',
      'REVIEWER_RESPONSE_MAP_20260919.md','REVIEWER_REPRODUCTION_20260919.md',
      'REVIEWER_COMPLETION_AUDIT_20260919.md']

def main():
    files=set()
    def add(path):
        path=Path(path)
        assert path.is_file(),path
        assert path.resolve().is_relative_to(ROOT.resolve())
        files.add(path.relative_to(ROOT))
    for path in ART.rglob('*'):
        if path.is_file() and path.suffix not in ['.tgz','.pyc'] and 'fireplace_repair_bundle' not in path.parts:
            add(path)
    for path in (ROOT/'src/planspace').glob('*.py'):add(path)
    for name in SCRIPTS:add(ROOT/'scripts'/name)
    for name in DOCS:add(ROOT/'docs'/name)
    for name in ['test_reviewer_revision_structures.py','test_strips_adapter.py','test_static_pddl_export.py','test_family_utility_selection.py']:
        add(ROOT/'tests'/name)
    add(ROOT/'configs/reviewer_family_utility_v1.json')
    add(ROOT/'configs/model_matrix_v0_9_context_171_six_model_gpuhub.json')
    add(ART/'fireplace_repair_bundle/configs/repair.json')
    for name in ['generate_reviewer_revision_data.py','generate_cap_resources.py']:add(ROOT/'paper/scripts'/name)
    add(ROOT/'paper/generated_v09_context.tex')
    for name in ['generic_domain_audit_175_v05.json','structural_splits_171_context_v0_1.json',
                 'independent_state_search_v0_1.json','action_semantics_supported_queue_171_context_v0_1.json']:
        add(ROOT/'artifacts'/name)
    for record in json.loads((ART/'input_freeze.json').read_text())['inputs']:
        add(ROOT/record['path'])
    for path in (ROOT/'artifacts').glob('*_action_prefix_sensitivity_v0_9_context171_six.json'):add(path)
    models=json.loads((ART/'fireplace_repair_verification.json').read_text())['models']
    data=json.loads((ROOT/models[0]['corrected_artifact']).read_text())
    for task in data['tasks']:add(ROOT/'tmp/automation_v05_authoritative_etWEL0/frozen_source'/task['source_path'])
    external=ROOT/'external/LLMs-Planning-review-20260919'
    freeze=json.loads((ART/'external_archive_freeze.json').read_text())
    for source in freeze['source_files']:add(ROOT/source['path'])
    for row in freeze['task_rows']:add(ROOT/row['problem'])
    for dom in ['blocksworld','logistics']:
        add(external/'llm_planning_analysis/configs'/f'{dom}.yaml')
        add(external/'llm_planning_analysis/instances'/dom/'generated_domain.pddl')
    val=external/'planner_tools/VAL'
    for sub in ['src','include','parser']:
        for path in (val/sub).rglob('*'):
            if path.is_file() and path.suffix not in ['.o','.d']:add(path)
    for name in ['LICENSE','README.md','Makefile','Make.files','Make.header','validate']:add(val/name)
    for path in external.glob('*LICENSE*'):
        if path.is_file():add(path)
    manifest={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(files)}
    OUT.mkdir(parents=True,exist_ok=True)
    archive=OUT/'PlanSpace_reviewer_evidence_20260919.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(files):z.write(ROOT/path,'PlanSpace_reviewer_evidence/'+str(path))
        z.writestr('PlanSpace_reviewer_evidence/REVIEWER_BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='planspace-evidence-check-') as tmp:
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            z.extractall(tmp)
        folder=Path(tmp)/'PlanSpace_reviewer_evidence'
        env={**os.environ,'PYTHONPATH':str(folder/'src')}
        result=subprocess.run([sys.executable,'scripts/verify_reviewer_revision_release.py'],cwd=folder,env=env,capture_output=True,text=True,check=True)
        (OUT/'evidence_standalone_verification.json').write_text(result.stdout)
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(sha+'  '+archive.name+'\n')
    (OUT/'evidence_package_manifest.json').write_text(json.dumps({'sha256':sha,'bytes':archive.stat().st_size,
         'files':len(files)+1,'source_hashes':manifest,'boundary':'Internal provenance archive; not anonymized public supplementary material.'},indent=2)+'\n')
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files)+1,'verification':'PASS'},indent=2))

if __name__=='__main__':main()
