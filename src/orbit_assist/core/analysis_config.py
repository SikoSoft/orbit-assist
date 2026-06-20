from functools import lru_cache
from pathlib import Path

from pydantic import TypeAdapter

from orbit_assist.schemas.analysis_config import AnalysisTypeConfig

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "analysisConfig.json"

_analysis_config_adapter = TypeAdapter(dict[str, AnalysisTypeConfig])


@lru_cache
def get_analysis_config() -> dict[str, AnalysisTypeConfig]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            f"Analysis config not found at {CONFIG_PATH}. "
            "Run `uv run fetch-analysis-config` locally, or ensure it is fetched at build time in CI."
        )
    return _analysis_config_adapter.validate_json(CONFIG_PATH.read_text())
