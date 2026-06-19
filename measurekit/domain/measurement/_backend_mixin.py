"""NumPy and PyTorch integration mixin for Quantity."""
from __future__ import annotations

import operator
from typing import Any

from typing_extensions import Self

from measurekit.domain.exceptions import IncompatibleUnitsError
from measurekit.domain.measurement.uncertainty import Uncertainty
from measurekit.domain.measurement.units import CompoundUnit

_Quantity = None


def _q():
    global _Quantity
    if _Quantity is None:
        from measurekit.domain.measurement.quantity import Quantity as _Q
        _Quantity = _Q
    return _Quantity


class BackendMixin:
    """NumPy ufunc/function and PyTorch function dispatch methods."""

    # --- NumPy Integration (Soft Dependency) ---
    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        """Handles NumPy ufuncs by delegating to the backend."""
        try:
            import numpy as np
        except ImportError:
            return NotImplemented

        # Handle reductions (e.g. np.sum which calls np.add.reduce)
        if method == "reduce":
            if ufunc == np.add:
                inp = inputs[0]
                if isinstance(inp, _q()):
                    res_mag = self._backend.sum(
                        inp.magnitude, axis=kwargs.get("axis")
                    )
                    return type(self).from_input(res_mag, inp.unit, self.system)
            return NotImplemented

        if method != "__call__":
            return NotImplemented

        # Standard Dispatch
        if ufunc == np.add:
            val = inputs[1] if inputs[0] is self else inputs[0]
            if isinstance(val, _q()) and self.unit != val.unit:
                if self.dimension != val.dimension:
                    raise IncompatibleUnitsError(self.unit, val.unit)
            return self.__add__(val)
        if ufunc == np.subtract:
            val = inputs[1] if inputs[0] is self else inputs[0]
            if isinstance(val, _q()) and self.unit != val.unit:
                if self.dimension != val.dimension:
                    raise IncompatibleUnitsError(self.unit, val.unit)
            if inputs[0] is self:
                return self.__sub__(val)
            return self.__rsub__(val)
        if ufunc == np.multiply:
            val = inputs[1] if inputs[0] is self else inputs[0]
            return self.__mul__(val)
        if ufunc == np.true_divide:
            if inputs[0] is self:
                return self.__truediv__(inputs[1])
            return self.__rtruediv__(inputs[0])
        if ufunc == np.power and inputs[0] is self:
            return self.__pow__(inputs[1])

        # Unary math that changes unit
        if ufunc == np.sqrt:
            return self**0.5
        if ufunc == np.square:
            return self**2

        # Unary math that preserves unit
        if ufunc == np.absolute:
            return abs(self)

        # Trig functions (Require dimensionless)
        trig_names = (
            "sin",
            "cos",
            "tan",
            "exp",
            "log",
            "log10",
            "arcsin",
            "arccos",
            "arctan",
            "tanh",
            "sinh",
            "cosh",
        )
        if ufunc.__name__ in trig_names:
            inp = inputs[0]
            if isinstance(inp, _q()):
                if not inp.dimension.is_dimensionless:
                    raise IncompatibleUnitsError(inp.unit, CompoundUnit({}))

                # Use numeric value if dimensionless
                # Convert to float/array to strip Quantity wrapper which causes infinite recursion in ufunc
                mag = inp.magnitude
                res_mag = ufunc(mag, **kwargs)
                u_inp = inp._numeric_std_dev
                has_unc = inp._has_uncertainty

                if has_unc:
                    # Propagate uncertainty using numerical derivative
                    h = 1e-7
                    # Ensure same backend for perturbation
                    m_plus = inp._backend.add(inp.magnitude, h)
                    m_minus = inp._backend.sub(inp.magnitude, h)

                    try:
                        # Estimate derivative
                        der = inp._backend.truediv(
                            inp._backend.sub(ufunc(m_plus), ufunc(m_minus)),
                            2 * h,
                        )
                        res_unc = inp._backend.mul(
                            inp._backend.abs(der), u_inp
                        )
                        return type(self).from_input(
                            res_mag,
                            CompoundUnit({}),
                            self.system,
                            uncertainty=res_unc,
                        )
                    except Exception:
                        # Conservative fallback for complex backends
                        return type(self).from_input(
                            res_mag,
                            CompoundUnit({}),
                            self.system,
                            uncertainty=u_inp,
                        )
                else:
                    return type(self).from_input(
                        res_mag, CompoundUnit({}), self.system
                    )

        return NotImplemented

    def __array_function__(self, func, types, args, kwargs):
        """Handles NumPy functions like np.concatenate, np.mean."""
        try:
            import numpy as np
        except ImportError:
            return NotImplemented

        if func == np.concatenate:
            mags = []
            unit = None
            for arg in args[0]:
                if isinstance(arg, _q()):
                    if unit is None:
                        unit = arg.unit
                    elif arg.unit != unit:
                        return NotImplemented  # Strict unit check
                    mags.append(arg.magnitude)
                else:
                    return NotImplemented  # All must be Quantity for now
            res_mag = np.concatenate(mags, **kwargs)
            return type(self)(res_mag, unit, system=self.system)

        if func == np.mean:
            # args[0] is self usually
            q = args[0]
            if isinstance(q, _q()):
                return type(self)(
                    np.mean(q.magnitude, **kwargs), q.unit, system=q.system
                )

        return NotImplemented

    def __torch_function__(self, func, types, args=(), kwargs=None):
        """Handles Torch functions like torch.mean, torch.relu."""
        if kwargs is None:
            kwargs = {}

        import torch

        # Helper to unwrap Quantities
        def unwrap(obj):
            if isinstance(obj, _q()):
                return obj.magnitude
            if isinstance(obj, (list, tuple)):
                return type(obj)(unwrap(x) for x in obj)
            return obj

        # --- Dispatch Logic ---
        # Map common torch functions to Quantity operators or functional logic

        # Arithmetic -> Delegate to operators to preserve uncertainty logic
        if func in (torch.add,):
            return operator.add(args[0], args[1])  # type: ignore
        if func in (torch.sub,):
            return operator.sub(args[0], args[1])  # type: ignore
        if func in (torch.mul,):
            return operator.mul(args[0], args[1])  # type: ignore
        if func in (torch.div, torch.true_divide):
            return operator.truediv(args[0], args[1])  # type: ignore
        if func in (torch.pow,):
            return operator.pow(args[0], args[1])  # type: ignore

        # Unary Math -> Check Dimensionless
        # (Sin, Cos, Exp, Log...)
        trig_map = {
            torch.sin: torch.sin,
            torch.cos: torch.cos,
            torch.tan: torch.tan,
            torch.exp: torch.exp,
            torch.log: torch.log,
            torch.log10: torch.log10,
            torch.abs: torch.abs,
            torch.sqrt: torch.sqrt,
        }

        if func in trig_map:
            q = args[0]
            if not isinstance(q, _q()):
                return NotImplemented

            # sqrt is special (unit becomes u^0.5)
            if func == torch.sqrt:
                return q**0.5

            # abs preserves unit
            if func == torch.abs:
                return abs(q)

            # Others require dimensionless
            if not q.dimension.is_dimensionless:
                raise IncompatibleUnitsError(q.unit, CompoundUnit({}))

            # Result is dimensionless
            res_mag = func(q.magnitude, **kwargs)
            # Create dimensionless quantity
            return type(self).from_input(res_mag, CompoundUnit({}), q.system)

        # Fallback: Unwrap -> Call -> Wrap (Blind wrapping)
        # This is dangerous for operations that change units, but acceptable for
        # shape ops (reshape, transpose) or generic tensor ops.

        unwrapped_args = tuple(unwrap(arg) for arg in args)
        unwrapped_kwargs = {k: unwrap(v) for k, v in kwargs.items()}

        result = func(*unwrapped_args, **unwrapped_kwargs)

        # If result is Tensor, try to wrap it using the first Quantity's unit
        # This is heuristic and might be wrong for some ops.
        # But it enables things like 'torch.unsqueeze(q)' to work.
        source_q = next(
            (arg for arg in args if isinstance(arg, _q())), None
        )

        if source_q is not None and isinstance(result, torch.Tensor):
            return type(self).from_input(result, source_q.unit, source_q.system)

        return result

    def to_device(self, device: str) -> Self:
        """Moves the quantity and its uncertainty to the specified device."""
        new_mag = self._backend.to_device(self.magnitude, device)
        new_unc_val = self._backend.to_device(self.uncertainty, device)
        new_unc = Uncertainty.from_standard(new_unc_val)

        return self._fast_new(
            new_mag,
            self.unit,
            new_unc,
            self.system,
            self.dimension,
            self._backend,
        )

    def backward(self, *args, **kwargs) -> None:
        """Delegates autograd backward call to the underlying magnitude."""
        if hasattr(self.magnitude, "backward"):
            self.magnitude.backward(*args, **kwargs)
        else:
            raise TypeError(
                f"Backend magnitude {type(self.magnitude)} no backward()"
            )

    # --- Representation ---

