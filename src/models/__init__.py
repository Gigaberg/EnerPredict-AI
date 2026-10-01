"""
Models Package
==============
Model registry and training workflows.
"""

from .registry import MODEL_REGISTRY
from .trainer import get_model_instances, train_regressor

__all__ = ["MODEL_REGISTRY", "get_model_instances", "train_regressor"]
