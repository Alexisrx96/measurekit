use super::*;
use sprs::TriMat;
use num_rational::Rational64;
use ndarray::{array, Array2};

#[test]
fn test_sparse_sandwich_identity() {
    let n = 3;
    let mut tri = TriMat::new((n, n));
    for i in 0..n {
        tri.add_triplet(i, i, 1.0);
    }
    let identity = tri.to_csc();
    let res = sparse_sandwich(&identity, &identity);
    for i in 0..n {
        assert_eq!(res.get(i, i), Some(&1.0));
    }
}

#[test]
fn test_dimension_vector_vector_space_properties() {
    let length = DimensionVector::base(BaseDimension::Length);
    let time = DimensionVector::base(BaseDimension::Time);
    let speed = length - time;

    assert_eq!(speed.get(BaseDimension::Length), Rational64::new(1, 1));
    assert_eq!(speed.get(BaseDimension::Time), Rational64::new(-1, 1));
    assert_eq!(speed.norm_sq(), Rational64::new(2, 1));

    let acceleration = speed - time;
    assert_eq!(acceleration.get(BaseDimension::Time), Rational64::new(-2, 1));
}

#[test]
fn test_dual_number_automatic_differentiation() {
    // f(x) = x^2 + sin(x)
    // f'(x) = 2x + cos(x)
    let x = DualNumber::variable(2.0);
    let y = x.powf(2.0) + x.sin();

    let expected_val = 4.0 + 2.0_f64.sin();
    let expected_der = 4.0 + 2.0_f64.cos();

    assert!((y.value - expected_val).abs() < 1e-10);
    assert!((y.derivative - expected_der).abs() < 1e-10);
}

#[test]
fn test_hyper_dual_hessian_multiplication() {
    let x1 = HyperDualNumber::hessian_var(3.0);
    let x2 = HyperDualNumber::constant(4.0);
    let y = x1 * x2;

    assert_eq!(y.value, 12.0);
    assert_eq!(y.d1, 4.0);
    assert_eq!(y.d2, 4.0);
}

#[test]
fn test_interval_arithmetic() {
    let i1 = Interval::new(2.0, 4.0);
    let i2 = Interval::new(1.0, 3.0);

    let sum = i1 + i2;
    assert_eq!(sum.min, 3.0);
    assert_eq!(sum.max, 7.0);

    let prod = i1 * i2;
    assert_eq!(prod.min, 2.0);
    assert_eq!(prod.max, 12.0);
    assert!(prod.contains(6.0));
}

#[test]
fn test_hessian_uncertainty_propagation() {
    // f(x) = x^2,  f'(x) = 2x, f''(x) = 2
    let mean = 10.0;
    let var = 2.0;
    let jac = array![20.0];
    let hess = Array2::from_elem((1, 1), 2.0);
    let cov = Array2::from_elem((1, 1), var);

    let propagated_mean = HessianPropagation::propagate_mean(mean * mean, &hess, &cov);
    let propagated_var = HessianPropagation::propagate_variance(&jac, &hess, &cov);

    // E[X^2] = E[X]^2 + Var[X] = 100 + 2 = 102
    assert_eq!(propagated_mean, 102.0);
    // 1st order: 20^2 * 2 = 800; 2nd order: 0.5 * (2 * 2)^2 = 8 → 808
    assert_eq!(propagated_var, 808.0);
}
