"""Resolve explicitly configured local Python implementations."""
from importlib import import_module


def load_component(reference):
    module, separator, attribute = reference.partition(":")
    if not separator or not module or not attribute:
        raise ValueError("Component must be module.path:attribute")
    return getattr(import_module(module), attribute)
