"""Bounded STATIC CAD numeric expression analysis, NOT downloaded-code execution.

We interpret only literal/assigned scalar numbers and +,-,*,/,** arithmetic
under strict depth, node-count, magnitude, finite and exponent limits.
Never evaluate function calls, attributes, imports, loops, comprehensions,
conditions, object methods, or arbitrary Python.
"""
from __future__ import annotations

import ast
import math
import re

from zero_to_cad_ingest import canonical

MAX_SOURCE=200_000
MAX_ARITH_NODES=256
MAX_ASSIGNMENTS=128
MAX_CALLS=128
MAX_MAGNITUDE=1e7

def pure_numeric(node:ast.AST,variables:dict[str,float],
                 depth:int=0,counter:list[int]|None=None)->float|None:
    if counter is None:counter=[0]
    counter[0]+=1
    if depth>12 or counter[0]>MAX_ARITH_NODES:
        return None
    if isinstance(node,ast.Constant) and type(node.value) in (int,float):
        result=float(node.value)
    elif isinstance(node,ast.Name):
        return variables.get(node.id)
    elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
        value=pure_numeric(node.operand,variables,depth+1,counter)
        if value is None:return None
        result=-value if isinstance(node.op,ast.USub) else value
    elif isinstance(node,ast.BinOp):
        left=pure_numeric(node.left,variables,depth+1,counter)
        right=pure_numeric(node.right,variables,depth+1,counter)
        if left is None or right is None:return None
        try:
            if isinstance(node.op,ast.Add):result=left+right
            elif isinstance(node.op,ast.Sub):result=left-right
            elif isinstance(node.op,ast.Mult):result=left*right
            elif isinstance(node.op,ast.Div):
                if abs(right)<1e-12:return None
                result=left/right
            elif isinstance(node.op,ast.Pow):
                if abs(right)>4 or left==0 and right<0:return None
                result=left**right
            else:return None
        except (OverflowError,ZeroDivisionError,ValueError):
            return None
    else:
        # This rejects ALL user-defined calls, subscripts, dynamic strings,
        # object attributes, and potential side-effect expressions.
        return None
    if isinstance(result,complex) or not math.isfinite(result) or abs(result)>MAX_MAGNITUDE:
        return None
    return float(result)

class CallCollector(ast.NodeVisitor):
    def __init__(self,variables:dict[str,float]):
        self.variables=variables
        self.calls=[]
    def visit_Call(self,node:ast.Call):
        self.generic_visit(node)
        if len(self.calls)>=MAX_CALLS or not isinstance(node.func,ast.Attribute):
            return
        operation=canonical(node.func.attr)
        if operation is None:
            return
        args=[]
        for item in [*node.args[:8],*[x.value for x in node.keywords[:8]]]:
            if isinstance(item,(ast.List,ast.Tuple)) and len(item.elts)<=8:
                candidates=item.elts
            else:
                candidates=(item,)
            for part in candidates:
                v=pure_numeric(part,self.variables)
                if v is not None:args.append(v)
        self.calls.append((operation,args[:12]))

def collect_static_cad_numbers(source:object)->tuple[list[tuple[str,list[float]]],dict]:
    if isinstance(source,bytes):
        source=source.decode("utf-8",errors="replace")
    if not isinstance(source,str) or not 0<len(source)<=MAX_SOURCE:
        return [],{"safe_resolved_assignments":0,"rejected_source":True}
    try:
        module=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):
        return [],{"safe_resolved_assignments":0,"rejected_source":True}
    variables={}
    # ONLY simple module-level numeric assignments. No source statements
    # are executed. Assigning an unknown expression invalidates old values.
    for item in module.body:
        if len(variables)>=MAX_ASSIGNMENTS:break
        if isinstance(item,ast.Assign) and len(item.targets)==1 and isinstance(item.targets[0],ast.Name):
            name=item.targets[0].id
            rhs=item.value
        elif isinstance(item,ast.AnnAssign) and isinstance(item.target,ast.Name):
            name=item.target.id
            rhs=item.value
        else:
            continue
        if (not isinstance(name,str) or not re.fullmatch("[A-Za-z_][A-Za-z_0-9]{0,79}",name)
            or name.startswith("__") or rhs is None):
            continue
        value=pure_numeric(rhs,variables)
        if value is None:
            variables.pop(name,None)
        else:
            variables[name]=value
    visitor=CallCollector(variables)
    visitor.visit(module)
    return visitor.calls,{
        "safe_resolved_assignments":len(variables),
        "CAD_calls_scanned":len(visitor.calls),
        "untrusted_code_executed":False,
        "accepted_operations_only":True
    }
