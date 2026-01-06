import measurekit_core

# Test 1: Create a unit
u = measurekit_core.RationalUnit({"length": (1, 3)})  # Length^(1/3)
print(f"Created: {u}")

# Test 2: Multiply
u2 = measurekit_core.RationalUnit({"length": (2, 3)})  # Length^(2/3)
res = u.multiply(u2)
print(f"Result (Should be length^1/1): {res}")
