#!/bin/bash

# Use internal htslib
export CFLAGS="-I${PREFIX}/include/curl/ -I${PREFIX}/include -L${PREFIX}/lib"

$PYTHON setup.py install
