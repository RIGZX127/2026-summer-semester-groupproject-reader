# platform/__init__.py
"""Mercury platform abstraction package.

NOTE: This package shadows the stdlib `platform` module.
We re-export all stdlib symbols here so that tools like pytest
that rely on `platform.python_version()` continue to work correctly.
"""
from __future__ import annotations

import importlib.util
import sysconfig

# Load the real stdlib platform module by file path to avoid circular import.
_stdlib_dir = sysconfig.get_path("stdlib")
_platform_path = f"{_stdlib_dir}/platform.py"

_spec = importlib.util.spec_from_file_location("_stdlib_platform", _platform_path)
_stdlib_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stdlib_mod)

# Expose all stdlib platform attributes in this namespace.
python_version = _stdlib_mod.python_version
python_version_tuple = _stdlib_mod.python_version_tuple
uname = _stdlib_mod.uname
system = _stdlib_mod.system
node = _stdlib_mod.node
release = _stdlib_mod.release
version = _stdlib_mod.version
machine = _stdlib_mod.machine
processor = _stdlib_mod.processor
architecture = _stdlib_mod.architecture
platform = _stdlib_mod.platform

# Also copy everything for wildcard imports.
for _k, _v in vars(_stdlib_mod).items():
    if not _k.startswith("__"):
        globals()[_k] = _v

del _k, _v, _spec, _stdlib_mod, _stdlib_dir, _platform_path