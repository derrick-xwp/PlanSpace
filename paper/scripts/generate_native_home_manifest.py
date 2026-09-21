"""Generate anonymous, source-verified provenance for the new qualitative figure."""
import hashlib,json
from pathlib import Path
base=Path(__file__).resolve().parents[2];root=base/'output/simulation_storyboards/premium_physics_v1'
rows=[]
for condition in ('A','B'):
    run=root/f'multi_{condition}_01'
    result=json.loads((run/'result.json').read_text());audit=json.loads((run/'independent_audit.json').read_text())
    replay=json.loads((root/f'replay_multi_{condition}_01/replay_manifest.json').read_text())
    assert result['status']=='PASS'
    assert all(x['terminal_pose_stable_and_inside_target'] and x['target_support_contact_observed'] for x in audit['objects'])
    for name,h in audit['source_hashes'].items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==h
    rows.append({'run_id':run.name,'condition':condition,'count':result['object_count'],'result_status':result['status'],'environment_sha256':result['environment_sha256'],'runner_sha256':result['runner_sha256'],'source_hashes':audit['source_hashes'],'audit':audit['objects'],'selected_frames':[{'phase':f['phase'],'frame':f['frame'],'timeline_s':f['timeline_s']} for f in replay['frames'] if f['phase']!='close']})
out=base/'paper/data/native_home_contact_manifest.json'
out.write_text(json.dumps({'scope':'two selected native contact demonstrations in an adapted tabletop task; excluded from all frozen benchmark denominators','rendering':'offline Blender rendering of synchronized body poses without trajectory interpolation','retained_failed_pilot':'probe_A_01','passed_single_object_gate':'probe_A_02','rows':rows},indent=2)+'\n')
print(out)
