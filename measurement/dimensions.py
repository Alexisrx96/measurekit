from dataclasses import dataclass
from typing import ClassVar, cast

from notation.lexer import generate_tokens, to_superscript
from notation.parsers import (
    NotationParser,
)
from notation.typing import ExponentsDict


@dataclass(frozen=True)
class Dimension:
    _cache: ClassVar[dict[tuple, "Dimension"]] = {}

    exponents: ExponentsDict

    def __new__(cls, exponents: ExponentsDict) -> "Dimension":
        normalized = {k: v for k, v in exponents.items() if v != 0}
        key = tuple(sorted(normalized.items()))
        if key in cls._cache:
            return cls._cache[key]
        instance = super().__new__(cls)
        object.__setattr__(instance, "exponents", normalized)
        cls._cache[key] = instance
        return instance

    def __init__(self, exponents: ExponentsDict) -> None:
        pass

    def __mul__(self, other: "Dimension") -> "Dimension":
        new_exponents = {**self.exponents}  # Ensure immutability
        for key, exp in other.exponents.items():
            new_exponents[key] = new_exponents.get(key, 0) + exp
        return Dimension(new_exponents)

    def __truediv__(self, other: "Dimension") -> "Dimension":
        new_exponents = {**self.exponents}
        for key, exp in other.exponents.items():
            new_exponents[key] = new_exponents.get(key, 0) - exp
        return Dimension(new_exponents)

    def __pow__(self, power: int | float) -> "Dimension":
        return Dimension({k: v * power for k, v in self.exponents.items()})

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dimension):
            return NotImplemented
        return self.exponents == other.exponents

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.exponents.items())))

    def __rtruediv__(self, other: float | int | complex) -> "Dimension":
        """Allows division where a scalar is divided by a Dimension
        (inverse)."""
        return Dimension({k: -v for k, v in self.exponents.items()})

    def __str__(self) -> str:
        """Returns a user-friendly representation with superscripts."""
        parts = []
        for key, exp in sorted(self.exponents.items()):
            if exp == 1:
                parts.append(key)
            else:
                parts.append(f"{key}{to_superscript(exp)}")
        return "·".join(parts) if parts else "1"

    def __repr__(self) -> str:
        return str(self.exponents)


def get_dimension(unit_expression: str) -> Dimension:
    tokens = generate_tokens(unit_expression)
    parser = NotationParser(tokens, Dimension)
    return cast(Dimension, parser.parse())
