import httpx

from orbit_assist.core.analysis_config import CONFIG_PATH
from orbit_assist.core.config import get_settings


def fetch_analysis_config() -> None:
    settings = get_settings()
    response = httpx.get(settings.analysis_config_url, timeout=10.0)
    response.raise_for_status()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(response.text)


def main() -> None:
    fetch_analysis_config()
