"""Demonstrates selection & control of reasoning methods."""


from pyClarion import (
    feature, chunk, rule, features, chunks, flow_in, flow_tt, flow_bt, flow_tb, 
    terminus, buffer, subsystem, agent,
    Structure, Construct,
    AgentCycle, NACSCycle, ACSCycle,
    Stimulus, Constants, ParamSet, MaxNodes, Repeater, TopDown, BottomUp, 
    AssociativeRules, ActionSelector, BoltzmannSelector, Gated, Filtered,
    Chunks, Rules, Assets,
    pprint
)

from itertools import count


gate_interface = ParamSet.Interface(
    tag="gate",
    vals=("standby", "clear", "update", "clear+update"),
    clients={
        flow_in("stimulus"),
        flow_tt("associations"),
        flow_bt("main")
    },
    func=lambda c: ("gate", c.ctype.name, c.cid),
    param_val="param"
)


chunk_db = Chunks()
rule_db = Rules()

rule_db.link(rule("1"), chunk("FRUIT"), chunk("APPLE")) 

chunk_db.link( 
    chunk("APPLE"), 
    feature("color", "#ff0000"), 
    feature("color", "#008000"),
    feature("tasty", True)
)

chunk_db.link( 
    chunk("JUICE"),
    feature("tasty", True),
    feature("state", "liquid")
)

chunk_db.link( 
    chunk("FRUIT"),
    feature("tasty", True),
    feature("sweet", True)
)


alice = Structure(
    name=agent("Alice"),
    emitter=AgentCycle(),
    assets=Assets(
        gate_interface=gate_interface
    )
)

with alice:

    stimulus = Construct(
        name=buffer("stimulus"), 
        emitter=Stimulus()
    )

    acs_ctrl = Construct(
        name=buffer("acs_ctrl"), 
        emitter=Stimulus()
    )

    gate = Construct(
        name=buffer("gate"),
        emitter=ParamSet(
            controller=(subsystem("acs"), terminus("nacs")),
            interface=alice.assets.gate_interface
        )
    )

    defaults = Construct(
        name=buffer("defaults"),
        emitter=Constants(
            strengths={f: 0.5 for f in alice.assets.gate_interface.defaults}
        )
    )

    acs = Structure(
        name=subsystem("acs"),
        emitter=ACSCycle(
            sources={
                buffer("acs_ctrl"), 
                buffer("defaults")
            }
        )
    )

    with acs:

        Construct(
            name=features("main"),
            emitter=MaxNodes(
                sources={
                    buffer("acs_ctrl"), 
                    buffer("defaults")
                }
            )
        )

        Construct(
            name=terminus("nacs"),
            emitter=ActionSelector(
                source=features("main"),
                client_interface=alice.assets.gate_interface,
                temperature=0.01
            )
        )

    nacs = Structure(
        name=subsystem("nacs"),
        emitter=NACSCycle(       
            sources={
                buffer("stimulus"), 
                buffer("gate")
            }
        ),
        assets=Assets(
            chunk_db=chunk_db, 
            rule_db=rule_db
        )
    )

    with nacs:

        Construct(
            name=features("main"),
            emitter=MaxNodes(
                sources={
                    flow_tb("main"),
                    flow_in("gate_meta")
                }
            )
        )

        Construct(
            name=chunks("main"),
            emitter=MaxNodes(
                sources={
                    buffer("stimulus"), 
                    flow_bt("main"), 
                    flow_tt("associations")
                }
            )
        )

        Construct(
            name=flow_in("stimulus"),
            emitter=Gated(
                base=Repeater(source=buffer("stimulus")),
                gate=buffer("gate")
            )
        )

        Construct(
            name=flow_in("gate_meta"),
            emitter=ParamSet.MetaKnowledge(
                source=buffer("gate"),
                client_interface=alice.assets.gate_interface
            )
        )

        Construct(
            name=flow_tt("associations"),
            emitter=Gated(
                base=AssociativeRules(
                    source=chunks("main"),
                    rules=nacs.assets.rule_db
                ),
                gate=buffer("gate")
            ) 
        )

        Construct(
            name=flow_bt("main"), 
            emitter=Gated(
                base=BottomUp(
                    source=features("main"),
                    chunks=nacs.assets.chunk_db
                ),
                gate=buffer("gate") 
            )
        )

        Construct(
            name=flow_tb("main"), 
            emitter=TopDown(
                source=chunks("main"),
                chunks=nacs.assets.chunk_db
            ) 
        )

        Construct(
            name=terminus("retrieval"),
            emitter=Filtered(
                base=BoltzmannSelector(
                    source=chunks("main"),
                    temperature=.1
                ),
                sieve=buffer("stimulus")
            )
        )


##################
### Simulation ###
##################


def record_step(agent, step):

    print("Step {}:".format(step))
    print()
    print("Activations")
    output = dict(agent.output)
    del output[buffer("defaults")]
    pprint(output)
    print()

counter = count(1)
alice.start()

step = next(counter)

print("CYCLE 1: Open stimulus only.\n") 

msg = "NACS should output nothing on step {} b/c flows not enabled...\n"
print(msg.format(step + 1))

stimulus.emitter.input({chunk("APPLE"): 1.})
acs_ctrl.emitter.input({
    feature("gate", "update"): 1.0,
    feature(("gate", "flow_in", "stimulus"), "param"): 1.0
})
alice.step()
record_step(alice, step)

step = next(counter)

stimulus.emitter.input({chunk("APPLE"): 1.})
acs_ctrl.emitter.input({})
alice.step()
record_step(alice, step)

step = next(counter)

print("CYCLE 2: Open stimulus & associations only.\n")

msg = "NACS should output 'FRUIT' on step {} due to associative rules...\n"
print(msg.format(step + 1))

stimulus.emitter.input({chunk("APPLE"): 1.})
acs_ctrl.emitter.input({
        feature("gate", "update"): 1.0,
        feature(("gate", "flow_tt", "associations"), "param"): 1.0
})
alice.step()
record_step(alice, step)

step = next(counter)

stimulus.emitter.input({chunk("APPLE"): 1.})
acs_ctrl.emitter.input({})
alice.step()
record_step(alice, step)

step = next(counter)

print("CYCLE 3: Open stimulus & bottom-up only.\n")

msg = (
    "NACS should output 'FRUIT' or 'JUICE' with equal probability on step {} " 
    "due to bottom-up activations...\n"
)
print(msg.format(step + 1))

stimulus.emitter.input({chunk("APPLE"): 1.})
acs_ctrl.emitter.input({
    feature("gate", "clear+update"): 1.0,
    feature(("gate", "flow_in", "stimulus"), "param"): 1.0,
    feature(("gate", "flow_bt", "main"), "param"): 1.0
})
alice.step()
record_step(alice, step)

step = next(counter)

stimulus.emitter.input({chunk("APPLE"): 1.})
acs_ctrl.emitter.input({})
alice.step()
record_step(alice, step)
