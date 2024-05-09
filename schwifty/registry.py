from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Union


try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore


Key = Union[str, tuple]
Value = Union[Dict[Key, Any], List[Dict[Key, Any]]]

_registry: dict[Key, Value] = {}


def merge_dicts(left: dict[Key, Any], right: dict[Key, Any]) -> dict[Key, Any]:
    merged = {}
    for key in frozenset(right) & frozenset(left):
        left_value, right_value = left[key], right[key]
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            merged[key] = merge_dicts(left_value, right_value)
        else:
            merged[key] = right_value

    for key, value in itertools.chain(left.items(), right.items()):
        if key not in merged:
            merged[key] = value
    return merged


def has(name: Key) -> bool:
    return name in _registry


def get(name: Key) -> Value:
    if has(name):
        return _registry[name]

    data = None
    directory = files(__package__) / f"{name}_registry"
    assert isinstance(directory, Path)
    for entry in sorted(directory.glob("*.json")):
        with entry.open(encoding="utf-8") as fp:
            chunk = json.load(fp)
            if data is None:
                data = chunk
            elif isinstance(data, list):
                data.extend(chunk)
            elif isinstance(data, dict):
                data = merge_dicts(data, chunk)
    if data is None:
        raise ValueError(f"Failed to load registry {name}")
    return save(name, data)


def save(name: Key, data: Value) -> Value:
    _registry[name] = data
    return data


def build_index(
    base_name: str,
    index_name: str,
    key: str | tuple[str, ...],
    accumulate: bool = False,
    **predicate: Any,
) -> None:
    def make_key(entry: dict[Key, Any]) -> tuple | str:
        return tuple(entry[k] for k in key) if isinstance(key, tuple) else entry[key]

    def match(entry: dict[Key, Any]) -> bool:
        return all(entry[key] == value for key, value in predicate.items())

    base = get(base_name)
    assert isinstance(base, list)
    if accumulate:
        data = defaultdict(list)
        for entry in base:
            if not match(entry):
                continue
            data[make_key(entry)].append(entry)
        save(index_name, dict(data))
    else:
        entries = {}
        for entry in base:
            if not match(entry):
                continue
            entries[make_key(entry)] = entry
        save(index_name, entries)


def manipulate(name: Key, func: Callable) -> None:
    registry = get(name)
    if isinstance(registry, dict):
        for key, value in registry.items():
            registry[key] = func(key, value)
    elif isinstance(registry, list):
        registry = [func(item) for item in registry]
    save(name, registry)
