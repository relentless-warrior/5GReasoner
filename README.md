# 5GReasoner
5GReasoner: A Property-Directed Security and Privacy Analysis Framework for 5G Cellular Network Protocol. (CCS'19)

# NuXmv


## Modules
Each module contains seprate README file for instructions on how to run.
## NAS Layer
isolation/FSM/AMF-NAS-5G.dot: Finite state machine (FSM) for AMF.
isolation/FSM/UE-NAS-5G.dot: Finite state machine (FSM) for UE.
isolation/dot2smv.py : Converter to nuXmv from UE and AMF finite state machines.
isolation/NAS_poperty.smv: Properties and counter-examples for NAS layer.

## RRC Layer
isolation/FSM/BS-RRC-5G.dot: Finite state machine (FSM) for Base station.
isolation/FSM/UE-RRC-5G.dot: Finite state machine (FSM) for RRC layer of UE.
isolation/dot2smv.py : Converter to nuXmv from UE-RRC and base station finite state machines.
isolation/RRC_poperty.smv: Properties and counter-examples for RRC layer.

## Cross Layer

Cross-layer/FSM/NAS/AMF-NAS-5G.dot: Finite state machine (FSM) for AMF.
Cross-layer/FSM/NAS/UE-NAS-5G.dot: Finite state machine (FSM) for UE.
Cross-layer/FSM/RRC/BS-RRC-5G.dot: Finite state machine (FSM) for Base station.
Cross-layer/FSM/RRC/UE-RRC-5G.dot: Finite state machine (FSM) for RRC layer of UE.
Cross-layer/dot2smv.py : Converter to nuXmv from the four finite state machines of both RRC and NAS layer.
Cross-layer/CrossLayer_property.smv: Properties and counter-examples for cross layer testing.
