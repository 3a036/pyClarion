from dataclasses import dataclass
from pyClarion.base.symbols import Node, Flow, Appraisal, Activity, Memory
from pyClarion.base.processors import Channel, Junction, Selector
from pyClarion.base.realizers.abstract import BasicConstructRealizer


class NodeRealizer(BasicConstructRealizer[Node]):

    def __init__(self, construct: Node, junction: Junction) -> None:
        
        super().__init__(construct)
        self.junction: Junction = junction
        self._init_io()

    def do(self) -> None:

        inputs = self.input.pull([self.construct])
        output = self.junction(*inputs)
        self.output.update(output)


class FlowRealizer(BasicConstructRealizer[Flow]):

    def __init__(
        self, construct: Flow, junction: Junction, channel: Channel
    ) -> None:
        
        super().__init__(construct)
        self.junction: Junction = junction
        self.channel: Channel = channel
        self._init_io()

    def do(self):

        inputs = self.input.pull()
        combined = self.junction(*inputs)
        output = self.channel(combined)
        self.output.update(output)


class AppraisalRealizer(BasicConstructRealizer[Appraisal]):

    def __init__(
        self, construct: Appraisal, junction: Junction, selector: Selector
    ) -> None:
        
        super().__init__(construct)
        self.junction: Junction = junction
        self.selector: Selector = selector
        self._init_io()

    def do(self):

        inputs = self.input.pull()
        combined = self.junction(*inputs)
        output = self.selector(combined)
        self.output.update(output)
