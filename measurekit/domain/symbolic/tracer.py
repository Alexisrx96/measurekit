import weakref
from typing import Any

from measurekit.domain.symbolic.graph import LeafNode, OpNode, SymbolicNode


class FormulaTracer:
    """Observer that tracks operations on Quantity objects and builds a symbolic graph.
    Uses WeakKeyDictionary to avoid memory leaks.
    """

    def __init__(self):
        # Maps Quantity instance to its SymbolicNode
        self._node_map: weakref.WeakKeyDictionary[Any, SymbolicNode] = (
            weakref.WeakKeyDictionary()
        )
        # Track symbolic names for convenience
        self._symbol_names: dict[SymbolicNode, str] = {}

    def register_leaf(self, quantity: Any, symbol: str):
        """Registers a Quantity as a named leaf in the symbolic graph."""
        node = LeafNode(
            symbol=symbol,
            unit_str=str(quantity.unit) if hasattr(quantity, "unit") else None,
        )
        self._node_map[quantity] = node
        self._symbol_names[node] = symbol

    def record_operation(
        self, op_name: str, operands: tuple[Any, ...], result: Any
    ):
        """Records an operation and its result in the symbolic graph."""
        arg_nodes = []
        for op in operands:
            node = self._node_map.get(op)
            if node is None:
                # If an operand is not traced, we might want to treat it as a constant
                # but for Phase 3 "Zero-Overhead", we only trace what's registered or derived.
                # However, if it's a scalar/non-Quantity, we could wrap it.
                # For now, if it's not in node_map, we skip tracing this branch or create a literal.
                if hasattr(op, "magnitude"):  # It's a Quantity but not traced
                    # We don't trace it to keep it zero-overhead
                    return
                # Literal support could be added here
                continue
            arg_nodes.append(node)

        if len(arg_nodes) == len(operands):
            # All operands are traced
            new_node = OpNode(op_name=op_name, args=tuple(arg_nodes))
            self._node_map[result] = new_node

    def get_node(self, quantity: Any) -> SymbolicNode | None:
        """Retrieves the symbolic node for a given quantity."""
        return self._node_map.get(quantity)

    def get_equation(self, quantity: Any) -> str:
        """Returns a LaTeX representation of the formula for the given quantity.
        Lazy-loads SymPy for translation.
        """
        node = self.get_node(quantity)
        if node is None:
            return ""

        from measurekit.domain.symbolic.export import SympyTranslator

        expr = SympyTranslator.translate(node)

        # If the quantity itself has a name/symbol, return Name = Formula
        # This is a bit tricky since the tracer doesn't necessarily know the "name"
        # of the result unless it was registered as a leaf later (which shouldn't happen for results).
        # We might want a way to tag results with symbols.

        import sympy

        return sympy.latex(expr)
