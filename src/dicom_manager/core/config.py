# DICOM-Manager - Config file handler.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from configparser import ConfigParser
import json
from pathlib import Path
import tomllib


def load_values(path: Path) -> dict[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    elif suffix == ".toml":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        data = data.get("values", data)
    elif suffix in {".ini", ".cfg"}:
        parser = ConfigParser()
        parser.optionxform = str
        parser.read(path, encoding="utf-8")
        if not parser.sections():
            raise ValueError("INI configuration has no section")
        section = "values" if parser.has_section("values") else parser.sections()[0]
        data = dict(parser[section])
    else:
        raise ValueError("--from-file supports .json, .toml, .ini and .cfg")
    if not isinstance(data, dict):
        raise ValueError("Configuration must contain a key/value object")
    return {str(k): str(v) for k, v in data.items()}


def write_template(path: Path, values: dict[str, str]) -> None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    elif suffix == ".toml":
        lines = ["[values]"] + [f'{k} = {json.dumps(v)}' for k, v in values.items()]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif suffix in {".ini", ".cfg"}:
        lines = ["[values]"] + [f"{k} = {v}" for k, v in values.items()]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        raise ValueError("Template format must be json, toml or ini")
