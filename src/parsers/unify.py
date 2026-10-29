import json
from pathlib import Path
from typing import Any

from src.configuracion.constants import PROCESSED_DATA_DIR


def load_json_records(file_path: Path) -> list[dict[str, Any]]:
    """Carga una lista de registros desde un archivo JSON si existe."""
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def enrich_record_with_source(record: dict[str, Any], source_name: str) -> dict[str, Any]:
    """Añade la fuente de procedencia a un registro."""
    return {"fuente": source_name, **record}


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Elimina monedas duplicadas basándose en su URL canónica."""
    seen_urls: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in records:
        url = item.get("url", "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)
    return unique


def validate_required_fields(record: dict[str, Any]) -> bool:
    """Valida la presencia de campos estrictamente obligatorios."""
    return bool(record.get("url") and record.get("imagenes") and record.get("descripcion_anverso"))


def build_unified_dataset() -> list[dict[str, Any]]:
    """Carga, unifica y valida los datos de Ibercoin y Biddr."""
    ibercoin_path = PROCESSED_DATA_DIR / "ibercoin.json"
    biddr_path = PROCESSED_DATA_DIR / "biddr.json"

    ib_items = [enrich_record_with_source(r, "ibercoin") for r in load_json_records(ibercoin_path)]
    bi_items = [enrich_record_with_source(r, "biddr") for r in load_json_records(biddr_path)]

    raw_combined = ib_items + bi_items
    valid_items = [r for r in raw_combined if validate_required_fields(r)]
    return deduplicate_records(valid_items)


def save_unified_dataset(out_filename: str = "coins_dataset.json") -> Path:
    """Guarda el dataset consolidado en la carpeta de procesados."""
    dataset = build_unified_dataset()
    out_path = PROCESSED_DATA_DIR / out_filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Dataset unificado: {len(dataset)} registros guardados en {out_path}")
    return out_path


if __name__ == "__main__":
    save_unified_dataset()