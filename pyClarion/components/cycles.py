"""Provides propagators for standard Clarion subsystems."""


__all__ = ["AgentCycle", "CycleS", "ACSCycle", "NACSCycle"]


from ..base.symbols import ConstructType, Symbol
from ..base.components import Cycle

from types import MappingProxyType
from typing import Dict, Mapping, Tuple, Container, cast


class AgentCycle(Cycle):
    """Represents an agent activation cycle."""

    _serves = ConstructType.agent
    output = ConstructType.buffer | ConstructType.subsystem
    sequence = [
        ConstructType.buffer,
        ConstructType.subsystem
    ]

    def __init__(self):
       
        self.sequence = type(self).sequence

    @staticmethod
    def emit(data=None):

        mapping = data if data is not None else dict()

        return MappingProxyType(mapping=mapping)


class CycleS(Cycle):
    """Represents a subsystem activation cycle."""

    _serves = ConstructType.subsystem
    # NOTE: Should flows be added to output? - Can
    output = ConstructType.nodes | ConstructType.terminus

    def __init__(self):

        self.sequence = type(self).sequence

    @staticmethod
    def emit(data=None):

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

