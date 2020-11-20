"""Definitions for memory constructs, most notably working memory."""


__all__ = ["ParamSet", "Register", "WorkingMemory", "collect_cmd_data"]


from ..base.symbols import (
    ConstructType, Symbol, 
    feature, subsystem, terminus,
    group_by_dims, lag
)
from ..base import numdicts as nd
from ..base.components import (
    Inputs, Propagator, FeatureInterface, FeatureDomain
)

from typing import Callable, Hashable, Tuple, List, Mapping, Collection
from dataclasses import dataclass
from itertools import chain, product
from types import MappingProxyType
import logging


def collect_cmd_data(
    construct: Symbol, 
    inputs: Inputs, 
    controller: Tuple[subsystem, terminus]
) -> nd.FrozenNumDict:
    """
    Extract command data from inputs. 
    
    Logs failure, but does not throw error.
    """

    subsystem, terminus = controller
    try:
        data = inputs[subsystem][terminus]
    except KeyError:
        data = frozenset()
        msg = "Failed data pull from %s in %s."
        logging.warning(msg, controller, construct)
    
    return data


class ParamSet(Propagator):
    """A controlled store of parameters."""

    _serves = ConstructType.buffer

    @dataclass
    class Interface(FeatureInterface):
        """
        Control interface for ParamSet instances.

        :param tag: Tag for ParamSet control dimension.
        :param vals: Control values, a sequence of four values corresponding to 
            the following commands in order: standby, clear, update, 
            clear then update.
        :param clients: Symbols to which parameters are mapped.
        :param func: Function consuming client symbols and outputting 
            corresponding parameter tags. It is okay to map two clients to the 
            same tag. This will couple their values.
        :param param_val: Singleton value to be used in parameter features.
        """

        tag: Hashable
        vals: Tuple[Hashable, Hashable, Hashable, Hashable]
        clients: Collection[Symbol]
        func: Callable[..., Hashable]
        param_val: Hashable

        def _set_interface_properties(self):

            _func, _pval = self.func, self.param_val
            _cmds = (feature(self.tag, val) for val in self.vals)
            _defaults = {feature(self.tag, self.vals[0])}
            _params = (feature(_func(s), _pval) for s in self.clients)

            self._cmds = frozenset(_cmds)
            self._defaults = frozenset(_defaults)
            self._params = frozenset(_params)

        def _validate_data(self):

            _param_tags = set(self.func(s) for s in self.clients)

            if len(set(self.vals)) != len(self.vals):
                raise ValueError("Vals must contain unique values.")
            if self.tag in _param_tags:
                msg = "Tag cannot be equal to an output of func over clients."
                raise ValueError(msg)

    class MetaKnowledge(Propagator):
        """
        Helper propagator for extracting commands & command parameters.
        
        This is useful if the agent should have cognitive access to the 
        commands and parameters passed to a ParamSet instance. 
        """

        _serves = ConstructType.flow_in

        def __init__(
            self, 
            source: Symbol, 
            client_interface: "ParamSet.Interface"
        ):
            
            self.source = source
            self.client_interface = client_interface

        def expects(self, construct):

            return construct == self.source

        def call(self, inputs):

            # Perhaps should transform metaknowledge features to prevent 
            # interference with legit action/param features? This would add an 
            # extra layer of complexity, which I don't like, but it may prove 
            # necessary... - Can

            d = nd.NumDict(inputs[self.source])
            d.filter(self._key)

            return d
        
        def _key(self, construct):

            return (
                isinstance(construct, feature) and
                construct.tag in self.client_interface.tags
            )

    def __init__(
        self, 
        controller: Tuple[subsystem, terminus], 
        interface: Interface,
        forward_commands: bool = True
    ) -> None:

        self.store = nd.NumDict()
        self.flags = nd.NumDict()

        self.controller = controller
        self.interface = interface
        self.forward_commands = forward_commands

    def expects(self, construct):
        
        return construct == self.controller[0]

    def call(self, inputs):
        """
        Update the paramset state and emit outputs.

        Updates are controlled by matching features emitted in the output of 
        self.controller to those defined in self.interface. If no commands are 
        encountered, default/standby behavior will be executed. The default 
        behavior is to maintain the current state.
        """

        data = collect_cmd_data(self.client, inputs, self.controller)
        cmds = self.interface.parse_commands(data)

        if 1 < len(cmds):
            msg = "{} expected only one command, received {}"
            raise ValueError(msg.format(type(self).__name__, len(cmds)))

        for dim, val in cmds.items():
            if val == self.interface.vals[0]:
                pass
            elif val == self.interface.vals[1]:
                self.clear_store()
            elif val in self.interface.vals[2:]:
                if val == self.interface.vals[3]:
                    self.clear_store()
                param_strengths = nd.restrict(data, self.interface.params)
                self.update_store(param_strengths)
            else:
                raise ValueError("Unexpected command value.")

        d = nd.NumDict()
        strengths = nd.transform_keys(self.store, feature.tag.fget)
        for construct in self.interface.clients:
            d[construct] = strengths[self.interface.func(construct)]
        
        if self.forward_commands:
            cmd_strengths = nd.restrict(data, self.interface.cmds)
            lagged_cmd_strengths = nd.transform_keys(cmd_strengths, lag, val=1)
            d |= self.store
            d |= lagged_cmd_strengths

        return d

    def update(self, inputs, output):

        # Flags get cleared on each update. New flags may then be added for the 
        # next cycle.
        self.clear_flags()

    def update_store(self, strengths):
        """
        Update strengths in self.store.
        
        Write op is implemented using the max operation. 
        """

        self.store |= strengths

    def clear_store(self):
        """Clear any nodes stored in self."""

        self.store.clear()

    def update_flags(self, strengths):

        self.flags |= strengths

    def clear_flags(self):

        self.flags.clear()


