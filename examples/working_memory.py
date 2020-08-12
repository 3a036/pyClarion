from pyClarion import *
from typing import cast
import pprint

alice = Structure(
    name=agent("Alice"),
    emitter=AgentCycle(),
    assets=Assets(chunks=Chunks())
)

wmud = WMUpdater(
    source=subsystem("NACS"),
    controller=(subsystem("ACS"), terminus("wm")),
    reset_dim="wm-reset",
    reset_vals={"release": True, "standby": False},
    write_dims=["wm-w0", "wm-w1", "wm-w2", "wm-w3", "wm-w4", "wm-w5", "wm-w6"],
    write_clear="clear",
    write_standby="standby",
    write_channels={
        "retrieve": terminus("retrieval"), 
        "extract": terminus("bl-state")
    },
    switch_dims=["wm-s0", "wm-s1", "wm-s2", "wm-s3", "wm-s4", "wm-s5", "wm-s6"],
    switch_vals={"toggle": True, "standby": False},
    chunks=alice.assets.chunks
)

wm = Construct(
    name=buffer("WM"),
    emitter=WorkingMemory(
        slots=[0, 1, 2, 3, 4, 5, 6],
        dims=("wm-state", "wm-exclude"),
        matches=MatchSet(constructs={subsystem("ACS"), subsystem("NACS")}),
    ),
    updater=wmud
)
alice.add(wm)

wm_defaults = Construct(
    name=buffer("WM-defaults"),
    emitter=ConstantBuffer(strengths={f: 0.5 for f in wmud.defaults})
)
alice.add(wm_defaults)

stimulus = Construct(name=buffer("Stimulus"), emitter=Stimulus())
alice.add(stimulus)

acs = Structure(
    name=subsystem("ACS"),
    emitter=ACSCycle(
        matches=MatchSet(
            constructs={
                buffer("Stimulus"), buffer("WM"), buffer("WM-defaults")
            }
        )
    )
)
alice.add(acs)

# print(wmud.interface)

fnodes = [
    Construct(
        name=f, 
        emitter=MaxNode(
            matches=MatchSet(
                ctype=ConstructType.flow_xb, 
                constructs={
                    buffer("Stimulus"), 
                    buffer("WM-defaults")
                }
            )
        )
    ) 
    for f in wmud.interface
]
acs.add(*fnodes)

acs.add(
    Construct(
        name=terminus("wm"),
        emitter=ActionSelector(
            temperature=.01,
            dims=wmud.dims
        )
    )
)

nacs = Structure(
    name=subsystem("NACS"),
    emitter=NACSCycle(
        matches={buffer("Stimulus"), buffer("WM"), buffer("WM-defaults")}
    ),
    updater=ChunkAdder(
        chunks=alice.assets.chunks,
        terminus=terminus("bl-state"),
        emitter=MaxNode(
            MatchSet(
                ctype=ConstructType.flow_xt,
                constructs={buffer("Stimulus")}
            ),
        ),
        prefix="bl-state"
    )
)
alice.add(nacs)

nacs.add(
    Construct(
        name=flow_bt("Main"), 
        emitter=BottomUp(chunks=alice.assets.chunks) 
    ),
    Construct(
        name=flow_tb("Main"), 
        emitter=TopDown(chunks=alice.assets.chunks)
    )
)

fnodes = [
    Construct(
        name=feature(dim, val), 
        emitter=MaxNode(
            matches=MatchSet(
                ctype=ConstructType.flow_xb, 
                constructs={buffer("Stimulus")}
            )
        )
    ) for dim, val in [
        ("fruit", "banana"),
        ("fruit", "kiwi"),
        ("fruit", "blueberry"),
        ("fruit", "dragon fruit"),
        ("fruit", "orange"),
        ("fruit", "strawberry"),
        ("price", "very cheap"),
        ("price", "cheap"),
        ("price", "fair"),
        ("price", "expensive"),
        ("price", "very expensive"),
    ]
]
nacs.add(*fnodes)

# As mentioned, we need to create a special terminus construct that produces 
# new chunk recommendations. This is achieved with a `ChunkExtractor` object,
# which assumes that chunks are stored in a `Chunks` object.

nacs.add(
    Construct(
        name=terminus("retrieval"),
        emitter=FilteredT(
            base=BoltzmannSelector(
                temperature=.1,
                matches=MatchSet(ctype=ConstructType.chunk)
            ),
            input_filter=buffer("Stimulus"))
    ),
    Construct(
        name=terminus("bl-state"),
        emitter=ThresholdSelector(threshold=0.9)
    )
)

# Agent setup is now complete!

##################
### Simulation ###
##################

# standby (empty wm)
print("Standby (Empty WM)")

d = {
    feature("fruit", "dragon fruit"): 1.0,
    feature("price", "expensive"): 1.0,
}

alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)

# toggle empty (should do nothing)
print("Toggle (Empty WM; does nothing)")

d = {feature("wm-s1", "toggle"): 1.0}
alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)

# single write
print("Single Write")

d = {
    feature("fruit", "dragon fruit"): 1.0,
    feature("price", "expensive"): 1.0,
    feature("wm-w0", "retrieve"): 1.0
}
alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)


# reset
print("Reset")

d = {
    feature("fruit", "dragon fruit"): 1.0,
    feature("price", "expensive"): 1.0,
    feature("wm-reset", "release"): 1.0
}
alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)


# double write
print("Double Write")

d = {
    feature("fruit", "banana"): 1.0,
    feature("price", "expensive"): 1.0,
    feature("wm-w0", "retrieve"): 1.0,
    feature("wm-w1", "extract"): 1.0
}
alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)

# Toggle Slot 1
print("Toggle Slot 1")

d = {feature("wm-s1", "toggle"): 1.0}
alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)


# single delete
print("Single Delete")

d = {feature("wm-w1", "clear"): 1.0}
alice.propagate(kwds={buffer("Stimulus"): {"stimulus": d}})
alice.update()

alice.propagate(kwds={})
pprint.pprint(alice.output)


##################
### CONCLUSION ###
##################

# This simple simulation sought to demonstrate the following:
#   - The basics of using updaters for learning, and
#   - A recipe for chunk extraction from the state of the bottom level. 
