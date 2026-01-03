from measurekit.domain.measurement.units import CompoundUnit

# SI Base Units
meter = CompoundUnit({"meter": 1})
kilogram = CompoundUnit({"kilogram": 1})
second = CompoundUnit({"second": 1})
ampere = CompoundUnit({"ampere": 1})
kelvin = CompoundUnit({"kelvin": 1})
mole = CompoundUnit({"mole": 1})
candela = CompoundUnit({"candela": 1})

# Common Derived Units
newton = CompoundUnit({"newton": 1})
joule = CompoundUnit({"joule": 1})
watt = CompoundUnit({"watt": 1})
pascal = CompoundUnit({"pascal": 1})
hertz = CompoundUnit({"hertz": 1})
coulomb = CompoundUnit({"coulomb": 1})
volt = CompoundUnit({"volt": 1})
ohm = CompoundUnit({"ohm": 1})

# Dimensionless
radian = CompoundUnit({"radian": 1})
steradian = CompoundUnit({"steradian": 1})
unity = CompoundUnit({})
