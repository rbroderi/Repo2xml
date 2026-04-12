import importlib


def test_package_importable() -> None:
    module = importlib.import_module("repo2xml")
    assert module is not None
