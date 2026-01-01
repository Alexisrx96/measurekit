### Fase 1: Blindaje de Tipos y Validación (Robustness Core)

El objetivo es que sea imposible usar mal la librería sin que el IDE o el linter griten.

#### 1.1. Integración "Blanda" de Pydantic V2

Implementar el shim para Pydantic en `measurekit/domain/measurement/quantity.py` para permitir validación de esquemas sin dependencias duras.

- **Acción de Código:** Añadir `__get_pydantic_core_schema__` en la clase `Quantity`.
- **Beneficio:** Permite usar `Quantity` directamente en modelos de FastAPI o Pydantic, serializando automáticamente unidades y valores.

#### 1.2. Adopción de `jaxtyping` para Tensores

Dado que soportas JAX y Torch, los type hints genéricos como `Any` en `dispatcher.py` son insuficientes. `jaxtyping` permite tipar formas y dtypes de tensores.

- **Acción de Código:**
- Añadir `jaxtyping` como dependencia opcional.
- Refactorizar `dispatcher.py` para usar protocolos tipados en lugar de `Any`.

```python
# En measurekit/core/protocols.py
from jaxtyping import Array, Float

class BackendOps(Protocol):
    def add(self, x: Float[Array, "..."], y: Float[Array, "..."]) -> Float[Array, "..."]: ...

```

- **Beneficio:** Detección estática de errores de dimensiones (ej. sumar un vector `[3]` con una matriz `[3, 3]`) antes de ejecutar.

#### 1.3. Migración a `uv` y Endurecimiento de Linting

Tu `pyproject.toml` ya usa `ruff`, pero podemos hacerlo más estricto para garantizar robustez.

- **Acción de Código:**
- Migrar de `Pipfile` a `pyproject.toml` completo gestionado por `uv` (el estándar moderno de facto).
- Activar reglas adicionales en `ruff` para seguridad y documentación:

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["E", "F", "UP", "B", "SIM", "I", "D", "N", "RUF", "TCH", "PT"]
# PT: flake8-pytest-style (mejores tests)
# TCH: flake8-type-checking (gestión de imports de tipos)
# RUF: Reglas específicas de Ruff (muy potentes)

```

---

### Fase 2: Testing Científico Avanzado (Robustness & QA)

Los tests unitarios simples (`assert a == b`) no son suficientes para física computacional. Necesitas "Property-Based Testing".

#### 2.1. Implementar `Hypothesis`

En lugar de escribir casos de prueba manuales (`1 + 1 = 2`), define propiedades matemáticas que deben cumplirse siempre (ej. conmutatividad, asociatividad).

- **Acción de Código:** Crear `tests/core/test_invariants.py`.

```python
from hypothesis import given, strategies as st
from measurekit import Q_

@given(st.floats(allow_nan=False), st.floats(allow_nan=False))
def test_addition_commutativity(a, b):
    q1 = Q_(a, "m")
    q2 = Q_(b, "m")
    assert q1 + q2 == q2 + q1

```

- **Beneficio:** `Hypothesis` encontrará casos borde (infinitos, ceros, números muy pequeños) que rompen tu lógica de unidades y que tú no pensaste.

#### 2.2. Benchmarking Continuo

Ya tienes scripts de benchmark (`benchmark_vectorized.py`), pero están aislados. Intégralos con `pytest-benchmark`.

- **Acción de Código:**
- Instalar `pytest-benchmark`.
- Convertir `benchmark_vectorized.py` en un test de pytest:

```python
def test_vectorized_propagation_speed(benchmark):
    # ... setup ...
    result = benchmark(lambda: q_array * 2)

```

- **Beneficio:** Detectar regresiones de rendimiento en cada PR automáticamente.

#### 2.3. Validación Cruzada de Backends

Asegurar que `numpy`, `torch` y `jax` den _exactamente_ el mismo resultado numérico.

- **Acción de Código:** Crear un parametrizador de pytest personalizado en `tests/conftest.py` que ejecute el mismo test matemático contra los 3 backends automáticamente.

---

### Fase 3: Documentación Viva (Evolution)

La documentación no debe ser solo texto en Markdown, debe estar viva y verificada por código.

#### 3.1. Doctests Estrictos

Tu código en `MK-001_Best_Practices.md` son ejemplos estáticos. Si cambias la API, los ejemplos quedarán obsoletos.

- **Acción de Código:**
- Habilitar `pytest --doctest-modules`.
- Mover los ejemplos de uso a los docstrings de las clases en formato REPL ejecutable.

```python
class Quantity:
    """
    ...
    Examples:
        >>> Q_(10, 'm') + Q_(5, 'm')
        Quantity(15, 'meter')
    """

```

#### 3.2. Automatización de Referencia de API con `mkdocstrings`

Ya tienes configurado `mkdocstrings` en `pyproject.toml`. Llévalo al siguiente nivel.

- **Acción de Código:**
- Crear/Configurar `mkdocs.yml` para usar el handler de python moderno.
- Usar referencias cruzadas en tus docstrings. En lugar de decir "Return a Quantity", usa "Returns: [measurekit.core.quantity.Quantity][]". `mkdocstrings` generará el enlace automáticamente.

#### 3.3. Tutoriales Ejecutables con `mkdocs-jupyter`

Para la documentación científica, los usuarios esperan notebooks.

- **Acción de Código:**
- Añadir `mkdocs-jupyter` a `pyproject.toml`.
- Escribir la documentación narrativa (como "How to use JAX with MeasureKit") directamente como archivos `.ipynb` en la carpeta `docs/`.
- Configurar el CI para ejecutar estos notebooks como tests antes de desplegar la doc (asegurando que la documentación nunca mienta).

### Resumen del Roadmap

| Prioridad | Tarea                                   | Archivos Afectados                     | Impacto                       | Estado |
| --------- | --------------------------------------- | -------------------------------------- | ----------------------------- | ------ |
| **Alta**  | **Integrar Pydantic V2 Shim**           | `quantity.py`                          | Interoperabilidad API moderna | ✅     |
| **Alta**  | **Migrar a `uv` y endurecer `ruff**`    | `pyproject.toml`, `Pipfile` (eliminar) | Calidad de código y DX        | ✅     |
| **Alta**  | **Adopción de `jaxtyping`**             | `backends/*.py`, `protocols.py`        | Seguridad de Tipos Tensores   | ✅     |
| **Media** | **Tests de Propiedades (`Hypothesis`)** | `tests/`                               | Robustez matemática crítica   | ✅     |
| **Media** | **Benchmarking Continuo**               | `tests/performance/`                   | Detección de Regresiones      | ✅     |
| **Media** | **Cross-Backend Testing**               | `tests/conftest.py`, `dispatcher.py`   | Consistencia numérica         | ✅     |
| **Baja**  | **Doctests & Notebooks CI**             | `docs/*.ipynb`, `core/*.py`            | Documentación siempre verde   | ✅     |
