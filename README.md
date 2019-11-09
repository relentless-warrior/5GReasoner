# 5GReasoner
5GReasoner: A Property-Directed Security and Privacy Analysis Framework for 5G Cellular Network Protocol. (CCS'19)


## Modules
Each module contains seprate README file for instructions on how to run.
## NAS Layer
- nuXmv/isolation/FSM/AMF-NAS-5G.dot: Finite state machine (FSM) for AMF.
- nuXmv/solation/FSM/UE-NAS-5G.dot: Finite state machine (FSM) for UE.
- nuXmv/isolation/dot2smv.py : Converter to nuXmv from UE and AMF finite state machines.
- nuXmv/isolation/NAS_poperty.smv: Properties and counter-examples for NAS layer.

## RRC Layer
* nuXmv/isolation/FSM/BS-RRC-5G.dot: Finite state machine (FSM) for Base station.

* nuXmv/isolation/FSM/UE-RRC-5G.dot: Finite state machine (FSM) for RRC layer of UE.

* nuXmv/isolation/dot2smv.py : Converter to nuXmv from UE-RRC and base station finite state machines.

* nuXmv/isolation/RRC_poperty.smv: Properties and counter-examples for RRC layer.

## Cross Layer

* nuXmv/Cross-layer/FSM/NAS/AMF-NAS-5G.dot: Finite state machine (FSM) for AMF.

* nuXmv/Cross-layer/FSM/NAS/UE-NAS-5G.dot: Finite state machine (FSM) for UE.

* nuXmv/Cross-layer/FSM/RRC/BS-RRC-5G.dot: Finite state machine (FSM) for Base station.

* nuXmv/Cross-layer/FSM/RRC/UE-RRC-5G.dot: Finite state machine (FSM) for RRC layer of UE.

* nuXmv/Cross-layer/dot2smv.py : Converter to nuXmv from the four finite state machines of both RRC and NAS layer.

* nuXmv/Cross-layer/CrossLayer_property.smv: Properties and counter-examples for cross layer testing.
