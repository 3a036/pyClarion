"""
Tools for representing networks of chunks and microfeatures.

.. warning::
    Highly experimental.

"""

import abc
import enum
from typing import Dict, Union, Set, Tuple, Optional, Hashable, Callable
from pyClarion.base.knowledge import Flow, Node, Chunk, Microfeature
from pyClarion.base.packet import ActivationPacket
from pyClarion.base.channel import Channel
from pyClarion.base.junction import Junction
from pyClarion.base.selector import Selector
from pyClarion.base.effector import Effector
from pyClarion.base.structure import NodeStructure, FlowStructure, ActuatorStructure
from pyClarion.base.connector import NodeConnector, FlowConnector, Actuator


class ActuatorNetwork(object):
    """A network of interconnected nodes and flows linked to an actuator."""

    def __init__(self,
        external_inputs: Dict[Hashable, Callable[..., ActivationPacket]],
        external_outputs: Dict[Hashable, Connector],
        actuator_structure: ActuatorStructure
    ) -> None:

        self._external_inputs = set(external_inputs.keys())
        self._external_outputs = set(external_outputs.keys())
        self._nodes: Dict[Node, NodeConnector] = dict()
        self._flows: Dict[Flow, FlowConnector] = dict()
        self._actuator = Actuator(actuator_structure)

        for connector in external_outputs.values():
            connector.add_link(
                actuator_structure.construct, self.actuator.get_pull_method()
            )

    def add_node(self, node_structure: NodeStructure) -> None:
        
        node = node_structure.construct
        node_connector = NodeConnector(node_structure)
        self.nodes[node] = node_connector
        for identifier, pull_method in self.external_inputs.items():
            node_connector.add_link(identifier, pull_method)
        for flow, flow_connector in self.flows.items():
            flow_connector.add_link(node, node_connector.get_pull_method())
            node_connector.add_link(flow, flow_connector.get_pull_method())
        self.actuator.add_link(node, node_connector.get_pull_method())

    def remove_node(self, node: Node) -> None:
        
        self.actuator.drop_link(node)
        for flow_connector in self.flows.values():
            flow_connector.drop_link(node)
        del self.nodes[node]
            
    def add_flow(self, flow_structure: FlowStructure) -> None:

        flow = flow_structure.construct
        flow_connector = FlowConnector(flow_structure)
        self.flows[flow] = flow_connector
        for node, node_connector in self.nodes.items():
            node_connector.add_link(flow, flow_connector.get_pull_method())
            flow_connector.add_link(node, node_connector.get_pull_method())

    def remove_flow(self, flow: Flow) -> None:
        
        try:
            for node_connector in self.nodes.values():
                node_connector.drop_link(flow)
            del self.flows[flow]
        except KeyError:
            pass

    @property
    def external_inputs(self) -> Set[Hashable]:
        """External inputs to this network"""

        return self._external_inputs

    @property
    def external_outputs(self) -> Set[Hashable]:
        """External inputs to this network"""

        return self._external_inputs

    @property
    def nodes(self) -> Dict[Node, NodeConnector]:
        '''Nodes known to this network.'''
        
        return self._nodes

    @property
    def flows(self) -> Dict[Flow, FlowConnector]:
        '''Activation flows defined for this network.'''

        return self._flows

    @property
    def actuator(self) -> Actuator:
        '''Action selector for this network.'''

        return self._actuator
