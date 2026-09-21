import pytest
from planspace.core import GroundAction,PlanningProblem,fact
from planspace.static_pddl_export import compile_static

def move(subject,source,target):
    return GroundAction(f'move-{subject}','move',(subject,source,target),frozenset({fact('ontop',subject,source)}),
        frozenset({fact('inside',subject,target)}),frozenset({fact('ontop',subject,source)}),
        constraints=('spatial_irreflexive','spatial_unique_location','ontop_acyclic','open_access_chains'),
        access_sources=(subject,),access_targets=(target,),gated_containers=frozenset({'box'}))

def test_export_adds_static_access_guard_without_using_runtime_guard():
    a=move('x','table','box')
    p=PlanningProblem('t',frozenset({fact('ontop','x','table'),fact('not_open','box')}),frozenset({fact('inside','x','box')}),(a,))
    domain,problem,actions,meta=compile_static(p)
    assert meta['additional_open_guards']['move-x']==['open(box)']
    assert '('+meta['fact_map']['open(box)']+')' in domain
    assert actions['move-x']=='a0'

def test_export_rejects_moving_container_ancestry():
    a=move('x','table','box');b=move('box','table','shelf')
    p=PlanningProblem('t',frozenset({fact('ontop','x','table'),fact('ontop','box','table')}),frozenset(),(a,b))
    with pytest.raises(ValueError,match='moving_access'):compile_static(p)

def test_export_rejects_possible_cycle_even_if_initially_acyclic():
    a=GroundAction('a','a',(),frozenset({fact('ontop','x','table')}),frozenset({fact('ontop','x','y')}),frozenset({fact('ontop','x','table')}))
    p=PlanningProblem('t',frozenset({fact('ontop','y','x'),fact('ontop','x','table')}),frozenset(),(a,))
    with pytest.raises(ValueError,match='cycle'):compile_static(p)
