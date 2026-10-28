import json
from pathlib import Path


def save_raw_html(content: str, output_path: Path) -> None:
    """Guarda contenido HTML en crudo creando los directorios necesarios."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def read_raw_html(file_path: Path) -> str:
    """Lee y devuelve el contenido de un archivo HTML local."""
    return file_path.read_text(encoding="utf-8")


def save_json_dataset(data: list[dict], output_path: Path) -> None:
    """Exporta el dataset final a JSON con indentación y formato UTF-8."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)