class Register(Propagator):
    """
    Dynamically stores and activates nodes.
    
    Consists of a node store plus a flag buffer. Stored nodes are persistent, 
    flags are cleared at update time.
    """

    _serves = ConstructType.buffer

    @dataclass
    class Interface(FeatureInterface):
        """
        Control interface for Register instances.
        
        :param tag: Dimension label for controlling write ops to register.
        :param standby: Value corresponding to standby operation.
        :param clear: Value corresponding to clear operation.
        :param channel_map: Tuple pairing values to termini for write 
            operation.
        """

        mapping: Mapping[Hashable, Symbol]
        tag: Hashable
        standby: Hashable
        clear: Hashable

        def _set_interface_properties(self) -> None:
            
            vals = chain((self.standby, self.clear), self.mapping)
            default = feature(self.tag, self.standby)
            
            self._cmds = frozenset(feature(self.tag, val) for val in vals)
            self._defaults = frozenset({default})
            self._params = frozenset()

        def _validate_data(self):
            
            value_set = set(chain((self.standby, self.clear), self.mapping))
            if len(value_set) < len(self.mapping) + 2:
                raise ValueError("Value set may not contain duplicates.") 

    def __init__(
        self, 
        controller: Tuple[subsystem, terminus], 
        source: subsystem,
        interface: Interface,
        forward_commands: bool = False
    ) -> None:
        """
        Initialize a Register instance.

        :param controller: Reference for construct issuing commands to self.
        :param source: Reference for construct from which to pull data.
        :param interface: Defines features for controlling updates to self.
        :param forward_commands: Optional bool indicating whether or not to 
            include received commands in emitted output. False by default. If 
            set to true, received commands are outputted with a lag value of 1.
        """

        self.store = nd.NumDict() 
        self.flags = nd.NumDict()

        self.controller = controller
        self.source = source
        self.interface = interface
        self.forward_commands = forward_commands

    @property
    def is_empty(self):
        """True iff no nodes are stored in self."""

        return len(self.store) == 0

    def expects(self, construct):
        
        ctl_subsystem, src_subsystem = self.controller[0], self.source

        return construct == ctl_subsystem or construct == src_subsystem

    def call(self, inputs):
        """
        Update the register state and emit the current register output.

        Updates are controlled by matching features emitted in the output of 
        self.controller to those defined in self.interface. If no commands are 
        encountered, default/standby behavior will be executed. The default 
        behavior is to maintain the current memory state.
        """

        data = collect_cmd_data(self.client, inputs, self.controller)
        cmds = self.interface.parse_commands(data)

        if 1 < len(cmds):
            msg = "{} expected only one command, received {}"
            raise ValueError(msg.format(type(self).__name__, len(cmds)))

        for dim, val in cmds.items():
            if val == self.interface.standby:
                pass
            elif val == self.interface.clear:
                self.clear_store()
            elif val in self.interface.mapping: 
                channel = self.interface.mapping[val]
                self.clear_store()
                self.update_store(inputs[self.source][channel])

        d = nd.NumDict(self.store)

        d |= self.flags

        if self.forward_commands:
            cmd_strengths = nd.restrict(data, self.interface.cmds)
            lagged_cmd_strengths = nd.transform_keys(cmd_strengths, lag, val=1)
            d |= lagged_cmd_strengths

        return nd.NumDict(d)

    def update(self, inputs, output):
        """
        Clear the register flag buffer.
        
        For richer update/learning behaviour, add updaters to client construct.
        """

        self.clear_flags()

    def update_store(self, strengths):
        """
        Update strengths in self.store.
        
        Write op is implemented using the max operation. 
        """

        self.store |= strengths

    def clear_store(self):
        """Clear any nodes stored in self."""

        self.store.clear()

    def update_flags(self, strengths):

        self.flags |= strengths

    def clear_flags(self):

        self.flags.clear()


