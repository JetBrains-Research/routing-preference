"""Loaders for characteristics and prompt templates."""

from .characteristic_loader import CharacteristicLoader, LoadedCharacteristic
from .prompt_loader import PromptLoader
from .xml_parser import strip_xml_tags

__all__ = [
    "CharacteristicLoader",
    "LoadedCharacteristic",
    "PromptLoader",
    "strip_xml_tags",
]
