"""Re-export the entry class so `from app.checks.ai.output_format_manipulation import OutputFormatManipulationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.output_format_manipulation.check import OutputFormatManipulationCheck

__all__ = ["OutputFormatManipulationCheck"]
