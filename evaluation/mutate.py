"""Small AST mutation generator (standard library only).

Used to estimate how well generated tests detect behavior changes: a mutant
is a copy of the fixed module with one operator or constant altered.
"""
import ast
import copy
import random

_BINOPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add, ast.Div: ast.Mult, ast.FloorDiv: ast.Mult, ast.Mod: ast.Mult}
_COMPARES = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In}
_BOOLOPS = {ast.And: ast.Or, ast.Or: ast.And}


def _candidates(node):
    """Return [(label, in_place_mutator)] for one AST node."""
    found = []
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        new = _BINOPS[type(node.op)]
        found.append((type(node.op).__name__ + '->' + new.__name__, lambda n, new=new: setattr(n, 'op', new())))
    elif isinstance(node, ast.Compare):
        for index, op in enumerate(node.ops):
            if type(op) in _COMPARES:
                new = _COMPARES[type(op)]
                found.append((type(op).__name__ + '->' + new.__name__, lambda n, index=index, new=new: n.ops.__setitem__(index, new())))
    elif isinstance(node, ast.BoolOp) and type(node.op) in _BOOLOPS:
        new = _BOOLOPS[type(node.op)]
        found.append((type(node.op).__name__ + '->' + new.__name__, lambda n, new=new: setattr(n, 'op', new())))
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            found.append((str(node.value) + '->' + str(not node.value), lambda n: setattr(n, 'value', not n.value)))
        elif isinstance(node.value, int):
            found.append((str(node.value) + '->' + str(node.value + 1), lambda n: setattr(n, 'value', n.value + 1)))
    return found


def mutants(source, limit=6, seed=0):
    """Return up to `limit` distinct, compilable mutants of `source`.

    Each item: {'label': str, 'line': int, 'code': str}. Selection is
    deterministic for a given seed so evaluation runs are reproducible.
    """
    tree = ast.parse(source)
    baseline = ast.unparse(tree)
    sites = []
    for index, node in enumerate(ast.walk(tree)):
        for choice, (label, _) in enumerate(_candidates(node)):
            sites.append((index, choice, label, getattr(node, 'lineno', 0)))
    random.Random(seed).shuffle(sites)
    seen = {baseline}
    out = []
    for index, choice, label, line in sites:
        if len(out) >= limit:
            break
        clone = copy.deepcopy(tree)
        node = list(ast.walk(clone))[index]
        _candidates(node)[choice][1](node)
        code = ast.unparse(clone)
        if code in seen:
            continue
        try:
            compile(code, '<mutant>', 'exec')
        except (SyntaxError, ValueError):
            continue
        seen.add(code)
        out.append({'label': label, 'line': line, 'code': code})
    return out
