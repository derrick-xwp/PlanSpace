"""Conservative exact export for tasks with provably static access ancestry.

Reject moving containers/ancestors, potential ontop cycles, unknown guards,
and non-location-preserving transfers. This checks execution correspondence,
not fidelity of the original household abstraction to a simulator.
"""
from collections import defaultdict
from .core import fact

SPATIAL={'inside','ontop','inroom','onfloor','draped'}
ANCESTRY={'inside','ontop','draped'}


def spatial(p):return p.name in SPATIAL and len(p.args)==2


def compile_static(problem):
    moved={p.args[0] for a in problem.actions for p in a.add_effects|a.delete_effects if spatial(p)}
    initial_locations=defaultdict(set);parents=defaultdict(set);ontop=defaultdict(set)
    for p in problem.initial_state:
        if spatial(p):initial_locations[p.args[0]].add(p)
        if p.name in ANCESTRY and len(p.args)==2:parents[p.args[0]].add(p.args[1])
    if any(len(v)>1 for v in initial_locations.values()):raise ValueError('initial_nonunique_location')
    for p in problem.initial_state|frozenset(p for a in problem.actions for p in a.add_effects):
        if spatial(p) and p.args[0]==p.args[1]:raise ValueError('possible_self_location')
        if p.name=='ontop' and len(p.args)==2:ontop[p.args[0]].add(p.args[1])
    def cyclic(start,node,visited):
        for target in ontop[node]:
            if target==start:return True
            if target not in visited and cyclic(start,target,visited|{target}):return True
        return False
    if any(cyclic(x,x,{x}) for x in list(ontop)):raise ValueError('possible_ontop_cycle')
    guards={}
    for action in problem.actions:
        if set(action.constraints)-{'spatial_irreflexive','spatial_unique_location','ontop_acyclic','open_access_chains'}:
            raise ValueError('unknown_constraint')
        additions={p for p in action.add_effects if spatial(p)}
        deletions={p for p in action.delete_effects if spatial(p)}
        if additions or deletions:
            if len(additions)!=1 or len(deletions)!=1:raise ValueError('not_single_transfer')
            add=next(iter(additions));delete=next(iter(deletions))
            if add.args[0]!=delete.args[0] or delete not in action.preconditions:raise ValueError('not_location_preserving')
        required=set()
        if 'open_access_chains' in action.constraints:
            roots=[]
            for source in action.access_sources:
                if source in moved and not initial_locations[source]<=action.preconditions:
                    raise ValueError('moving_access_source_not_pinned')
                roots.extend(parents[source])
            roots.extend(action.access_targets)
            seen=set()
            while roots:
                node=roots.pop()
                if node in seen:continue
                seen.add(node)
                if node in moved:raise ValueError('moving_access_ancestor_or_target')
                if node in action.gated_containers:required.add(fact('open',node))
                roots.extend(parents[node])
        guards[action.action_id]=frozenset(required)
    facts=set(problem.initial_state)|set().union(*(set(g) for g in (problem.goal_alternatives or (problem.goal,))))
    for a in problem.actions:facts.update(a.preconditions|a.add_effects|a.delete_effects|guards[a.action_id])
    fmap={p:f'f{i}' for i,p in enumerate(sorted(facts))}
    amap={a.action_id:f'a{i}' for i,a in enumerate(problem.actions)}
    def conjunction(preds):return '(and '+' '.join('('+fmap[p]+')' for p in sorted(preds))+')'
    lines=['(define (domain planspace-static)', '(:requirements :strips :disjunctive-preconditions)',
           '(:predicates '+' '.join('('+x+')' for x in fmap.values())+')']
    for a in problem.actions:
        effects=' '.join('('+fmap[p]+')' for p in sorted(a.add_effects))+' '+ ' '.join('(not ('+fmap[p]+'))' for p in sorted(a.delete_effects))
        lines.append(f'(:action {amap[a.action_id]} :parameters () :precondition {conjunction(a.preconditions|guards[a.action_id])} :effect (and {effects}))')
    lines.append(')')
    goals=problem.goal_alternatives or (problem.goal,)
    goal=conjunction(goals[0]) if len(goals)==1 else '(or '+' '.join(conjunction(g) for g in goals)+')'
    pddl=f'(define (problem planspace-task) (:domain planspace-static) (:init '+ ' '.join('('+fmap[p]+')' for p in sorted(problem.initial_state))+f') (:goal {goal}))'
    return '\n'.join(lines),pddl,amap,{'additional_open_guards':{k:sorted(map(str,v)) for k,v in guards.items()},
        'fact_map':{str(p):v for p,v in fmap.items()},'support_policy':'static access ancestors, location-preserving transfers, acyclic union of ontop edges'}
