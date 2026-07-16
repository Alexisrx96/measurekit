use super::*;
use ndarray::Array1;

#[test]
fn test_gaussian_tan_enum() {
    let g = UncertaintyValue::Gaussian(GaussianBackend { mean: 0.5, std_dev: 0.1 });
    let result = g.propagate_function("tan").unwrap();
    let expected_mean = 0.5_f64.tan();
    let expected_std = ((1.0 + expected_mean.powi(2)) * 0.1).abs();
    assert!((result.mean() - expected_mean).abs() < 1e-10);
    assert!((result.std_dev() - expected_std).abs() < 1e-10);
}

#[test]
fn test_gaussian_tanh_enum() {
    let g = UncertaintyValue::Gaussian(GaussianBackend { mean: 0.5, std_dev: 0.1 });
    let result = g.propagate_function("tanh").unwrap();
    let expected_mean = 0.5_f64.tanh();
    let expected_std = ((1.0 - expected_mean.powi(2)) * 0.1).abs();
    assert!((result.mean() - expected_mean).abs() < 1e-10);
    assert!((result.std_dev() - expected_std).abs() < 1e-10);
}

#[test]
fn test_montecarlo_tan_enum() {
    let mc = UncertaintyValue::MonteCarlo(MonteCarloBackend {
        samples: Array1::from_vec(vec![0.0, 0.5, -0.5]),
    });
    let result = mc.propagate_function("tan").unwrap();
    match result {
        UncertaintyValue::MonteCarlo(m) => {
            let expected = [0.0_f64.tan(), 0.5_f64.tan(), (-0.5_f64).tan()];
            for (actual, expected) in m.samples.iter().zip(expected.iter()) {
                assert!((actual - expected).abs() < 1e-10);
            }
        }
        _ => panic!("expected MonteCarlo variant"),
    }
}

#[test]
fn test_montecarlo_tanh_enum() {
    let mc = UncertaintyValue::MonteCarlo(MonteCarloBackend {
        samples: Array1::from_vec(vec![0.0, 0.5, -0.5]),
    });
    let result = mc.propagate_function("tanh").unwrap();
    match result {
        UncertaintyValue::MonteCarlo(m) => {
            let expected = [0.0_f64.tanh(), 0.5_f64.tanh(), (-0.5_f64).tanh()];
            for (actual, expected) in m.samples.iter().zip(expected.iter()) {
                assert!((actual - expected).abs() < 1e-10);
            }
        }
        _ => panic!("expected MonteCarlo variant"),
    }
}

#[test]
fn test_unscented_tan_enum() {
    let u = UncertaintyValue::Unscented(UnscentedBackend {
        sigma_points: Array1::from_vec(vec![0.0, 0.5, -0.5]),
        weights: Array1::from_vec(vec![1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0]),
    });
    let result = u.propagate_function("tan").unwrap();
    match result {
        UncertaintyValue::Unscented(uu) => {
            let expected = [0.0_f64.tan(), 0.5_f64.tan(), (-0.5_f64).tan()];
            for (actual, expected) in uu.sigma_points.iter().zip(expected.iter()) {
                assert!((actual - expected).abs() < 1e-10);
            }
        }
        _ => panic!("expected Unscented variant"),
    }
}

#[test]
fn test_unscented_tanh_enum() {
    let u = UncertaintyValue::Unscented(UnscentedBackend {
        sigma_points: Array1::from_vec(vec![0.0, 0.5, -0.5]),
        weights: Array1::from_vec(vec![1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0]),
    });
    let result = u.propagate_function("tanh").unwrap();
    match result {
        UncertaintyValue::Unscented(uu) => {
            let expected = [0.0_f64.tanh(), 0.5_f64.tanh(), (-0.5_f64).tanh()];
            for (actual, expected) in uu.sigma_points.iter().zip(expected.iter()) {
                assert!((actual - expected).abs() < 1e-10);
            }
        }
        _ => panic!("expected Unscented variant"),
    }
}
