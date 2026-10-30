import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json(path: str | Path, data: Any, **kwargs: Any) -> None:
    """Write ``data`` as JSON to ``path`` without ever leaving a truncated file behind.

    ``with open(path, "w") as fp: json.dump(process(), fp)`` truncates the target before
    ``process()`` runs, so any error while fetching or parsing wipes the existing registry.
    Instead, the data is serialized first and written to a temporary file in the same
    directory, which then atomically replaces the target.
    """
    path = Path(path)
    content = json.dumps(data, **kwargs)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            fp.write(content)
        # mkstemp creates the file as 0600; keep the permissions of the file we replace.
        os.chmod(tmp, path.stat().st_mode if path.exists() else 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
