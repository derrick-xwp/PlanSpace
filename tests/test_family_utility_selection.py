import importlib.util
from pathlib import Path

p=Path(__file__).parents[1]/'scripts/evaluate_reviewer_family_utility.py'
spec=importlib.util.spec_from_file_location('utility',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_diversity_preserves_budget_and_is_repeatable():
    samples={i:None for i in range(5)};groups={0:'a',1:'a',2:'a',3:'b',4:'c'}
    selected=m.choose(samples,groups,7,3)
    assert len(selected)==3 and len({groups[i] for i in selected})==3
    assert selected==m.choose(samples,groups,7,3)

def test_fill_same_group_and_empty_pool():
    assert len(m.choose(range(5),dict.fromkeys(range(5),'same'),7,3))==3
    assert m.choose([],{},7,3)==[]
    assert len(m.choose([1,2],None,7,3))==2
