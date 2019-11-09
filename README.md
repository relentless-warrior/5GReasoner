# 5GReasoner
5GReasoner: A Property-Directed Security and Privacy Analysis Framework for 5G Cellular Network Protocol. (CCS'19)


## Modules
Each module contains seprate README file for instructions on how to run.
## NAS Layer
- nuXmv/isolation/FSM/AMF-NAS-5G.dot: Finite state machine (FSM) for AMF.
- nuXmv/solation/FSM/UE-NAS-5G.dot: Finite state machine (FSM) for UE.
- nuXmv/isolation/dot2smv.py : Converter to nuXmv from UE and AMF finite state machines.
- nuXmv/isolation/NAS_poperty.smv: Properties and counter-examples for NAS layer.

- Lustre/dot2lustre.py : Converter to Lustre.
- Lustre/properties-guarantees/UE_NAS_guarantees.txt : Properties for NAS conformance tests.
- Lustre/FSM/NAS/UE-NAS-5G.dot : Fine state machine (FSM) for UE.
- Lustre/FSM/AMF-NAS-5G.dot : Finite state machine (FSM) for AMF.
- Lustre/NAS.lus : Lustre file for NAS layer with conformance guarantees.

## RRC Layer
* nuXmv/isolation/FSM/BS-RRC-5G.dot: Finite state machine (FSM) for Base station.

* nuXmv/isolation/FSM/UE-RRC-5G.dot: Finite state machine (FSM) for RRC layer of UE.

* nuXmv/isolation/dot2smv.py : Converter to nuXmv from UE-RRC and base station finite state machines.

* nuXmv/isolation/RRC_poperty.smv: Properties and counter-examples for RRC layer.

* Lustre/dot2lustre.py : Convert to Lustre.

* Lustre/properties-guarantees/UE_RRC_guarantees.txt : Properties for RRC conformance tests.

* Lustre/FSM/RRC/UE-RRC-5G.dot : Finite state machine (FSM) for RRC of UE.

* Lustre/FSM/RRC/BS-RRC-5G.dot : Finite state machine (FSM) for Base station.

* Lustre/RRC.lus : Lustre file for RRC layer with conformance guarantees.

## Cross Layer

* nuXmv/Cross-layer/FSM/NAS/AMF-NAS-5G.dot: Finite state machine (FSM) for AMF.

* nuXmv/Cross-layer/FSM/NAS/UE-NAS-5G.dot: Finite state machine (FSM) for UE.

* nuXmv/Cross-layer/FSM/RRC/BS-RRC-5G.dot: Finite state machine (FSM) for Base station.

* nuXmv/Cross-layer/FSM/RRC/UE-RRC-5G.dot: Finite state machine (FSM) for RRC layer of UE.

* nuXmv/Cross-layer/dot2smv.py : Converter to nuXmv from the four finite state machines of both RRC and NAS layer.

* nuXmv/Cross-layer/CrossLayer_property.smv: Properties and counter-examples for cross layer testing.
