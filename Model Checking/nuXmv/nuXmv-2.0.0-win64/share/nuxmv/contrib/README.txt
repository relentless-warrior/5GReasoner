This directory contains various scripts for converting between the
nuXmv native input format and other formats for specifying transition
systems. These scripts are distributed under the same license of
nuXmv. For details about the license, please read carefully
LICENSE.txt in the nuXmv distribution.

----------------------------------------------------------------------
* vmt2nuxmv.py 

  Generates a nuXmv file from a VMT [1] file.

  It reads from standard input, and writes to standard output.

----------------------------------------------------------------------
* vmt2btor.py

  Generates a BTOR [2] file from a VMT file.

  It reads from standard input, and writes to standard output. Since
  BTOR only allows a single invariant property for each file, if the
  VMT file contains multiple properties, the invariant property to
  include in the output should be specified with the -p option.

----------------------------------------------------------------------
* btor2nuxmv.py

  Generates either a nuXmv or a VMT file from a BTOR file.

  It reads from standard input, and writes to standard output. The
  format for output can be specified by passing either --vmt or
  --nuxmv as a command-line argument. If none is specified, --nuxmv is
  assumed.

  Notice that, currently the support for arrays in nuXmv is limited,
  so the conversion will fail if the input BTOR file contains
  arrays. However, arrays are supported if --vmt is selected.

----------------------------------------------------------------------

All the above scripts require the MathSAT5 Python bindings to work.

The MathSAT5 Python bindings can be downloaded from the MathSAT5 web
site: http://mathsat.fbk.eu.



References:

[1] A description of the VMT format can be found in the User's Manual
    of nuXmv, section 5.6.2

[2] A description of the BTOR format can be found in: Robert
    Brummayer, Armin Biere, Florian Lonsing. "BTOR: bit-precise
    modelling of word-level problems for model checking".
