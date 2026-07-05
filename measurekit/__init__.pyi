# measurekit/__init__.pyi
# Typing stub for the main entry point of MeasureKit.

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from measurekit.application.factories import QuantityFactory
from measurekit.core.registry import UnitRegistry as UnitRegistry
from measurekit.domain.exceptions import (
    ConversionError as ConversionError,
)
from measurekit.domain.exceptions import (
    MeasureKitError as MeasureKitError,
)
from measurekit.domain.exceptions import (
    UnitNotFoundError as UnitNotFoundError,
)
from measurekit.domain.exceptions import (
    UnknownUnitError as UnknownUnitError,
)
from measurekit.domain.measurement.equivalencies import (
    equivalencies as equivalencies,
)
from measurekit.domain.measurement.equivalencies import (
    spectral as spectral,
)
from measurekit.domain.measurement.equivalencies import (
    thermodynamic as thermodynamic,
)
from measurekit.domain.measurement.quantity import Quantity as Quantity
from measurekit.domain.measurement.system import UnitSystem as UnitSystem
from measurekit.domain.measurement.uncertainty import (
    Uncertainty as Uncertainty,
)
from measurekit.domain.measurement.units import CompoundUnit as CompoundUnit
from measurekit.domain.measurement.vectorized_uncertainty import (
    MeasureKitContext as MeasureKitContext,
)
from measurekit.domain.measurement.vectorized_uncertainty import (
    PruningConfig as PruningConfig,
)

Q_: QuantityFactory
default_system: UnitSystem
units: UnitRegistry

def create_default_system() -> UnitSystem: ...
def create_system(config_path_or_name: str) -> UnitSystem: ...
def get_active_system() -> UnitSystem: ...
def get_current_system() -> UnitSystem: ...
def get_unit(unit_expression: str | CompoundUnit) -> CompoundUnit: ...
def jit(func: Callable[..., Any]) -> Callable[..., Any]: ...
def load_state(filepath: str | Path) -> None: ...
def save_state(filepath: str | Path, protocol: int = ...) -> None: ...
def system_context(
    system_name_or_obj: str | UnitSystem,
) -> AbstractContextManager[None]: ...
def uncertainty_mode(
    mode: str, **kwargs: Any
) -> AbstractContextManager[None]: ...

# For the configuration proxy
class _ConfigProxy:
    @property
    def propagation_mode(
        self,
    ) -> Callable[[str], AbstractContextManager[None]]: ...
    def set_propagation_mode(
        self, mode: str
    ) -> AbstractContextManager[None]: ...

config: _ConfigProxy

__all__ = [
    "Q_",
    "CompoundUnit",
    "ConversionError",
    "MeasureKitContext",
    "MeasureKitError",
    "PruningConfig",
    "Quantity",
    "Uncertainty",
    "UnitNotFoundError",
    "UnknownUnitError",
    "create_default_system",
    "create_system",
    "default_system",
    "equivalencies",
    "get_active_system",
    "get_current_system",
    "get_unit",
    "jit",
    "load_state",
    "save_state",
    "spectral",
    "system_context",
    "thermodynamic",
    "uncertainty_mode",
    "units",
]
