"""repo2xml — bundle a repository into a single XML file for LLMs."""

# ruff: noqa F402
from beartype.claw import beartype_this_package

beartype_this_package()

from repo2xml.bundler import RepoBundler as RepoBundler
from repo2xml.bundler import bundle_repo as bundle_repo
