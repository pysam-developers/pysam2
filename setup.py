#! /usr/bin/python

'''pysam - a python module for reading, manipulating and writing
genomic data sets.

pysam is a lightweight wrapper of the htslib C-API and provides
facilities to read and write SAM/BAM/VCF/BCF/BED/GFF/GTF/FASTA/FASTQ
files as well as access to the command line functionality of the
samtools and bcftools packages. The module supports compression and
random access through indexing.

This module provides a low-level wrapper around the htslib C-API as
using cython and a high-level API for convenient access to the data
within standard genomic file formats.

See:
http://www.htslib.org
https://github.com/pysam-developers/pysam
http://pysam.readthedocs.org/en/stable

'''

import collections
import glob
import os
import platform
import re
import subprocess
import sys
import sysconfig
from contextlib import contextmanager
from setuptools import Extension, setup
from cy_build import CyExtension as Extension, cy_build_ext as build_ext
try:
    import cython
    HAVE_CYTHON = True
except ImportError:
    HAVE_CYTHON = False

IS_PYTHON3 = sys.version_info.major >= 3


@contextmanager
def changedir(path):
    save_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(save_dir)


def run_configure(option):
    sys.stdout.flush()
    try:
        retcode = subprocess.call(
            " ".join(("./configure", option)),
            shell=True)
        if retcode != 0:
            return False
        else:
            return True
    except OSError as e:
        return False


def check_file_is_present(path_var, filename, msg):
    if path_var is None:
        raise ValueError(msg)
    fn = os.path.join(path_var, filename)
    if not os.path.exists(fn):
        raise OSError("expected file {} not found".format(fn))
    
                          
@contextmanager
def set_compiler_envvars():
    tmp_vars = []
    for var in ['CC', 'CFLAGS', 'LDFLAGS']:
        if var in os.environ:
            print ("# pysam: (env) {}={}".format(var, os.environ[var]))
        elif var in sysconfig.get_config_vars():
            value = sysconfig.get_config_var(var)
            print ("# pysam: (sysconfig) {}={}".format(var, value))
            os.environ[var] = value
            tmp_vars += [var]

    try:
        yield
    finally:
        for var in tmp_vars:
            del os.environ[var]


def configure_library(library_dir, env_options=None, options=[]):

    configure_script = os.path.join(library_dir, "configure")

    on_rtd = os.environ.get("READTHEDOCS") == "True"
    # RTD has no bzip2 development libraries installed:
    if on_rtd:
        env_options = "--disable-bz2"

    if not os.path.exists(configure_script):
        raise ValueError(
            "configure script {} does not exist".format(configure_script))

    with changedir(library_dir), set_compiler_envvars():
        if env_options is not None:
            if run_configure(env_options):
                return env_options

        for option in options:
            if run_configure(option):
                return option

    return None


def distutils_dir_name(dname):
    """Returns the name of a distutils build directory
    see: http://stackoverflow.com/questions/14320220/
               testing-python-c-libraries-get-build-path
    """
    f = "{dirname}.{platform}-{version[0]}.{version[1]}"
    return f.format(dirname=dname,
                    platform=sysconfig.get_platform(),
                    version=sys.version_info)


def get_pysam_version():
    sys.path.insert(0, "pysam")
    import version
    return version.__version__


HTSLIB_LIBRARY_DIR = os.environ.get("HTSLIB_LIBRARY_DIR", None)
if HTSLIB_LIBRARY_DIR is None and "CONDA_PREFIX" in os.environ:
    HTSLIB_LIBRARY_DIR = os.path.join(os.environ.get("CONDA_PREFIX"), "lib")

check_file_is_present(HTSLIB_LIBRARY_DIR, "libhts.so", "HTSLIB_LIBRARY_DIR not set")
        
HTSLIB_INCLUDE_DIR = os.environ.get("HTSLIB_INCLUDE_DIR", None)
if HTSLIB_INCLUDE_DIR is None and "CONDA_PREFIX" in os.environ:
    HTSLIB_INCLUDE_DIR = os.path.join(os.environ.get("CONDA_PREFIX"), "include")

check_file_is_present(HTSLIB_INCLUDE_DIR, "htslib/hts.h", "HTSLIB_INCLUDE_DIR not set")
    
HTSLIB_SOURCE = None

package_list = ['pysam',
                'pysam.include']
package_dirs = {'pysam': 'pysam'}


cmdclass = {'build_ext': build_ext}

# If cython is available, the pysam will be built using cython from
# the .pyx files. If no cython is available, the C-files included in the
# distribution will be used.
if HAVE_CYTHON:
    print ("# pysam: cython is available - using cythonize if necessary")
    source_pattern = "pysam/libc%s.pyx"
else:
    print ("# pysam: no cython available - using pre-compiled C")
    source_pattern = "pysam/libc%s.c"

