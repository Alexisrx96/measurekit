# Welcome to MeasureKit

MeasureKit is a high-performance physical dimension handling and unit conversion engine designed for modern scientific computing. It features **multi-backend support** (NumPy, JAX, PyTorch, Python), **static type safety** with `jaxtyping`, and **Pydantic integration**.

## Key Features

- **Multi-Backend Support**: Seamlessly switch between NumPy, JAX, PyTorch, and Python backends.
- **Type Safety**: Strictly typed tensor operations using `jaxtyping`.
- **Performance**: Optimized for speed with vectorized operations.
- **Pydantic Integration**: Easy validation and serialization using Pydantic V2.
- **Uncertainty Propagation**: Built-in support for handling measurement uncertainties.

## Installation

```bash
pip install measurekit
```

## Quick Start

```python
from measurekit.domain.measurement.quantity import Quantity as Q
from measurekit.domain.measurement.system import UnitSystem

# Initialize a standard unit system (usually done automatically via startup)
# For demonstration, we assume a system exists or use the default if configured.

# Create a quantity
q = Q(10, "m")
print(q)
# Output: Quantity(10, m)

# Convert units
q_km = q.to("km")
print(q_km)
# Output: Quantity(0.01, km)
```
