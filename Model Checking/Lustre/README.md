# 5GReasoner - Lustre

This directory contains the dot files for NAS and RRC in isolation.

To generate the lustre (.lus) files, please use the python script provided
by running the following command

python2 dot2lustre.py -client <Path to UE dot file> -server <Path to BS or AMF dot file> -o <Path to output lustre file>

The dot files are included in the "FSM" directory, which then is broken down into "RRC" and "NAS"

For convenience purposes, the Lustre files for NAS and RRC in isolation have been included 
in this directory,
NAS.lus and RRC.lus respectively.

Lustre model only suports isolation and only UE FSM is being tested. This being said, it is 
possible to write guarantees (i.e., properties)
to test AMF (or BS) as well as adversarial testing.

To test for AMF (or BS), one can write guarantees in the "AMF_NAS_controller_contract" and
"BS_RRC_controller_contract" respectively. To test in an adversarial environment, one can
write guarantees in the "Run_5G_FSM_contract".

Note that the keyword used in Lustre "--%MAIN;" will have to be moved to let tool know which set
of guarantees it is currently verifying for.

To modify the conformance tests being used for UE, one can edit the UE_NAS_guarantees.txt file 
or the UE_RRC_guarantees.txt file respectively found in the properties-guarantees directory.

Once the desired Lustre file has been generated, we have provided the kind2 executable to test
the desired properties.

To run a lustre file, simply run the following command

./kind2-v1.1.0-linux <Lustre file>

If a problem is encountered with the executable, optionally Kind2 supports a stable web interface which
can be found at the following link:

http://kind2-mc.github.io/kind2/

Additionally, this directory contains a "conformance" directory which contain the conformance tests
in English and contains a directory named "3GPP Document" where the 3GPP document that was used is included.
