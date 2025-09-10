import sympy

from measurekit.measurement.units import CompoundUnit


class SymbolicQuantity:
    def __init__(self, symbol_name: str, unit: CompoundUnit):
        self.symbol = sympy.Symbol(symbol_name)
        self.unit = unit

    def __repr__(self):
        return f"({self.symbol}) [{self.unit}]"

    # Sobrecargar operadores para que operen sobre los símbolos y las unidades
    def __mul__(self, other):
        new_symbol = self.symbol * other.symbol
        new_unit = self.unit * other.unit
        # Devolver un nuevo objeto simbólico que contiene la expresión
        return SymbolicExpression(new_symbol, new_unit)

    # ... implementar __add__, __truediv__, __pow__, etc. ...


class SymbolicExpression:
    def __init__(self, symbol: sympy.Expr, unit: CompoundUnit):
        self.symbol = symbol
        self.unit = unit

    def __repr__(self):
        return f"({self.symbol}) [{self.unit}]"

    # Sobrecargar operadores para que operen sobre los símbolos y las unidades
    def __mul__(self, other):
        new_symbol = self.symbol * other.symbol
        new_unit = self.unit * other.unit
        # Devolver un nuevo objeto simbólico que contiene la expresión
        return SymbolicExpression(new_symbol, new_unit)

    def __add__(self, other):
        new_symbol = self.symbol + other.symbol
        new_unit = self.unit
        # Comprobar que las dimensiones de ambos lados son compatibles
        if self.unit.dimension != other.unit.dimension:
            raise ValueError(
                "Las dimensiones de ambos lados de la suma no coinciden."
            )
        # Devolver un nuevo objeto simbólico que contiene la expresión
        return SymbolicExpression(new_symbol, new_unit)

    def __truediv__(self, other):
        new_symbol = self.symbol / other.symbol
        new_unit = self.unit / other.unit
        # Devolver un nuevo objeto simbólico que contiene la expresión
        return SymbolicExpression(new_symbol, new_unit)

    def __pow__(self, power):
        new_symbol = self.symbol**power
        new_unit = self.unit**power
        # Devolver un nuevo objeto simbólico que contiene la expresión
        return SymbolicExpression(new_symbol, new_unit)


class Equation:
    def __init__(self, lhs: SymbolicExpression, rhs: SymbolicExpression):
        # Comprobar que las dimensiones de ambos lados son compatibles
        if lhs.unit.dimension != rhs.unit.dimension:
            raise ValueError(
                "Las dimensiones de ambos lados de la ecuación no coinciden."
            )
        self.equation = sympy.Eq(lhs.symbol, rhs.symbol)
        self.lhs = lhs
        self.rhs = rhs

    def solve_for(self, symbol_to_solve: SymbolicQuantity):
        # Usar sympy para resolver la ecuación
        solution_expr = sympy.solve(self.equation, symbol_to_solve.symbol)[0]

        # Analizar la expresión resultante para deducir la nueva unidad
        # (Este es el paso más complejo, requiere un parser de expresiones de sympy)
        # ... lógica para determinar la unidad de la solución ...

        return SymbolicExpression(solution_expr, resulting_unit)
