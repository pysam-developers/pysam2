import os
import sys
import sysconfig

from pysam.libchtslib import *
from pysam.libcutils import *
import pysam.libcutils as libcutils
import pysam.libcfaidx as libcfaidx
from pysam.libcfaidx import *
import pysam.libctabix as libctabix
from pysam.libctabix import *
# import pysam.libctabixproxies as libctabixproxies
# from pysam.libctabixproxies import *
import pysam.libcsamfile as libcsamfile
from pysam.libcsamfile import *
import pysam.libcalignmentfile as libcalignmentfile
from pysam.libcalignmentfile import *
import pysam.libcalignedsegment as libcalignedsegment
from pysam.libcalignedsegment import *
import pysam.libcvcf as libcvcf
from pysam.libcvcf import *
import pysam.libcbcf as libcbcf
from pysam.libcbcf import *
import pysam.libcbgzf as libcbgzf
from pysam.libcbgzf import *
import pysam.Pileup as Pileup


# export all the symbols from separate modules
__all__ = \
    libchtslib.__all__ +\
    libcutils.__all__ +\
    libctabix.__all__ +\
    libcvcf.__all__ +\
    libcbcf.__all__ +\
    libcbgzf.__all__ +\
    libcfaidx.__all__ +\
    libctabixproxies.__all__ +\
    libcalignmentfile.__all__ +\
    libcalignedsegment.__all__ +\
    libcsamfile.__all__


from pysam.version import __version__


def get_include():
    '''return a list of include directories.'''
    dirname = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    includes = [dirname]
    return includes


def get_defines():
    '''return a list of defined compilation parameters.'''
    # ('_FILE_OFFSET_BITS', '64'),
    # ('_USE_KNETFILE', '')]
    return []


def get_libraries():
    '''return a list of libraries to link against.'''
    # Note that this list does not include libcsamtools.so as there are
    # numerous name conflicts with libchtslib.so.
    dirname = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    pysam_libs = ['libctabixproxies',
                  'libcfaidx',
                  'libcsamfile',
                  'libcvcf',
                  'libcbcf',
                  'libchtslib',
                  'libctabix']

    so = sysconfig.get_config_var('SO')
    return [os.path.join(dirname, x + so) for x in pysam_libs]
