"""Re-export the entry class so `from app.checks.ai.ai_training_data_extraction import TrainingDataExtractionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_training_data_extraction.check import TrainingDataExtractionCheck

__all__ = ["TrainingDataExtractionCheck"]
