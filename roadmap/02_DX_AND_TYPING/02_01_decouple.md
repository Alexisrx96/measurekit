# Task: Eliminate Circular Dependencies

← [Phase 2 Overview](./02_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P1 (High — Affects maintainability and IDE support)

---

## Problem Statement

The codebase has circular import issues masked by lazy imports:

```
quantity.py → units.py → system.py → quantity.py (cycle!)
```

Current "solution": Import inside methods when needed.

---

## Identified Lazy Imports

| File          | Line | Import                                                               |
| ------------- | ---- | -------------------------------------------------------------------- |
| `quantity.py` | 204  | `import measurekit.domain.measurement.units`                         |
| `quantity.py` | 222  | `from measurekit.domain.measurement.uncertainty`                     |
| `quantity.py` | 242  | `from measurekit.domain.measurement.units import get_default_system` |
| `quantity.py` | 284  | `from measurekit.application.tracing.context`                        |
| `quantity.py` | 557  | `from measurekit.application.factories`                              |
| `quantity.py` | 572  | `from measurekit.application.startup`                                |
| `context.py`  | 108  | `# Lazy import to avoid top-level cycles`                            |

---

## Proposed Solution: Dependency Inversion

### Step 1: Create `measurekit.interfaces`

New package with abstract base classes:

```python
# measurekit/interfaces/__init__.py
from .quantity import QuantityProtocol
from .units import UnitProtocol, UnitSystemProtocol
from .uncertainty import UncertaintyProtocol
```

```python
# measurekit/interfaces/quantity.py
from typing import Protocol, Any

class QuantityProtocol(Protocol):
    @property
    def magnitude(self) -> Any: ...
    @property
    def unit(self) -> Any: ...
    @property
    def uncertainty(self) -> Any: ...
    def to(self, unit: str) -> "QuantityProtocol": ...
```

### Step 2: Domain Classes Implement Protocols

```python
# measurekit/domain/measurement/quantity.py
from measurekit.interfaces import QuantityProtocol

class Quantity(CoreQuantity, QuantityProtocol):
    ...
```

### Step 3: Inject Dependencies via Context

Instead of importing `get_default_system()` everywhere:

```python
# measurekit/application/context.py
_SYSTEM_CONTEXT: ContextVar[UnitSystemProtocol] = ContextVar("system")

def get_system() -> UnitSystemProtocol:
    return _SYSTEM_CONTEXT.get()
```

---

## Migration Strategy

1. **Phase A:** Create interfaces, don't change existing code
2. **Phase B:** Add protocol implementations to existing classes
3. **Phase C:** Replace lazy imports with DI one file at a time
4. **Phase D:** Delete lazy imports, verify no circular import errors

---

## Files to Create/Modify

| File                                        | Change                          |
| ------------------------------------------- | ------------------------------- |
| `measurekit/interfaces/__init__.py`         | NEW                             |
| `measurekit/interfaces/quantity.py`         | NEW                             |
| `measurekit/interfaces/units.py`            | NEW                             |
| `measurekit/domain/measurement/quantity.py` | Implement protocol, inject deps |
| `measurekit/application/context.py`         | Add system context              |

---

## Verification

1. `python -c "import measurekit"` — No import errors
2. Run full test suite: `pytest tests/`
3. `mypy measurekit/ --strict` — Check protocol compliance
4. `grep -r "import measurekit" measurekit/ | grep -v "^#" | grep -v TYPE_CHECKING` — Should only be top-level
