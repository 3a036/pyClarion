'''
This module provides constructs for modeling activation flows in pyClarion.

Usage
=====

The main export of this module is the ``Channel`` class. A pyClarion ``Channel`` 
is a callable object that receives a single ``ActivationPacket`` instance as 
input and outputs a single ``ActivationPacket`` instance in response.

``Channel`` objects may be used to capture activation flows in many ways, at 
multiple levels of granularity. The role of the ``Channel`` class is to provide 
implementations of various activation flows with a uniform interface while 
leaving authors free to determine as many implementation details as possible.

An important point to note is that ``Channel`` objects are responsible only for 
implementing an activation flow. They are not responsible for implementing or 
handling learning. Learning is the responsibility of other constructs.

Instantiation
-------------

The ``Channel`` class is an abstract class. 

>>> Channel()
Traceback (most recent call last):
    ...
TypeError: Can't instantiate abstract class Channel with abstract methods __call__

To define a concrete ``Channel``, one must provide a ``__call__`` method with 
an appropriate signature.

>>> class MyPacket(ActivationPacket):
...     def default_activation(self, key):
...         return 0.0
... 
>>> class MyChannel(Channel):
...     """An activation channel that outputs an empty MyPacket instance."""
...     def __call__(self, input_map : ActivationPacket) -> MyPacket:
...         return MyPacket() 
... 
>>> MyChannel()
<__main__.MyChannel object at ...>

Channel Sub-Types
-----------------

``Channel`` subclasses are expected to extend input types and restrict output 
types, in keeping with the Liskov principle. In practice, the input type is 
generally expected to be left unchanged, and the output type is expected be 
restricted so as to reflect the type of processing that occurred.

>>> class MyTopDownPacket(TopDownPacket, MyPacket):
...     pass
... 
>>> class MyTopDownChannel(TopDown):
...     """A top-down channel that outputs an empty MyTopDownPacket instance."""
...     def __call__(self, input_map : ActivationPacket) -> MyTopDownPacket:
...         return MyTopDownPacket() 
... 

Several abstract base ``Channel`` types are defined in this module in order to 
facilitate definition and identification of ``Channel`` types fulfilling 
various roles within Clarion theory.

Use Cases
---------

The simplest use case for a ``Channel`` object is to statically transform 
activation packets.

>>> from pyClarion.base.node import Node
>>> class ScaledPacket(MyPacket):
...     pass
... 
>>> class MultiplierChannel(Channel):
... 
...     def __init__(self, multiplier):
...         self.multiplier = multiplier
... 
...     def __call__(self, input_map):
...         output = ScaledPacket()
...         for n in input_map:
...             output[n] = input_map[n] * self.multiplier
...         return output
... 
>>> n1, n2 = Node(), Node()
>>> input_activations = MyPacket({n1 : 0.2, n2 : 0.4})
>>> channel = MultiplierChannel(2)
>>> channel(input_activations) == MyPacket({n1 : 0.4, n2 : 0.8})
True

A much more interesting use case of ``Channel`` is implementing knowledge-based
processing of the input activation packet.

>>> from pyClarion.base.node import Microfeature, Chunk
>>> class MyTopLevelPacket(TopLevelPacket, MyPacket):
...     pass
... 
>>> class MyAssociativeNetwork(TopLevel):
... 
...     def __init__(
...         self, association_matrix : T.Dict[Node, T.Dict[Node, float]]
...     ) -> None:
...         """Initialize an associative network.
... 
...         :param association_matrix: A dict that maps conclusion chunks to 
...         dicts mapping their condition chunks to their respective weights.
...         """
...         self.assoc = association_matrix
... 
...     def __call__(self, input_map : ActivationPacket) -> MyTopLevelPacket:
...         output = MyTopLevelPacket()
...         for conclusion_chunk in self.assoc:
...             output[conclusion_chunk] = 0.0
...             for condition_chunk in self.assoc[conclusion_chunk]:
...                 output[conclusion_chunk] += (
...                         input_map[condition_chunk] *
...                         self.assoc[conclusion_chunk][condition_chunk]
...                 )
...         return output
>>> ch1, ch2, ch3 = Chunk('BLOOD ORANGE'), Chunk('RED'), Chunk('YELLOW')
>>> # Throw in some Microfeatures to see if MyAssociativeNetwork gets confused
>>> mf1, mf2 = Microfeature('color', 'red'), Microfeature('color', 'orange')
>>> association_matrix = {
...     ch1 : {ch1 : 1.0, ch2 : 0.4, ch3 : 0.2},
...     ch2 : {ch1 : 0.4, ch2 : 1.0, ch3 : 0.1},
...     ch3 : {ch1 : 0.2, ch2 : 0.1, ch3 : 1.0}    
... }
>>> channel = MyAssociativeNetwork(association_matrix)
>>> input_map = MyPacket({ch1 : 1.0, mf1: 0.3, mf2 : 0.2})
>>> channel(input_map) == {ch1 : 1.0, ch2 : 0.4, ch3 : 0.2}
True

``Channel`` instances can be used to wrap efficient implementations of various 
components.

>>> class AmazingDQN(object):
...     def __call__(self, input_map):
...         """This should be truly amazing; but it's just a placeholder."""
...
...         output = dict()
...         for k, v in input_map.items():
...              if isinstance(k, Microfeature):
...                  output[k] = v
...         return output
... 
>>> class MyAmazingDQNPacket(BottomLevelPacket, MyPacket):
...     pass
... 
...
>>> class MyAmazingDQNChannel(BottomLevel):
...     """A wrapper for an AmazingDQN implementation."""
...
...     def __init__(self, amazing_dqn):
...         self.amazing_dqn = amazing_dqn
... 
...     def __call__(self, input_map : ActivationPacket) -> MyAmazingDQNPacket:
...         output = self.amazing_dqn(input_map)
...         return MyAmazingDQNPacket(output)
... 
...     def call_amazing_dqn(self, input_map):
...         return self.amazing_dqn.__call__(input_map)
... 
>>> amazing_dqn = AmazingDQN()
>>> channel = MyAmazingDQNChannel(amazing_dqn)
>>> channel(input_map) == {mf1 : 0.3, mf2 : 0.2}
True

Granularity
-----------

There is no a priori restriction on the granularity of a ``Channel`` object. The 
examples above are rather coarse, often capturing and handling all of the 
knowledge of some component (e.g., an entire associative network). Such an 
architecture may be well-suited for certain use cases, but others may call for 
a more fine-grained implementation such as the one below:

>>> class FineGrainedTopDown(TopDown):
...     """Represents a top-down link between two individual nodes."""
... 
...     def __init__(self, chunk, microfeature, weight):
...         self.chunk = chunk
...         self.microfeature = microfeature
...         self.weight = weight
...
...     def __call__(self, input_map):
...         output = MyTopDownPacket({
...             self.microfeature : input_map[self.chunk] * self.weight
...         })
...         return output
... 

The ``FineGrainedTopDown`` class above defines a top-down link between a single 
chunk and microfeature. 
'''

