"""Functional API for explicit covariance state management.

This module provides a functional interface for arithmetic operations on Quantities,
allowing the user to explicitly manage the covariance state (matrix) rather than
relying on a global context. This is essential for JAX transformations
(jit, vmap, pmap) and complex distributed scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from measurekit.domain.measurement.vectorized_uncertainty import (
    CovarianceStore,
    propagate_affine,
)

if TYPE_CHECKING:
    from measurekit.domain.measurement.quantity import Quantity

T = TypeVar("T")


class FunctionalState:
    """Holds the explicit state for functional propagation.

    Wraps the allocator (metadata) and the current covariance matrix (data).
    """

    def __init__(
        self,
        store: CovarianceStore | None = None,
        matrix: Any = None,
        registry: dict[int, slice] | None = None,
    ):
        """Initializes the functional state.

        Args:
            store: The covariance store allocator.
            matrix: The explicit covariance data matrix.
            registry: Mapping of object IDs to allocated slices.
        """
        if store is None:
            # Create a detached store (no global backend default)
            # We need a backend to init store?
            # We defer until first usage or require a backend.
            # Assuming numpy for default if totally empty
            from measurekit.backends.numpy_backend import NumpyBackend

            store = CovarianceStore(backend=NumpyBackend())
            store._ensure_initialized()

        self.store = store
        # If matrix is provided, it overrides the store's internal matrix
        # This allows 'threading' the matrix through JAX graph while
        # keeping the store allocator consistent.
        self.matrix = matrix if matrix is not None else store._matrix
        self.registry = registry if registry is not None else {}

    def allocate(self, size: int) -> slice:
        """Allocates a slice in the state (mutates allocator metadata)."""
        return self.store.allocate(size)

    def ensure_registered(self, q: Quantity) -> tuple[slice, Any]:
        """Ensures a quantity is registered in the state, updating matrix if needed.

        Returns:
            (slice, updated_matrix)
        """
        # Checks if quantity already has a vector_slice
        # If not, allocates and updates matrix (diagonal variance)

        key = id(q.uncertainty_obj)
        if key in self.registry:
            return self.registry[key], self.matrix

        # Access internal Uncertainty
        unc = q.uncertainty_obj
        from measurekit.domain.measurement.uncertainty import CovarianceModel

        backend = self.store.backend

        # If already has slice (and we assume it matches this state's timeline)
        # We can't easily verify if the slice belongs to *this* state
        # without unique IDs.
        # But if user is consistent, it should be fine.
        if isinstance(unc, CovarianceModel) and unc.vector_slice is not None:
            # Check if slice is within current allocated range?
            # For now assume yes.
            return unc.vector_slice, self.matrix

        # Need to register
        val = backend.asarray(q.uncertainty)
        size = backend.size(val)
        slc = self.allocate(size)  # Mutation of allocator

        # Calculate Variance Diag
        diag_val = backend.reshape(backend.pow(val, 2), (-1,))
        variance = backend.sparse_diags([diag_val], [0], shape=(size, size))

        # Append to matrix
        # matrix = bmat([[current, 0], [0, variance]])
        if self.matrix is None:
            new_matrix = variance
        else:
            # Check if matrix is empty/zero-shape
            if hasattr(self.matrix, "shape") and self.matrix.shape == (0, 0):
                new_matrix = variance
            else:
                new_matrix = backend.sparse_bmat(
                    [[self.matrix, None], [None, variance]]
                )

        self.registry[key] = slc
        return slc, new_matrix


def add(
    a: Quantity, b: Quantity, state: FunctionalState
) -> tuple[Quantity, FunctionalState]:
    """Functional addition: (a + b, new_state)."""
    return _apply_affine(a, b, state, 1.0, 1.0)


def sub(
    a: Quantity, b: Quantity, state: FunctionalState
) -> tuple[Quantity, FunctionalState]:
    """Functional subtraction: (a - b, new_state)."""
    return _apply_affine(a, b, state, 1.0, -1.0)


def _apply_affine(
    a: Quantity,
    b: Quantity,
    state: FunctionalState,
    jac_a: float,
    jac_b: float,
) -> tuple[Quantity, FunctionalState]:
    """Helper for affine operations."""
    backend = state.store.backend

    # 1. Register inputs in state
    slc_a, mat_1 = state.ensure_registered(a)
    state.matrix = mat_1  # Update intermediate

    slc_b, mat_2 = state.ensure_registered(b)
    state.matrix = mat_2

    # 2. Compute Result Magnitude
    # Naive addition for now, assumes clean units or let Quantity handle it?
    # Quantity.to() logic might be needed before add.
    # Assuming units match for this low-level func, or we use a.unit logic.
    # Simple magnitude op:
    res_mag = (
        backend.add(a.magnitude, b.magnitude)
        if jac_b > 0
        else backend.sub(a.magnitude, b.magnitude)
    )

    # 3. Propagate
    out_size = backend.size(res_mag)
    out_slice = state.allocate(out_size)

    # Jacobians are identity/scalar for add/sub
    # We need to broadcast them if they are scalar.
    # propagate_affine expects array-like or sparse jacobians usually?
    # The logic in propagate_affine handles 'asarray'.

    # Construct Jacobians
    # Assumes element-wise operation (diagonal jacobian)

    val_a_ones = backend.ones((out_size,), reference=res_mag)
    # If jac_a is scalar, broadcast
    diag_a = backend.mul(val_a_ones, jac_a)
    j_a = backend.sparse_diags([diag_a], [0], shape=(out_size, out_size))

    val_b_ones = backend.ones((out_size,), reference=res_mag)
    diag_b = backend.mul(val_b_ones, jac_b)
    j_b = backend.sparse_diags([diag_b], [0], shape=(out_size, out_size))

    jacs = [j_a, j_b]

    new_matrix = propagate_affine(
        state.matrix, out_slice, [slc_a, slc_b], jacs, backend
    )

    # 4. Construct Result Quantity
    from measurekit.domain.measurement.uncertainty import CovarianceModel

    # Extract new std_dev from diagonal
    # This might require sparse slicing or getting diagonal
    # For JAX compatibility, getting diagonal of a sparse matrix might be tricky?
    # BCOO diagonal?
    # BackendOps should support sparse_diagonal.

    # In JAX/Functional, we might lazy-evaluate std_dev?
    # But Quantity expects an uncertainty object.

    # Note: Retrieving the diagonal here involves reading the properties
    # of the result matrix.
    # new_matrix is the state.

    # result block
    # We can't easily extract just the block without backend support.
    # But diagonal extraction is usually supported.
    # Let's assume we can get full diagonal.
    diag = backend.sparse_diagonal(new_matrix)  # Returns dense vector of diag

    # Slice it
    # JAX/Numpy slicing
    res_diag = diag[out_slice]
    res_std = backend.sqrt(res_diag)
    res_std = backend.reshape(res_std, backend.shape(res_mag))

    # Result Uncertainty
    res_unc = CovarianceModel(
        std_dev_internal=res_std,
        vector_slice=out_slice,
        # Lineage is empty/irrelevant for vectorized
    )

    # Result Quantity
    # Helper to construct
    res_q = a._fast_new(
        res_mag,
        a.unit,  # Assuming unit match
        res_unc,
        a.system,
        a.dimension,
        backend,
    )

    return res_q, FunctionalState(state.store, new_matrix, state.registry)
