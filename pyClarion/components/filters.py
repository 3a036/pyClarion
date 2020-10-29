"""Tools for filtering inputs and outputs of propagators."""


__all__ = ["GatedA", "FilteredT", "FilteringRelay"]


from pyClarion.base.symbols import Symbol, ConstructType, feature
from pyClarion.components.propagators import (
    PropagatorA, PropagatorB, PropagatorT
)
from pyClarion.utils.funcs import (
    scale_strengths, multiplicative_filter, group_by_dims, invert_strengths, 
    eye, inv
)

from itertools import product
from typing import NamedTuple, Tuple, Hashable, Union
import pprint


class GatedA(PropagatorA):
    """Gates output of an activation propagator."""
    
    tfms = {"eye": eye, "inv": inv}

    def __init__(
        self, 
        base: PropagatorA, 
        gate: Symbol,
        tfm: str = "eye"
    ) -> None:

        self.base = base
        self.gate = gate
        self.tfm = self.tfms[tfm]

    def expects(self, construct):

        return construct == self.gate or self.base.expects(construct)

    def call(self, construct, inputs):

        weight = inputs.pop(self.gate)[construct]
        base_strengths = self.base.call(construct, inputs)
        output = scale_strengths(
            weight=self.tfm(weight), 
            strengths=base_strengths
        )

        return output


class FilteredT(PropagatorT):
    """Filters input to a terminus."""
    
    def __init__(
        self, 
        base: PropagatorT, 
        filter: Symbol, 
        invert_weights: bool = True
    ) -> None:

        self.base = base
        self.filter = filter
        self.invert_weights = invert_weights

    def expects(self, construct):

        return construct == self.filter or self.base.expects(construct)

    def call(self, construct, inputs):

        weights = inputs.pop(self.filter)
        
        if self.invert_weights:
            weights = invert_strengths(weights)
            fdefault=1.0
        else:
            fdefault=0.0

        filtered_inputs = {
            source: multiplicative_filter(
                weights=weights, strengths=strengths, fdefault=fdefault
                )
            for source, strengths in inputs.items()
        }
        output = self.base.call(construct, filtered_inputs)

        return output


class FilteringRelay(PropagatorB):
    """Computes gate and filter settings as directed by a controller."""
    
    class Interface(NamedTuple):
        """
        Control interface for filtering relay.
        
        Defines mapping for assignment of filter weights to cilent constructs 
        based on controller instructions.

        :param clients: Tuple containing either symbols naming individual 
            clients or a tuple of construct symbols for groups. It is expected 
            that len(clients) == len(tags).
        :param tags: Tuple listing control dimension labels. The i-th tag 
        controls the strength assigned to the i-th entry in param `symbols` 
        based on the value of the dimension (tag, 0).
        :param vals: A tuple defining feature values corresponding to each 
            strength degree. The i-th value is taken to correspond to a filter 
            weighting level of i / (len(vals) - 1).
        """

        clients: Tuple[Union[Symbol, Tuple[Symbol, ...]], ...]
        tags: Tuple[Hashable, ...]
        vals: Tuple[Hashable, ...]

        @property
        def features(self):
            """Filter setting features."""

            dvpairs = product(self.tags, self.vals)

            return tuple(feature(tag, val, 0) for tag, val in dvpairs)

        @property
        def dims(self):
            """
            Dimensions associated with self.
            
            Has form (tag, 0) for each tag in self.tags, returned in order.
            """

            return tuple((tag, 0) for tag in self.tags)

        @property
        def defaults(self):
            """Features for default filter settings."""
            
            return tuple(feature(tag, self.vals[0], 0) for tag in self.tags)

    class InterfaceError(Exception):
        """Raised when a passed a malformed interface."""
        pass

    @classmethod
    def _validate_interface(cls, interface: Interface) -> None:

        if len(interface.clients) != len(interface.tags):
            raise cls.InterfaceError(
                "Number of dims must be equal to number of entries in symbols."
            )
        if len(interface.vals) < 2:
            raise cls.InterfaceError("Vals must define at least 2 values.")
        if len(interface.vals) != len(set(interface.vals)):
            raise cls.InterfaceError("Vals may not contain duplicates.")

    @staticmethod
    def _validate_controller(controller):

        subsystem, terminus = controller
        if subsystem.ctype not in ConstructType.subsystem:
            raise ValueError(
                "Arg `controller` must name a subsystem at index 0."
            )
        if terminus.ctype not in ConstructType.terminus:
            raise ValueError(
                "Arg `controller` must name a terminus at index 1."
            )

    def __init__(
        self,
        controller: Tuple[Symbol, Symbol],
        interface: Interface
    ) -> None:

        self._validate_controller(controller)
        self._validate_interface(interface)

        super().__init__()
        self.controller = controller
        self.interface = interface

    def expects(self, construct):

        return construct == self.controller[0]

    def _parse_commands(self, inputs):

        subsystem, terminus = self.controller
        data = inputs[subsystem].get(terminus, frozenset())

        # Filter irrelevant feature symbols
        cmd_set = set(
            f for f in data if 
            f in self.interface.features and 
            f.tag in self.interface.tags and
            f.lag == 0
        )

        groups = group_by_dims(features=cmd_set)
        cmds = {}
        for k, g in groups.items():
            if len(g) > 1:
                raise ValueError(
                "Multiple commands for dim '{}' in FilterBus.".format(k)
            )
            cmds[k] = g[0]

        return cmds

    def call(self, construct, inputs):
        
        d, cmds = {}, self._parse_commands(inputs)
        for i, tag in enumerate(self.interface.tags):
            cmd = cmds.get((tag, 0), self.interface.defaults[i])
            level = self.interface.vals.index(cmd.val)
            strength = level / (len(self.interface.vals) - 1)
            entry = self.interface.clients[i]
            if isinstance(entry, tuple): # entry of type Tuple[Symbol, ...]
                for client in entry:
                    d[client] = strength
            else: # entry of type Symbol
                d[entry] = strength

        return d
