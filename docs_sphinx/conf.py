"""Sphinx configuration for repo2xml API documentation."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "repo2xml"
author = "repo2xml contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
add_module_names = False

# Google-style docstrings.
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Use Python type hints from signatures, so docstrings don't need type repeats.
autodoc_typehints = "signature"

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]
