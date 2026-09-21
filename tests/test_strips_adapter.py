import pytest
from planspace.strips_adapter import StripsAdapter
from planspace.core import execute_plan

D='''(define (domain d) (:requirements :strips) (:predicates (p ?x) (q ?x))
(:action move :parameters (?x) :precondition (p ?x) :effect (and (q ?x) (not (p ?x)))))'''
P='''(define (problem t) (:domain d) (:objects a b) (:init (p a)) (:goal (q a)))'''

def test_strips_replay_and_failure():
    x=StripsAdapter.parse(D,P)
    a=x.action('(MOVE A)')
    assert execute_plan(x.problem,[a]).valid
    result=execute_plan(x.problem,[a,a])
    assert not result.valid and result.failure_step==1

def test_adapter_rejects_unsupported_semantics():
    with pytest.raises(ValueError):StripsAdapter.parse(D.replace(':strips',':strips :adl'),P)
    with pytest.raises(ValueError):StripsAdapter.parse(D.replace(':precondition (p ?x)',':precondition (not (p ?x))'),P)
    with pytest.raises(ValueError):StripsAdapter.parse(D,P).action('(move c)')
    with pytest.raises(ValueError):StripsAdapter.parse(D,P).action('(move a b)')
