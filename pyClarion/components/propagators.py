"""Provides some basic propagators for building pyClarion agents."""


__all__ = [
    "MaxNodes", "Repeater", "Lag", "ThresholdSelector", "ActionSelector", 
    "BoltzmannSelector", "Constants", "Stimulus"
]


from ..base import ConstructType, Symbol, Propagator, chunk, feature
from ..base import numdicts as nd

from typing import (
    Tuple, Mapping, Set, NamedTuple, FrozenSet, Optional, Union, Dict, 
    Sequence, Container
)
from typing import Iterable, Any
from copy import copy


########################
### Node Propagators ###
########################


class MaxNodes(Propagator):
    """Computes the maximum recommended activation for each node in a pool."""

    _serves = ConstructType.nodes
    _ctype_map = {
        ConstructType.features: ConstructType.feature, 
        ConstructType.chunks: ConstructType.chunk
    }

    def __init__(self, sources: Container[Symbol]):

        self.sources = sources

    def expects(self, construct):

        return construct in self.sources

    def call(self, inputs):

        d = nd.NumDict()
        for strengths in inputs.values():
            d |= strengths
        d.filter(self._filter)

        return d

    def _filter(self, f):

        return f.ctype in self._ctype_map[self.client.ctype]


########################
### Flow Propagators ###
########################


class Repeater(Propagator):
    """Copies the output of a single source construct."""

    _serves = (
        ConstructType.flow_in | ConstructType.flow_h | ConstructType.buffer
    )

    def __init__(self, source: Symbol) -> None:

        self.source = source

    def expects(self, construct):

        return construct == self.source

    def call(self, inputs):

        return nd.NumDict(inputs[self.source])


class Lag(Propagator):
    """Lags strengths for given set of features."""

    _serves = ConstructType.flow_in | ConstructType.flow_bb

    def __init__(self, source: Symbol, max_lag=1):
        """
        Initialize a new `Lag` propagator.

        :param source: Pool of features from which to computed lagged strengths.
        :param max_lag: Do not compute lags beyond this value.
        """

        if source.ctype not in ConstructType.features:
            raise ValueError("Expected construct type to be 'features'.")

        self.source = source
        self.max_lag = max_lag

    def expects(self, construct: Symbol):

        return construct == self.source

    def call(self, inputs):

        d = nd.NumDict(inputs[self.source])
        d = nd.transform_keys(d, self._lag)
        d.filter(self._filter)

        return d

    def _filter(self, f):

        return f.ctype in ConstructType.feature and f.lag <= self.max_lag

    @staticmethod
    def _lag(f):
        
        return feature(f.tag, f.val, f.lag + 1)

############################
### Terminus Propagators ###
############################


class ThresholdSelector(Propagator):
    """
    Propagator for extracting nodes above a thershold.
    
    Targets feature nodes by default.
    """

    _serves = ConstructType.terminus

    def __init__(self, source: Symbol, threshold: float = 0.85):

        self.source = source
        self.threshold = threshold
        
    def expects(self, construct: Symbol):

        return construct == self.source

    def call(self, inputs):

        d = nd.NumDict(inputs[self.source])

        return nd.threshold(d, self.threshold) 


class BoltzmannSelector(Propagator):
    """Selects a chunk according to a Boltzmann distribution."""

    _serves = ConstructType.terminus

    def __init__(self, source, temperature=0.01, threshold=0.25):
        """
        Initialize a ``BoltzmannSelector`` instance.

        :param temperature: Temperature of the Boltzmann distribution.
        """

        self.source = source
        self.temperature = temperature
        self.threshold = threshold

    def expects(self, construct: Symbol):

        return construct == self.source

    def call(self, inputs):
        """Select actionable chunks for execution. 
        
        Selection probabilities vary with chunk strengths according to a 
        Boltzmann distribution.
        """

        strengths = nd.NumDict(inputs[self.source])
        thresholded = nd.threshold(strengths, self.threshold) 
        probabilities = nd.boltzmann(thresholded, self.temperature)
        d = nd.draw(probabilities, 1)

        return d


class ActionSelector(Propagator):
    """Selects action paramaters according to Boltzmann distributions."""

    _serves = ConstructType.terminus

    def __init__(self, source, client_interface, temperature):
        """
        Initialize an ``ActionSelector`` instance.

        :param dims: Registered action dimensions.
        :param temperature: Temperature of the Boltzmann distribution.
        """

        if source.ctype not in ConstructType.features:
            raise ValueError("Expected source to be of ctype 'features'.")

        # Need to make sure that sparse activation representation doesn't cause 
        # problems. Add self.features to make sure selection is done 
        # consistently? - CSM

        self.source = source
        self.client_interface = client_interface
        self.temperature = temperature

    def expects(self, construct):
        
        return construct == self.source 

    def call(self, inputs):
        """Select actionable chunks for execution. 
        
        Selection probabilities vary with feature strengths according to a 
        Boltzmann distribution. Probabilities for each target dimension are 
        computed separately.
        """

        strengths = inputs[self.source]

        d = nd.NumDict({f: strengths[f] for f in self.client_interface.params})

        for dim, fs in self.client_interface.cmds_by_dims.items():
            ipt = nd.NumDict({f: strengths[f] for f in fs})
            prs = nd.boltzmann(ipt, self.temperature)
            selection = nd.draw(prs, 1)
            d.update(selection)

        return d


##########################
### Buffer Propagators ###
##########################


class Constants(Propagator):
    """
    Outputs a constant activation pattern.
    
    Useful for setting defaults and testing. Provides methods for updating 
    constants through external intervention.
    """

    _serves = ConstructType.basic_construct

    def __init__(self, strengths = None) -> None:

        self.strengths = nd.NumDict(strengths) or nd.NumDict()

    def expects(self, construct: Symbol):

        return False

    def call(self, inputs):
        """Return stored strengths."""

        return self.strengths

    def update_strengths(self, strengths):
        """Update self with contents of dict-like strengths."""

        self.strengths.update(strengths)

    def clear(self) -> None:
        """Clear stored node strengths."""

        self.strengths.clear()


class Stimulus(Propagator):
    """Propagates externally provided stimulus."""

    _serves = ConstructType.buffer

    def __init__(self):

        self.stimulus = nd.NumDict()

    def expects(self, construct: Symbol):

        return False

    def input(self, data):

        self.stimulus.update(data)

    def call(self, inputs):

        d = self.stimulus
        self.stimulus = nd.NumDict()

        return d
