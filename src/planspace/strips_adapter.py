"""Fail-closed, untyped positive-STRIPS adapter for frozen external domains.

Only the :strips fragment is accepted. This is not a general PDDL parser and
does not translate the household executor's dynamic constraints.
"""
from dataclasses import dataclass
from .bddl_parser import parse_sexpression
from .core import GroundAction, PlanningProblem, fact


def atom(expr, bindings=None):
    if not isinstance(expr, tuple) or not expr or any(not isinstance(x,str) for x in expr):
        raise ValueError(f'Not an atomic predicate: {expr}')
    if expr[0] in {'not','or','forall','exists','when','=','imply'}:
        raise ValueError(f'Unsupported predicate: {expr[0]}')
    bindings=bindings or {}
    return fact(expr[0],*(bindings.get(x,x) for x in expr[1:]))


def literals(expr,bindings=None,allow_delete=False):
    exprs=expr[1:] if expr and expr[0]=='and' else (expr,)
    positive,negative=set(),set()
    for e in exprs:
        if e[0]=='not':
            if not allow_delete or len(e)!=2:
                raise ValueError('Negative preconditions/goals are unsupported')
            negative.add(atom(e[1],bindings))
        else:
            positive.add(atom(e,bindings))
    return frozenset(positive),frozenset(negative)


@dataclass
class StripsAdapter:
    problem: PlanningProblem
    schemas: dict
    objects: frozenset
    predicates: dict

    @classmethod
    def parse(cls, domain_text, problem_text):
        d=parse_sexpression(domain_text.lower());p=parse_sexpression(problem_text.lower())
        if d[0]!='define' or p[0]!='define':
            raise ValueError('Expected define')
        schemas={};predicates={};domain_name=None
        for section in d[1:]:
            tag=section[0]
            if tag=='domain':domain_name=section[1]
            elif tag==':requirements':
                if set(section[1:])!={':strips'}:raise ValueError('Only :strips supported')
            elif tag==':predicates':predicates={a[0]:len(a)-1 for a in section[1:]}
            elif tag==':action':
                fields=dict(zip(section[2::2],section[3::2]))
                if set(fields)!={':parameters',':precondition',':effect'}:raise ValueError('Unknown action field')
                params=fields[':parameters']
                if any(not x.startswith('?') for x in params) or len(set(params))!=len(params):raise ValueError('Typed/duplicate parameters unsupported')
                literals(fields[':precondition']);literals(fields[':effect'],allow_delete=True)
                schemas[section[1]]=fields
            else:raise ValueError(f'Unsupported domain section {tag}')
        sections={s[0]:s[1:] for s in p[1:]}
        if set(sections)!={'problem',':domain',':objects',':init',':goal'}:raise ValueError('Unsupported problem section')
        if sections[':domain']!=(domain_name,):raise ValueError('Domain mismatch')
        objects=frozenset(sections[':objects'])
        if '-' in objects:raise ValueError('Typed objects unsupported')
        initial=frozenset(atom(e) for e in sections[':init'])
        goal,_=literals(sections[':goal'][0])
        obj=cls(PlanningProblem(sections['problem'][0],initial,goal,()),schemas,objects,predicates)
        for f in initial|goal:obj.check_fact(f)
        return obj

    def check_fact(self,p):
        if self.predicates.get(p.name)!=len(p.args) or any(a not in self.objects for a in p.args):
            raise ValueError(f'Unknown/ill-typed atom {p}')

    def action(self,text):
        expr=parse_sexpression(text.lower())
        if not isinstance(expr,tuple) or not expr:raise ValueError('Invalid action syntax')
        name,*args=expr
        if name not in self.schemas or any(x not in self.objects for x in args):raise ValueError('Unknown action/object')
        schema=self.schemas[name];params=schema[':parameters']
        if len(args)!=len(params):raise ValueError('Action arity mismatch')
        binding=dict(zip(params,args));pre,_=literals(schema[':precondition'],binding)
        add,delete=literals(schema[':effect'],binding,True)
        for f in pre|add|delete:self.check_fact(f)
        return GroundAction('('+ ' '.join(expr)+')',name,tuple(args),pre,add,delete)
