"""
build_backend.py – holds the custom Extension objects and build_ext logic.
Only imported inside the isolated build env created by pip/PEP 517.
"""

from pathlib import Path
import os, platform, sys
from sysconfig import get_paths
from setuptools import Extension
from setuptools.command.build_ext import build_ext

# ----- helper ---------------------------------------------------------------

def _mac_find_libomp():
    """Return (include_dir, lib_dir) for Homebrew libomp; graceful fallback."""
    if platform.system() != "Darwin":
        return None, None
    default = Path("/opt/homebrew/opt/libomp")
    if os.getenv("CI"):                      # don’t shell-out on CI runners
        prefix = default
    else:
        import shutil, subprocess
        try:
            prefix = Path(subprocess.check_output(
                ["brew", "--prefix", "libomp"], text=True).strip())
        except Exception:
            prefix = default
    return prefix / "include", prefix / "lib"

# ----- custom build_ext -----------------------------------------------------

class CustomBuildExtCommand(build_ext):
    """Adds NumPy headers automatically."""
    def finalize_options(self):
        super().finalize_options()
        import numpy as np
        self.include_dirs.append(np.get_include())

# ----- common compiler flags ------------------------------------------------

INCLUDE_DIRS = [
    "source-cpp/pyBKT/Eigen",
    get_paths()["include"],
]
LIBRARY_DIRS = []
EXTRA_COMPILE_ARGS = ["-fPIC", "-w", "-O3"]
EXTRA_LINK_ARGS   = []
LIBRARIES         = ["pthread", "dl", "util", "m"]

if platform.system() == "Darwin":
    # Clang OpenMP flags
    EXTRA_COMPILE_ARGS += ["-Xpreprocessor", "-fopenmp", "-stdlib=libc++"]
    EXTRA_LINK_ARGS    += ["-stdlib=libc++", "-fopenmp"]
    omp_inc, omp_lib   = _mac_find_libomp()
    if omp_inc and omp_lib:
        INCLUDE_DIRS.append(str(omp_inc))
        LIBRARY_DIRS.append(str(omp_lib))
        LIBRARIES.append("omp")
else:
    EXTRA_COMPILE_ARGS += ["-fopenmp"]
    EXTRA_LINK_ARGS    += ["-fopenmp"]

# remove empties
LIBRARY_DIRS = [p for p in LIBRARY_DIRS if p]
INCLUDE_DIRS = [p for p in INCLUDE_DIRS if p]

# ----- extension objects ----------------------------------------------------

def _ext(path: str, name: str):
    """Utility that turns a source path into an Extension with shared flags."""
    return Extension(
        name,
        [path],
        include_dirs     = INCLUDE_DIRS,
        library_dirs     = LIBRARY_DIRS + [sys.exec_prefix + "/lib"],
        libraries        = LIBRARIES,
        extra_compile_args = EXTRA_COMPILE_ARGS,
        extra_link_args    = EXTRA_LINK_ARGS,
        language = "c++",
    )

ext_modules = [
    _ext("source-cpp/pyBKT/generate/synthetic_data_helper.cpp",
         "pyBKT.generate.synthetic_data_helper"),
    _ext("source-cpp/pyBKT/fit/E_step.cpp",
         "pyBKT.fit.E_step"),
    _ext("source-cpp/pyBKT/fit/predict_onestep_states.cpp",
         "pyBKT.fit.predict_onestep_states"),
]

# For `python -m build`, setuptools will pick up ext_modules + cmdclass here
__all__ = ["ext_modules", "CustomBuildExtCommand"]
