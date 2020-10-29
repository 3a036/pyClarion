"""Demonstrates selection & control of reasoning methods."""


from pyClarion import *
import pprint


alice = Structure(
    name=agent("Alice"),
    emitter=AgentCycle(),
    assets=Assets(chunks=Chunks())
)

with alice:

    stimulus = Construct(
        name=buffer("stimulus"), 
        emitter=Stimulus()
    )

    gate = Construct(
        name=buffer("flow-gate"),
        emitter=FilteringRelay(
            controller=(subsystem("acs"), terminus("nacs")),
            interface=FilteringRelay.Interface(
                clients=(
                    flow_in("stimulus"), 
                    flow_tt("associations"), 
                    flow_bt("main")
                ),
                tags=("nacs-stim", "nacs-assoc", "nacs-bt"),
                vals=(0, 1)
            )
        )
    )

    defaults = Construct(
        name=buffer("defaults"),
        emitter=ConstantBuffer(
            strengths={f: 0.5 for f in gate.emitter.interface.defaults}
        )
    )

    acs = Structure(
        name=subsystem("acs"),
        emitter=ACSCycle(
            sources={buffer("stimulus"), buffer("defaults")}
        )
    )

    with acs:

        Construct(
            name=features("main"),
            emitter=MaxNodes(
                sources={buffer("stimulus"), buffer("defaults")},
                ctype=ConstructType.feature
            )
        )

        Construct(
            name=terminus("nacs"),
            emitter=ActionSelector(
                source=features("main"),
                dims=gate.emitter.interface.dims,
                temperature=0.01
            )
        )

    nacs = Structure(
        name=subsystem("nacs"),
        emitter=NACSCycle(       
            sources={
                buffer("stimulus"), 
                buffer("flow-gate")
            }
        ),
        assets=Assets(rules=Rules())
    )

    with nacs:

        Construct(
            name=features("main"),
            emitter=MaxNodes(
                sources={flow_tb("main")},
                ctype=ConstructType.feature
            )
        )

        Construct(
            name=chunks("main"),
            emitter=MaxNodes(
                sources={
                    buffer("stimulus"), 
                    flow_bt("main"), 
                    flow_tt("associations")
                },
                ctype=ConstructType.chunk
            )
        )

        Construct(
            name=flow_in("stimulus"),
            emitter=GatedA(
                base=Repeater(source=buffer("stimulus")),
                gate=buffer("flow-gate")
            )
        )

        Construct(
            name=flow_tt("associations"),
            emitter=GatedA(
                base=AssociativeRules(
                    source=chunks("main"),
                    rules=nacs.assets.rules
                ),
                gate=buffer("flow-gate")
            ) 
        )

        Construct(
            name=flow_bt("main"), 
            emitter=GatedA(
                base=BottomUp(
                    source=features("main"),
                    chunks=alice.assets.chunks
                ),
                gate=buffer("flow-gate") 
            )
        )

        Construct(
            name=flow_tb("main"), 
            emitter=TopDown(
                source=chunks("main"),
                chunks=alice.assets.chunks
            ) 
        )

        Construct(
            name=terminus("retrieval"),
            emitter=FilteredT(
                base=BoltzmannSelector(
                    source=chunks("main"),
                    temperature=.1
                ),
                filter=flow_in("stimulus")
            )
        )


nacs.assets.rules.link(chunk("FRUIT"), chunk("APPLE")) # type: ignore

alice.assets.chunks.link( # type: ignore
    chunk("APPLE"), 
    feature("color", "#ff0000"), 
    feature("color", "#008000"),
    feature("tasty", True)
)

alice.assets.chunks.link( # type: ignore
    chunk("JUICE"),
    feature("tasty", True),
    feature("state", "liquid")
)

alice.assets.chunks.link( # type: ignore
    chunk("FRUIT"),
    feature("tasty", True),
    feature("sweet", True)
)


##################
### Simulation ###
##################

print("CYCLE 1: Open stimulus only.") 

stimulus.emitter.input({feature("nacs-stim", 1.0): 1.0})
alice.propagate()
alice.update()
print(
    "Step 1: {} -> {}".format(
        gate.emitter.controller, 
        alice[gate.emitter.controller].output
    )
)

stimulus.emitter.input({chunk("APPLE"): 1.})
alice.propagate()
alice.update()
print("Step 2: {} ->".format(subsystem("nacs")))
pprint.pprint(alice[subsystem("nacs")].output)
print()


print("CYCLE 2: Open stimulus & associations only.")

stimulus.emitter.input({
    feature("nacs-stim", 1.): 1., 
    feature("nacs-assoc", 1.): 1.
})
alice.propagate()
alice.update()
print(
    "Step 1: {} -> {}".format(
        gate.emitter.controller, 
        alice[gate.emitter.controller].output
    )
)

stimulus.emitter.input({chunk("APPLE"): 1.})
alice.propagate()
alice.update()
print("Step 2: {} ->".format(subsystem("nacs")))
pprint.pprint(alice[subsystem("nacs")].output)
print()

print("CYCLE 3: Open stimulus & bottom-up only.")

stimulus.emitter.input({
    feature("nacs-stim", 1.): 1.,
    feature("nacs-bt", 1.): 1.
})
alice.propagate()
alice.update()
print(
    "Step 1: {} -> {}".format(
        gate.emitter.controller, 
        alice[gate.emitter.controller].output
    )
)

stimulus.emitter.input({chunk("APPLE"): 1.})
alice.propagate()
alice.update()
print("Step 2: {} ->".format(subsystem("nacs")))
pprint.pprint(alice[subsystem("nacs")].output)
print()
