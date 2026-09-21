"""Guard the distinction between composition, DAG order and replay validity."""
from collections import Counter
from planspace.core import GroundAction, PlanningProblem, execute_plan, fact
from planspace.partial_order import dependency_edges, matches_partial_order


def test_same_multiset_outside_conservative_dag_can_be_valid():
    p, q, r = fact('p'), fact('q'), fact('r')
    # The initially true shared condition induces a conservative edge although
    # neither ordering needs the other's redundant add effect.
    a=GroundAction('a','a',(),frozenset({p}),frozenset({p,q}),frozenset())
    b=GroundAction('b','b',(),frozenset({p}),frozenset({r}),frozenset())
    problem=PlanningProblem('redundant-cause',frozenset({p}),frozenset({q,r}),(a,b))
    edges=dependency_edges((a,b))
    assert Counter(['a','b'])==Counter(['b','a'])
    assert not matches_partial_order(['b','a'],(a,b),edges)
    assert execute_plan(problem,(b,a)).valid


def test_goal_revision_can_invalidate_an_unchanged_reference():
    one,two=fact('inside','log1'),fact('inside','log2')
    a=GroundAction('move1','move',(),frozenset(),frozenset({one}),frozenset())
    b=GroundAction('move2','move',(),frozenset(),frozenset({two}),frozenset())
    old=PlanningProblem('old',frozenset(),frozenset({one}),(a,b))
    corrected=PlanningProblem('corrected',frozenset(),frozenset({one,two}),(a,b))
    assert matches_partial_order(['move1'],(a,),frozenset())
    assert execute_plan(old,(a,)).valid
    assert not execute_plan(corrected,(a,)).valid
    assert execute_plan(corrected,(a,b)).valid


def test_duplicate_occurrences_are_not_collapsed_into_a_set():
    a=GroundAction('a','a',(),frozenset(),frozenset(),frozenset())
    b=GroundAction('b','b',(),frozenset(),frozenset(),frozenset())
    assert not matches_partial_order(['a','b'],(a,b,a),frozenset())
    assert matches_partial_order(['a','b','a'],(a,b,a),frozenset({(0,1),(1,2)}))
    assert not matches_partial_order(['a','a','b'],(a,b,a),frozenset({(0,1),(1,2)}))
