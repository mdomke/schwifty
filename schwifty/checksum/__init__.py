import abc
import enum
from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Type


class InputType(enum.Enum):
    BBAN = enum.auto()
    ACCOUNT_CODE = enum.auto()


class Algorithm(metaclass=abc.ABCMeta):
    name: ClassVar[str]
    accepts: ClassVar[InputType] = InputType.ACCOUNT_CODE

    @abc.abstractmethod
    def compute(self, account_code: str) -> str:
        pass

    @abc.abstractmethod
    def validate(self, account_code: str) -> bool:
        pass


algorithms: Dict[str, Algorithm] = {}


def register(algorithm_cls: Type[Algorithm], prefix: Optional[str] = None) -> Type[Algorithm]:
    key = algorithm_cls.name
    if prefix is not None:
        key = f"{prefix}:{key}"
    algorithms[key] = algorithm_cls()
    return algorithm_cls


from schwifty.checksum import belgium  # noqa
from schwifty.checksum import france  # noqa
from schwifty.checksum import germany  # noqa
from schwifty.checksum import italy  # noqa
