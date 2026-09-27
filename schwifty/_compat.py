"""Re-export stdlib symbols that are missing on the oldest supported Python.

``typing.override`` exists only from 3.12 onward; on 3.11 we use
``typing_extensions`` (see the conditional dependency in pyproject.toml).
"""

import sys


if sys.version_info >= (3, 12):
    from typing import override as override  # noqa: PLC0414
else:
    from typing_extensions import override as override  # noqa: PLC0414


__all__ = ["override"]
