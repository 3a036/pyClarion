"""Provides propagators for standard Clarion subsystems."""


__all__ = ["AgentCycle", "CycleS", "ACSCycle", "NACSCycle"]


from pyClarion.base import ConstructType, Symbol, MatchSet, Cycle
from types import MappingProxyType
from typing import Dict, Mapping, Tuple, Container


class AgentCycle(Cycle[Dict[Symbol, float], Mapping[Symbol, float]]):
    """Represents an agent activation cycle."""

    output = ConstructType.buffer | ConstructType.subsystem
    sequence = [
        ConstructType.buffer,
        ConstructType.subsystem
    ]

    def __init__(self):
       
        self.sequence = type(self).sequence

    def expects(self, construct: Symbol):

        return False

    def emit(self, data: Dict[Symbol, float] = None) -> Mapping[Symbol, float]:

        mapping = data if data is not None else dict()
        return MappingProxyType(mapping=mapping)


class CycleS(Cycle[Dict[Symbol, float], Mapping[Symbol, float]]):
    """Represents a subsystem activation cycle."""

    output = ConstructType.nodes | ConstructType.terminus

    def __init__(self, sources: Container[Symbol] = None):

        self.sources = sources if sources is not None else set()
        self.sequence = type(self).sequence

    def expects(self, construct: Symbol):

        return construct in self.sources

    def emit(self, data: Dict[Symbol, float] = None) -> Mapping[Symbol, float]:

        mapping = data if data is not None else dict()
        return MappingProxyType(mapping=mapping)


class ACSCycle(CycleS):

    sequence = [
        ConstructType.flow_in,
        ConstructType.features,
        ConstructType.flow_bt,
        ConstructType.chunks,
        ConstructType.flow_h,
        ConstructType.chunks,
        ConstructType.flow_tb,
        ConstructType.features,
        ConstructType.terminus
    ]


class NACSCycle(CycleS):

    sequence = [
        ConstructType.flow_in,
        ConstructType.chunks,
        ConstructType.flow_tb,
        ConstructType.features,
        ConstructType.flow_h,
        ConstructType.features,
        ConstructType.flow_bt,
        ConstructType.chunks,
        ConstructType.terminus
    ]

