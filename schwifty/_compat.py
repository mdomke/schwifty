import sys


if sys.version_info >= (3, 12):
    from typing import override as override  # noqa: PLC0414
else:
    from typing_extensions import override as override  # noqa: PLC0414


__all__ = ["override"]
