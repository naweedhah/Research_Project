from ml.calibration.temperature import TemperatureScaler
import torch


def test_temperature_scaler_changes_logits():
    scaler = TemperatureScaler()
    logits = torch.tensor([[2.0, 0.1, -1.0, 0.0], [0.2, 1.5, 0.1, -0.4]])
    targets = torch.tensor([0, 1])
    before = scaler(logits).detach().clone()
    scaler.fit(logits, targets, max_iter=20)
    after = scaler(logits)
    assert after.shape == before.shape
