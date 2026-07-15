use sprs::CsMat;

pub trait SandwichProduct {
    fn sandwich_product(&self, center: &CsMat<f64>) -> CsMat<f64>;
}

impl SandwichProduct for CsMat<f64> {
    fn sandwich_product(&self, center: &CsMat<f64>) -> CsMat<f64> {
        let temp = self * center;
        &temp * &self.transpose_view()
    }
}

pub fn sparse_sandwich(j: &CsMat<f64>, sigma: &CsMat<f64>) -> CsMat<f64> {
    j.sandwich_product(sigma)
}
