"""Provides abstract classes for defining forward propagation cycles."""


__all__ = ["Propagator", "PropagatorA", "PropagatorD", "PropagatorB"]


from pyClarion.base.symbols import ConstructSymbol
from pyClarion.base.packets import (
    ActivationPacket, DecisionPacket, SubsystemPacket
)
from typing import TypeVar, Generic, Mapping, Callable, Any, Mapping, Tuple, Set
from abc import abstractmethod


Dt = TypeVar('Dt') # type variable for inputs to processes
It = TypeVar('It', contravariant=True) # type variable for propagator inputs
Xt = TypeVar('Xt') # type variable for intermediate stage 
                   # Should Xt be covariant/contravariant? - Can 
Ot = TypeVar('Ot', covariant=True) # type variable for propagator outputs

PullFuncs = Mapping[ConstructSymbol, Callable[[], Dt]]
Inputs = Mapping[ConstructSymbol, Dt]
APData = Mapping[ConstructSymbol, Any] # type for ActivationPacket init
DPData = Tuple[APData, Set[ConstructSymbol]] # type for DecisionPacket init


class Propagator(Generic[It, Xt, Ot]):
    """
    Abstract class for propagating strengths, decisions, and states.

    Propagator subclasses and instances define how constructs process inputs 
    and set outputs.
    """

    # Would it be worth implenting this as a Protocol? - Can

    def __call__(
        self, construct: ConstructSymbol, inputs: PullFuncs[It], **kwds: Any
    ) -> Ot:
        """
        Execute construct's forward propagation cycle.

        Wrapper for self.call().

        Pulls data from inputs constructs, delegates processing to self.call(),
        and wraps result in appropriate Packet instance.
        """

        inputs_ = {source: pull_func() for source, pull_func in inputs.items()}
        intermediate: Xt = self.call(construct, inputs_, **kwds)
        
        return self.make_packet(intermediate)

    @abstractmethod
    def make_packet(self, data: Xt = None) -> Ot:
        pass

    @abstractmethod
    def call(
        self, construct: ConstructSymbol, inputs: Inputs[It], **kwds: Any
    ) -> Xt:
        """
        Execute construct's forward propagation cycle.

        :param construct: The construct symbol associated with the realizer 
            owning to the propagation callback. 
        :param inputs: A dictionary, mapping construct symbols to Packet 
            instances, specifying input passed to the owning construct by other 
            constructs within the simulation. 
        :param kwargs: Any additional parameters passed to the call to owning 
            construct's propagate() method through the `options` argument. These 
            arguments may be used to contextually modify propagator behavior, 
            pass in external inputs, etc. For ease of debugging and as a 
            precaution against subtle bugs (e.g., failing to set an option due 
            to misspelled keyword argument name) it is recommended that 
            Propagator instances throw errors upon receipt of unexpected 
            keyword arguments.
        """
        pass


class PropagatorA(Propagator[ActivationPacket, APData, ActivationPacket]):
    """
    Represents a propagator for nodes or flows.

    Maps activations to activations.
    """

    def make_packet(self, data: APData = None) -> ActivationPacket:

        data = data if data is not None else dict()
        return ActivationPacket(mapping=data)


class PropagatorD(Propagator[ActivationPacket, DPData, DecisionPacket]):
    """
    Represents a propagator for response selection.

    Maps activations to decisions.
    """

    def make_packet(self, data: DPData = None) -> DecisionPacket:

        mapping, selection = data if data is not None else (dict(), set())
        return DecisionPacket(mapping=mapping, selection=selection)


class PropagatorB(Propagator[SubsystemPacket, APData, ActivationPacket]):
    """
    Represents a propagator for buffers.

    Maps subsystem outputs to activations.
    """
    
    def make_packet(self, data: APData = None) -> ActivationPacket:

        data = data if data is not None else dict()
        return ActivationPacket(mapping=data)
