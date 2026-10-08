"""Map capability folders to stable import names in a source checkout.

Installed wheels use ``pyproject.toml`` ``package-dir``. Source runs
(``python install.py``, pytest without a rebuilt editable install) use this
finder so public imports stay the same:

* ``knowledge``
* ``pipeline_plugins``
* ``pipeline_features``
* ``pipeline_observability``
* ``pipeline_eval``
* ``pipeline_orchestrator``
* ``pipeline_docs``
* ``pipeline_kit.paths`` / ``pipeline_kit.license`` (root modules)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCE_PACKAGES = {
    "knowledge": ROOT / "capabilities" / "knowledge",
    "pipeline_plugins": ROOT / "capabilities" / "plugins",
    "pipeline_features": ROOT / "capabilities" / "feature_flags",
    "pipeline_observability": ROOT / "capabilities" / "observability",
    "pipeline_eval": ROOT / "capabilities" / "eval",
    "pipeline_orchestrator": ROOT / "orchestrator",
    "pipeline_docs": ROOT / "capabilities" / "docs",
}


class SourcePackageFinder:
    def __init__(self, mapping: dict[str, Path]):
        self.mapping = {name: path for name, path in mapping.items() if path.is_dir()}

    def find_spec(self, fullname, path=None, target=None):  # noqa: ARG002
        top = fullname.split(".", 1)[0]
        root = self.mapping.get(top)
        if root is None:
            return None
        if fullname == top:
            init = root / "__init__.py"
            if not init.is_file():
                return None
            return importlib.util.spec_from_file_location(
                fullname,
                init,
                submodule_search_locations=[str(root)],
            )
        rel = fullname[len(top) + 1 :].replace(".", "/")
        file_py = root / f"{rel}.py"
        if file_py.is_file():
            return importlib.util.spec_from_file_location(fullname, file_py)
        package_dir = root / rel
        init = package_dir / "__init__.py"
        if init.is_file():
            return importlib.util.spec_from_file_location(
                fullname,
                init,
                submodule_search_locations=[str(package_dir)],
            )
        return None


class PipelineKitFinder:
    """Expose ``pipeline_kit.*`` root modules from a source checkout.

    The wheel maps the ``pipeline_kit`` package onto this repo root. A source
    run has no ``pipeline_kit/`` directory, so this finder serves the package
    init plus root modules such as ``license`` and ``paths``.
    """

    # Root-level modules that belong to the pipeline_kit package (package-dir = ".")
    _MODULES = {
        "install": "install.py",
        "layout": "layout.py",
        "license": "license.py",
        "paths": "paths.py",
    }

    def find_spec(self, fullname, path=None, target=None):  # noqa: ARG002
        if fullname == "pipeline_kit":
            init = ROOT / "__init__.py"
            if not init.is_file():
                return None
            return importlib.util.spec_from_file_location(
                fullname,
                init,
                submodule_search_locations=[str(ROOT)],
            )
        if fullname.startswith("pipeline_kit."):
            leaf = fullname.split(".", 1)[1]
            if "." in leaf:
                return None
            filename = self._MODULES.get(leaf)
            if not filename:
                # Allow any existing root .py so package-dir="." stays consistent
                candidate = ROOT / f"{leaf}.py"
            else:
                candidate = ROOT / filename
            if candidate.is_file():
                return importlib.util.spec_from_file_location(fullname, candidate)
        return None


_installed = False


def install_source_importers() -> None:
    """Register folder→import mappings when this tree is a kit checkout."""
    global _installed
    if _installed:
        return
    mapping = {name: path for name, path in SOURCE_PACKAGES.items() if path.is_dir()}
    if not mapping:
        return
    sys.meta_path.insert(0, PipelineKitFinder())
    sys.meta_path.insert(0, SourcePackageFinder(mapping))
    _installed = True
