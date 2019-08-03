from pyClarion.base.symbols import *
from pyClarion.base.packets import *
from pyClarion.components.utils import *
from pyClarion.base.realizers import Proc


class MaxNode(Proc):
    """Simple node returning maximum strength for given construct."""

    def call(self, construct, inputs, **kwargs):

        packets = (pull_func() for pull_func in inputs.values())
        strength = max_strength(construct, packets)
        return ActivationPacket(strengths=strength)


class BoltzmannSelector(Proc):
    """Selects a chunk according to a Boltzmann distribution."""

    def __init__(self, temperature, k=1):
        """
        Initialize a ``BoltzmannSelector`` instance.

        :param temperature: Temperature of the Boltzmann distribution.
        """

        self.temperature = temperature
        self.k = k

    def call(self, construct, inputs, **kwargs):
        """Select actionable chunks for execution. 
        
        Selection probabilities vary with chunk strengths according to a 
        Boltzmann distribution.

        :param strengths: Mapping of node strengths.
        """

        packets = (pull_func() for pull_func in inputs.values())
        strengths = simple_junction(packets)
        probabilities = boltzmann_distribution(strengths, self.temperature)
        selection = select(probabilities, self.k)
        dpacket = DecisionPacket(strengths=probabilities, selection=selection)
        return dpacket


class MappingEffector(object):
    """Links actionable chunks to callbacks."""

    def __init__(self, callbacks = None) -> None:
        """
        Initialize a SimpleEffector instance.

        :param chunk2callback: Mapping from actionable chunks to callbacks.
        """

        self.callbacks = callbacks if callbacks is not None else dict()

    def __call__(self, dpacket) -> None:
        """
        Execute callbacks associated with each chosen chunk.

        :param dpacket: A decision packet.
        """
        
        for chunk in dpacket.selection:
            self.callbacks[chunk].__call__()

    def set_action(self, chunk_, callback):

        self.callbacks[chunk_] = callback


class ConstantSource(Proc):
    """Outputs a stored activation packet."""

    def __init__(self, strengths = None) -> None:

        self.strengths = strengths or dict()

    def call(self, construct, inputs, **kwargs):
        """Return stored strengths."""

        return ActivationPacket(strengths=self.strengths)

    def update(self, strengths):
        """Update self with contents of dict-like strengths."""

        self.strengths = self.strengths.copy()
        self.strengths.update(strengths)

    def clear(self) -> None:
        """Clear stored node strengths."""

        self.strengths = {}


class Stimulus(Proc):

    def call(self, construct, inputs, stimulus=None, **kwargs):

        packet = stimulus or ActivationPacket()
        return packet