import re
import time
from typing import Any
from src.configuracion.constants import REQUEST_DELAY


def pause(seconds: float = REQUEST_DELAY) -> None:
    """Aplica una espera para respetar la tasa de peticiones."""
    time.sleep(seconds)


def clean_text(text: str | None) -> str:
    """Limpia espacios redundantes y saltos de línea."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def build_valid_record(data: dict[str, Any]) -> dict[str, Any]:
    """Filtra y descarta claves con valores nulos, vacíos o listas sin elementos."""
    return {
        key: value
        for key, value in data.items()
        if value is not None and value != "" and value != []
    }