class WorkingMemory(Propagator):
    """
    A simple working memory mechanism.

    The mechanism follows a slot-based storage and control architecture. It 
    supports writing data to slots, clearing slots, excluding slots from the 
    output and resetting the memory state. 

    This class defines the basic datastructure and memory update method. For 
    minimality, it does not report mechanism states (e.g., which slots are 
    filled).
    """

    # TODO: In the future, WorkingMemory should return a special flag feature 
    # if an empty slot is opened to signify retrieval failure from that slot. 
    # This requires extensions to the interface. - Can

    _serves = ConstructType.buffer

    @dataclass
    class Interface(FeatureInterface):
        """
        Control interface for WorkingMemory propagator.

        :param slots: Number of working memory slots.
        :param prefix: Marker for identifying this particular set of control 
            features.
        :param write_marker: Marker for controlling WM slot write operations.
        :param read_marker: Marker for controlling WM slot read operations.
        :param reset_marker: Marker for controlling global WM state resets.
        :param standby: Value for standby action on writing operations.
        :param clear: Value for clear action on writing operations.
        :param mapping: Mapping pairing a write operation value with a 
            terminus from the source subsystem. Signals WM to write contents of 
            terminus to a slot.
        :param reset_vals: Global reset control values. First value corresponds 
            to standby. Second value corresponds to reset initiation.
        :param read_vals: Read operation control values. First value 
            corresponds to standby (i.e., no read), second value to read action. 
        """

        slots: int
        prefix: Hashable
        write_marker: Hashable
        read_marker: Hashable
        reset_marker: Hashable
        standby: Hashable
        clear: Hashable
        mapping: Mapping[Hashable, Symbol]
        reset_vals: Tuple[Hashable, Hashable]
        read_vals: Tuple[Hashable, Hashable]

        @property
        def write_tags(self):

            return self._write_tags

        @property
        def read_tags(self):

            return self._read_tags

        @property
        def reset_tag(self):

            return self._reset_tag

        @property
        def write_dims(self):

            return self._write_dims

        @property
        def read_dims(self):

            return self._read_dims

        @property
        def reset_dim(self):

            return self._reset_dim

        def _set_interface_properties(self) -> None:
            
            slots, pre = self.slots, self.prefix
            w, r, re = self.write_marker, self.read_marker, self.reset_marker

            _w_tags = tuple((pre, w, i) for i in range(slots))
            _r_tags = tuple((pre, r, i) for i in range(slots))
            _re_tag = (pre, re)

            _w_vals = set(chain((self.standby, self.clear), self.mapping))
            _r_vals = self.read_vals
            _re_vals = self.reset_vals

            _w_d_val = self.standby
            _r_d_val = _r_vals[0]
            _re_d_val = _re_vals[0]

            _w_gen = ((tag, val) for tag, val in product(_w_tags, _w_vals))
            _r_gen = ((tag, val) for tag, val in product(_r_tags, _r_vals))
            _re_gen = ((_re_tag, val) for val in _re_vals)

            _w_dgen = ((tag, val) for tag, val in product(_w_tags, _w_vals))
            _r_dgen = ((tag, val) for tag, val in product(_r_tags, _r_vals))
            _re_dgen = ((_re_tag, val) for val in _re_vals)

            _w_cmds = frozenset(feature(tag, val) for tag, val in _w_gen)
            _r_cmds = frozenset(feature(tag, val) for tag, val in _r_gen)
            _re_cmds = frozenset(feature(tag, val) for tag, val in _re_gen)

            _w_defaults = frozenset(feature(tag, _w_d_val) for tag in _w_tags)
            _r_defaults = frozenset(feature(tag, _r_d_val) for tag in _r_tags)
            _re_defaults = frozenset({feature(_re_tag, _re_d_val)})
            _defaults = _w_defaults | _r_defaults | _re_defaults

            self._write_tags = _w_tags
            self._read_tags = _r_tags
            self._reset_tag = _re_tag

            self._write_dims = tuple(sorted(set(f.dim for f in _w_cmds)))
            self._read_dims = tuple(sorted(set(f.dim for f in _r_cmds)))
            self._reset_dim = (_re_tag, 0)

            self._cmds = _w_cmds | _r_cmds | _re_cmds
            self._defaults = _defaults
            self._params = frozenset()

        def _validate_data(self):
            
            markers = (self.write_marker, self.read_marker, self.reset_marker)
            w_vals = set(chain((self.standby, self.clear), self.mapping))
            
            if len(set(markers)) < 3:
                raise ValueError("Marker arguments must be mutually distinct.")
            if len(set(w_vals)) < len(self.mapping) + 2:
                raise ValueError("Write vals may not contain duplicates.")
            if len(set(self.read_vals)) < len(self.read_vals):
                raise ValueError("Read vals may not contain duplicates.")
            if len(set(self.reset_vals)) < len(self.reset_vals):
                raise ValueError("Reset vals may not contain duplicates.")

    def __init__(
        self,
        controller: Tuple[subsystem, terminus],
        source: subsystem,
        interface: Interface,
        forward_commands: bool = False
    ) -> None:
        """
        Initialize a new WorkingMemory instance.

        :param controller: Reference for construct issuing commands to self.
        :param source: Reference for construct from which to pull data.
        :param interface: Defines features for controlling updates to self.
        :param forward_commands: Optional bool indicating whether or not to 
            include received commands in emitted output. False by default. If 
            set to true, received commands are outputted with a lag value of 1.
        """

        self.controller = controller
        self.source = source
        self.interface = interface
        self.forward_commands = forward_commands

        self.flags = nd.NumDict()
        self.gate = nd.NumDict()
        self.cells = tuple(
            Register(
                controller=controller,
                source=source,
                interface=Register.Interface(
                    mapping=interface.mapping,
                    tag=tag,
                    standby=interface.standby,
                    clear=interface.clear
                ),
            forward_commands=forward_commands
            )
            for tag in interface.write_tags
        )

    def entrust(self, construct):

        for cell in self.cells:
            cell.entrust(construct)
        super().entrust(construct)

    def expects(self, construct):
        
        ctl_subsystem, src_subsystem = self.controller[0], self.source

        return construct in (ctl_subsystem, src_subsystem)

    def call(self, inputs):
        """
        Update the memory state and emit output activations.

        Updates are controlled by matching features emitted in the output of 
        self.controller to those defined in self.interface. If no commands are 
        encountered, default/standby behavior will be executed. The default 
        behavior is to maintain the current memory state.
        
        The update cycle processes global resets first, slot contents are 
        updated next. As a result, it is possible to clear the memory globally 
        and populate it with new information (e.g., in the service of a new 
        goal) in one single update. 
        """

        data = collect_cmd_data(self.client, inputs, self.controller)
        cmds = self.interface.parse_commands(data)

        # global wm reset
        if cmds[self.interface.reset_dim] == self.interface.reset_vals[1]:
            self.reset_cells()

        d = nd.NumDict()
        for cell, dim in zip(self.cells, self.interface.read_dims):
            cell_strengths = cell.call(inputs)
            if cmds[dim] == self.interface.read_vals[1]:
                d |= cell_strengths

        d |= self.flags
        
        if self.forward_commands:
            cmd_strengths = nd.restrict(data, self.interface.cmds)
            lagged_cmd_strengths = nd.transform_keys(cmd_strengths, lag, val=1)
            d |= lagged_cmd_strengths
        
        return d

    def update(self, inputs, output):
        """
        Clear the working memory flag buffer.
        
        For richer update/learning behaviour, add updaters to client construct.
        """

        self.clear_flags()

    def reset_cells(self):
        """
        Reset memory state.
        
        Clears all memory slots and closes all switches.
        """

        for cell in self.cells:
            cell.clear_store()

    def update_flags(self, strengths):

        self.flags |= strengths

    def clear_flags(self):

        self.flags.clear()
