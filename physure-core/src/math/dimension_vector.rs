use num_rational::Rational64;
use std::ops::{Add, Sub, Mul};

/// Standard SI base dimension index enum (7 fundamental dimensions).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BaseDimension {
    Length = 0,
    Mass = 1,
    Time = 2,
    ElectricCurrent = 3,
    ThermodynamicTemperature = 4,
    AmountOfSubstance = 5,
    LuminousIntensity = 6,
}

/// A 7-dimensional vector over Rational numbers representing physical dimensions as a Vector Space over Q^7.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Copy)]
pub struct DimensionVector {
    pub exponents: [Rational64; 7],
}

impl DimensionVector {
    pub fn dimensionless() -> Self {
        DimensionVector {
            exponents: [Rational64::new(0, 1); 7],
        }
    }

    pub fn base(dim: BaseDimension) -> Self {
        let mut exponents = [Rational64::new(0, 1); 7];
        exponents[dim as usize] = Rational64::new(1, 1);
        DimensionVector { exponents }
    }

    pub fn is_dimensionless(&self) -> bool {
        self.exponents.iter().all(|r| *r.numer() == 0)
    }

    pub fn get(&self, dim: BaseDimension) -> Rational64 {
        self.exponents[dim as usize]
    }

    pub fn set(&mut self, dim: BaseDimension, val: Rational64) {
        self.exponents[dim as usize] = val;
    }

    /// Inner product (dot product) of dimension vectors in Q^7 vector space.
    pub fn dot(&self, other: &Self) -> Rational64 {
        let mut sum = Rational64::new(0, 1);
        for i in 0..7 {
            sum = sum + (self.exponents[i] * other.exponents[i]);
        }
        sum
    }

    /// Squared L2 norm of the dimension exponents vector.
    pub fn norm_sq(&self) -> Rational64 {
        self.dot(self)
    }
}

impl Add for DimensionVector {
    type Output = Self;
    fn add(self, rhs: Self) -> Self::Output {
        let mut exponents = [Rational64::new(0, 1); 7];
        for i in 0..7 {
            exponents[i] = self.exponents[i] + rhs.exponents[i];
        }
        DimensionVector { exponents }
    }
}

impl Sub for DimensionVector {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self::Output {
        let mut exponents = [Rational64::new(0, 1); 7];
        for i in 0..7 {
            exponents[i] = self.exponents[i] - rhs.exponents[i];
        }
        DimensionVector { exponents }
    }
}

impl Mul<Rational64> for DimensionVector {
    type Output = Self;
    fn mul(self, rhs: Rational64) -> Self::Output {
        let mut exponents = [Rational64::new(0, 1); 7];
        for i in 0..7 {
            exponents[i] = self.exponents[i] * rhs;
        }
        DimensionVector { exponents }
    }
}