# Exit if there are no pre-compiled files and no cython available
fn = source_pattern % "tabix"
if not os.path.exists(fn):
    raise ValueError(
        "no cython installed, but can not find {}."
        "Make sure that cython is installed when building "
        "from the repository"
        .format(fn))

# linking against a shared, externally installed htslib version, no
# sources required for htslib
htslib_sources = []
shared_htslib_sources = []
chtslib_sources = []
htslib_library_dirs = [HTSLIB_LIBRARY_DIR]
htslib_include_dirs = [HTSLIB_INCLUDE_DIR]
external_htslib_libraries = ['z', 'hts']

#######################################################
# Windows compatibility - untested
if platform.system() == 'Windows':
    include_os = ['win32']
    os_c_files = ['win32/getopt.c']
    extra_compile_args = []
else:
    include_os = []
    os_c_files = []
    # for python 3.4, see for example
    # http://stackoverflow.com/questions/25587039/
    # error-compiling-rpy2-on-python3-4-due-to-werror-
    # declaration-after-statement
    extra_compile_args = [
        "-Wno-unused",
        "-Wno-strict-prototypes",
        "-Wno-sign-compare",
        "-Wno-error=declaration-after-statement"]

define_macros = []

suffix = sysconfig.get_config_var('EXT_SUFFIX')
if not suffix:
    suffix = sysconfig.get_config_var('SO')

internal_pysamutil_libraries = [
    os.path.splitext("chtslib{}".format(suffix))[0],
    os.path.splitext("cutils{}".format(suffix))[0]]

libraries_for_pysam_module = external_htslib_libraries + internal_pysamutil_libraries

# Order of modules matters in order to make sure that dependencies are resolved.
# The structures of dependencies is as follows:
# libchtslib: htslib utility functions and htslib itself if builtin is set.
# libcsamtools: samtools code (builtin)
# libcbcftools: bcftools code (builtin)
# libcutils: General utility functions, depends on all of the above
# libcXXX (pysam module): depends on libchtslib and libcutils

# The list below uses the union of include_dirs and library_dirs for
# reasons of simplicity.

modules = [
    dict(name="pysam.libchtslib",
         sources=[source_pattern % "htslib", "pysam/htslib_util.c"] + shared_htslib_sources + os_c_files,
         libraries=external_htslib_libraries),
    dict(name="pysam.libcutils",
         sources=[source_pattern % "utils", "pysam/pysam_util.c"] + htslib_sources + os_c_files,
         libraries=external_htslib_libraries),
    dict(name="pysam.libcalignmentfile",
         sources=[source_pattern % "alignmentfile"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libcsamfile",
         sources=[source_pattern % "samfile"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libcalignedsegment",
         sources=[source_pattern % "alignedsegment"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libctabix",
         sources=[source_pattern % "tabix"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libcfaidx",
         sources=[source_pattern % "faidx"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libcbcf",
         sources=[source_pattern % "bcf"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libcbgzf",
         sources=[source_pattern % "bgzf"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libctabixproxies",
         sources=[source_pattern % "tabixproxies"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
    dict(name="pysam.libcvcf",
         sources=[source_pattern % "vcf"] + htslib_sources + os_c_files,
         libraries=libraries_for_pysam_module),
]

common_options = dict(
    language="c",
    extra_compile_args=extra_compile_args,
    define_macros=define_macros,
    # for out-of-tree compilation, use absolute paths
    library_dirs=[os.path.abspath(x) for x in ["pysam"] + htslib_library_dirs],
    include_dirs=[os.path.abspath(x) for x in htslib_include_dirs + \
                  ["samtools", "samtools/lz4", "bcftools", "pysam", "."] + include_os])

# add common options (in python >3.5, could use n = {**a, **b}
for module in modules:
    module.update(**common_options)

classifiers = """
Development Status :: 4 - Beta
Intended Audience :: Science/Research
Intended Audience :: Developers
License :: OSI Approved
Programming Language :: Python
Topic :: Software Development
Topic :: Scientific/Engineering
Operating System :: POSIX
Operating System :: Unix
Operating System :: MacOS
"""

metadata = {
    'name': "pysam",
    'version': get_pysam_version(),
    'description': "pysam",
    'long_description': __doc__,
    'author': "Andreas Heger",
    'author_email': "andreas.heger@gmail.com",
    'license': "MIT",
    'platforms': ["POSIX", "UNIX", "MacOS"],
    'classifiers': [_f for _f in classifiers.split("\n") if _f],
    'url': "https://github.com/pysam-developers/pysam",
    'packages': package_list,
    'requires': ['cython (>=0.21)'],
    'ext_modules': [Extension(**opts) for opts in modules],
    'cmdclass': cmdclass,
    'package_dir': package_dirs,
    'package_data': {'': ['*.pxd', '*.h'], },
    # do not pack in order to permit linking to csamtools.so
    'zip_safe': False,
    'use_2to3': True,
}

if __name__ == '__main__':
    dist = setup(**metadata)