import abc
import typing as T
from pyClarion.base.activation.packet import (
    ActivationPacket, TopDownPacket, BottomUpPacket, TopLevelPacket, 
    BottomLevelPacket
)


###############
# ABSTRACTION #
###############


class Channel(abc.ABC):
    """An abstract class for capturing activation flows.

    This is a callable class that provides an interface for handling basic 
    activation flows. Outputs are allowed to be empty when such behavior is 
    sensible.
    
    It is assumed that an activation channel will pay attention only to the 
    activations relevant to the computation it implements. For instance, if an 
    activation class implementing a bottom-up connection is passed a bunch of 
    chunk activations, it should simply ignore these and look for matching
    microfeatures. 
    
    If an activation channel is handed an input that does not contain a complete 
    activation dictionary for expected nodes, it should not fail. Instead, it 
    should have a well-defined default behavior for such cases. 

    See module documentation for examples and details.
    """
    
    @abc.abstractmethod
    def __call__(self, input_map : ActivationPacket) -> ActivationPacket:
        """Compute and return activations resulting from an input to this 
        channel.

        .. note::
            Assumptions about missing expected nodes in the input map should 
            be explicitly specified/documented, along with behavior for handling 
            such cases. 

        :param input_map: An activation packet representing the input to this 
            channel.
        """

        pass


######################
# BASE CHANNEL TYPES #
######################


class TopDown(Channel):
    """A base class for top-down activation channels.

    This is an abstract interface for various possible implementations of 
    top-down activation channels. 
    """

    @abc.abstractmethod
    def __call__(self, input_map : ActivationPacket) -> TopDownPacket:
        
        pass


class BottomUp(Channel):
    """A base class for bottom-up activation channels.

    This is an abstract interface for various possible implementations of 
    bottom-up activation channels. 
    """

    @abc.abstractmethod
    def __call__(self, input_map : ActivationPacket) -> BottomUpPacket:

        pass


class TopLevel(Channel):
    """A base class for top-level (i.e., explicit) activation channels.

    This is an abstract interface for various possible implementations of 
    top-level activation channels. 
    """

    @abc.abstractmethod
    def __call__(self, input_map : ActivationPacket) -> TopLevelPacket:
        
        pass


class BottomLevel(Channel):
    """A base class for bottom-level (i.e., implicit) activation channels.

    This is an abstract interface for various possible implementations of 
    bottom-level activation channels.
    """

    @abc.abstractmethod
    def __call__(self, input_map : ActivationPacket) -> BottomLevelPacket:

        pass


################
# TYPE ALIASES #
################


TopChannel = T.Union[TopLevel, BottomUp]
BottomChannel = T.Union[BottomLevel, TopDown]


if __name__=='__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)