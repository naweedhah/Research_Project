# Inference adapters (loaded by app.main)

from app.main import DemoModelAdapter, OnnxModelAdapter, PyTorchMultimodalAdapter, SklearnModelAdapter

__all__ = [
    "DemoModelAdapter",
    "SklearnModelAdapter",
    "PyTorchMultimodalAdapter",
    "OnnxModelAdapter",
]
