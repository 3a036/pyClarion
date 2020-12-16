"""Ops on numerical dictionaries with automdiff support."""


# TODO: GradientOps may not handle defaults correctly! Check and correct. - Can


__all__ = ["log", "exp", "sigmoid", "set_by", "sum_by", "max_by"]


from .numdicts import (
    D, NumDict, MutableNumDict, record_call, register_op, register_grad
)
from .funcs import by

from typing import TypeVar, Union, Callable, Hashable, Any
import math


def log(d: D) -> NumDict:
    """Compute the elementwise natural logarithm of d."""

    return d.log()


def exp(d: D) -> NumDict:
    """Compute the base-e exponential of d."""

    return d.exp()


def sigmoid(d: D) -> NumDict:
    """Apply the logistic function elementwise to d."""

    return 1 / (1 + (-d).exp())


@register_op
def set_by(
    target: D, source: D, *, keyfunc: Callable[..., Hashable]
) -> NumDict:
    """
    Construct a numdict mapping target keys to matching values in source. 
    
    For each key in source, output[key] = source[keyfunc(key)]. Defaults are
    discarded.
    """

    value = NumDict({k: source[keyfunc(k)] for k in target}, None)
    record_call(set_by, value, (target, source), {"keyfunc": keyfunc})

    return value

@register_grad(set_by)
def _grad_set_by(grads, target, source, *, keyfunc):

    return (grads * 0, sum_by(grads, keyfunc=keyfunc))


@register_op
def sum_by(d: D, *, keyfunc: Callable[..., Hashable], **kwds: Any) -> NumDict:
    """
    Sum the values of d grouped by keyfunc.
    
    Maps each l in the range of keyfunc to the sum of all d[k] such that 
    keyfunc(k) is equal to l. See by() for further details.
    """

    value = by(d, sum, keyfunc, **kwds)
    _kwds = {"keyfunc": keyfunc}
    _kwds.update(kwds)
    record_call(sum_by, value, (d,), _kwds)

    return value

@register_grad(sum_by)
def _grad_sum_by(grads, d, *, keyfunc):
    
    return (set_by(d, grads, keyfunc=keyfunc),)


@register_op
def max_by(d: D, *, keyfunc: Callable[..., Hashable], **kwds: Any) -> NumDict:
    """
    Find maximum values in d grouped by keyfunc.
    
    Maps each l in the range of keyfunc to the max of all d[k] such that 
    keyfunc(k) is equal to l. See by() for further details.
    """

    value = by(d, max, keyfunc, **kwds)
    _kwds = {"keyfunc": keyfunc}
    _kwds.update(kwds)
    record_call(max_by, value, (d,), _kwds)

    return value

# TODO: _grad_max_by is not differentiable, should probably be made so. - Can
@register_grad(max_by)
def _grad_max_by(grads, d, *, keyfunc):

    _isclose = math.isclose
    y = max_by(d, keyfunc=keyfunc)
    arg_max = {k for k, v in d.items() if _isclose(v, y[keyfunc(k)])}
    grad_max = NumDict({k: grads[keyfunc(k)] if k in arg_max else 0 for k in d})

    return (grad_max,)
