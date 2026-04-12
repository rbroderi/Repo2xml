"""repo2xml — bundle a repository into a single XML file for LLMs."""

from repo2xml._bundler import RepoBundler
from repo2xml._bundler import bundle_repo

__all__ = ["RepoBundler", "bundle_repo"]
