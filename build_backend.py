"""
build_backend.py – creates the C++ Extension objects and a custom build_ext
so setuptools can find NumPy headers automatically.

If PYBKT_ALLOW_PYTHON_FALLBACK=1 is set, no extensions are built and the
package falls back to pure Python.
"""
from pathlib import Path
import os, platform, sys
from sysconfig import get_paths
from setuptools import Extension
from setuptools.command.build_ext import build_ext

# ---------------------------------------------------------------------------

def _mac_find_libomp():
    """Return (include_dir, lib_dir) for Homebrew libomp (Apple silicon & Intel)."""
    if platform.system() != "Darwin":
        return None, None
    default = Path("/opt/homebrew/opt/libomp")  # also works on Intel (Rosetta)
    import shutil, subprocess
    if shutil.which("brew"):
        try:
            prefix = Path(subprocess.check_output(
                ["brew", "--prefix", "libomp"], text=True).strip())
        except subprocess.CalledProcessError:
            prefix = default
    else:
        prefix = default
    return prefix / "include", prefix / "lib"

# ---------------------------------------------------------------------------

class CustomBuildExtCommand(build_ext):
    """Adds NumPy's C headers to the include path automatically."""
    def finalize_options(self):
        super().finalize_options()
        import numpy as np
        self.include_dirs.append(np.get_include())

# ---------------------------------------------------------------------------

INCLUDE_DIRS   = ["source-cpp/pyBKT/Eigen", get_paths()["include"]]
LIBRARY_DIRS   = []
EXTRA_COMPILE  = ["-fPIC", "-w", "-O3"]
EXTRA_LINK     = []
LIBRARIES      = ["pthread", "dl", "util", "m"]

if platform.system() == "Darwin":
    EXTRA_COMPILE += ["-Xpreprocessor", "-fopenmp", "-stdlib=libc++"]
    EXTRA_LINK    += ["-stdlib=libc++", "-fopenmp"]
    omp_inc, omp_lib = _mac_find_libomp()
    if omp_inc and omp_lib:
        INCLUDE_DIRS.append(str(omp_inc))
        LIBRARY_DIRS.append(str(omp_lib))
        LIBRARIES.append("omp")
else:
    EXTRA_COMPILE += ["-fopenmp"]
    EXTRA_LINK    += ["-fopenmp"]

INCLUDE_DIRS = [p for p in INCLUDE_DIRS if p]
LIBRARY_DIRS = [p for p in LIBRARY_DIRS if p]

def _ext(src: str, module_name: str) -> Extension:
    """Factory for Extension objects with shared flags."""
    return Extension(
        module_name,
        [src],
        include_dirs      = INCLUDE_DIRS,
        library_dirs      = LIBRARY_DIRS + [sys.exec_prefix + "/lib"],
        libraries         = LIBRARIES,
        extra_compile_args= EXTRA_COMPILE,
        extra_link_args   = EXTRA_LINK,
        language          = "c++",
    )

ext_modules = [
    _ext("source-cpp/pyBKT/generate/synthetic_data_helper.cpp",
         "pyBKT.generate.synthetic_data_helper"),
    _ext("source-cpp/pyBKT/fit/E_step.cpp",
         "pyBKT.fit.E_step"),
    _ext("source-cpp/pyBKT/fit/predict_onestep_states.cpp",
         "pyBKT.fit.predict_onestep_states"),
]

# Optional pure-Python wheel
if os.getenv("PYBKT_ALLOW_PYTHON_FALLBACK") == "1":
    ext_modules = []

__all__ = ["ext_modules", "CustomBuildExtCommand"]
