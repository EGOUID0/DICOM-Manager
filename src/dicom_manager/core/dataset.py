# DICOM-Manager - Dataset handler.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from pydicom.datadict import tag_for_keyword
from pydicom.tag import Tag


def resolve_tag(value: str):
    tag = tag_for_keyword(value)
    if tag is not None:
        return Tag(tag)
    cleaned = value.replace("(", "").replace(")", "").replace(",", "").replace(" ", "")
    if len(cleaned) == 8:
        try:
            return Tag(int(cleaned, 16))
        except ValueError:
            pass
    raise ValueError(f"Unknown DICOM keyword/tag: {value}")


def change_tag_value(dataset, tag, new_value) -> int:
    tag = Tag(tag)
    changed = 0
    for element in dataset:
        if element.VR == "SQ":
            for item in element.value:
                changed += change_tag_value(item, tag, new_value)
        elif element.tag == tag:
            element.value = new_value
            changed += 1
    return changed


def apply_values(dataset, values: dict[str, str]) -> dict[str, int]:
    result = {}
    for key, value in values.items():
        tag = resolve_tag(key)
        result[key] = change_tag_value(dataset, tag, value)
    return result
