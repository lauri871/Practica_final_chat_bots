import sys
import json
from pathlib import Path
from typing import Any

from src.configuracion.constants import PROCESSED_DATA_DIR


def convert_currency(record: dict[str, Any]) -> dict[str, Any]:
    """Convierte los precios a Euros (€) aplicando conversión si la moneda original era CHF (Biddr)."""
    if "precio" in record:
        url = record.get("url", "")
        # Si la fuente es Biddr o su URL contiene biddr.com, convertimos de CHF a Euros (ej. tipo de cambio 1.07)
        if record.get("fuente") == "biddr" or "biddr.com" in url:
            record["precio"] = round(record["precio"] * 1.07, 2)
        record["moneda"] = "EUR"
    return record


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """Elimina campos nulos, vacíos o incorrectos y normaliza los textos."""
    cleaned = {}
    for key, value in record.items():
        if value is not None and value != "" and value != []:
            if isinstance(value, str):
                cleaned[key] = " ".join(value.split())
            elif isinstance(value, list):
                cleaned[key] = [v.strip() for v in value if v]
            else:
                cleaned[key] = value
    return cleaned


def validate_minimum_requirements(record: dict[str, Any]) -> bool:
    """Valida los campos obligatorios mínimos exigidos en la normativa del proyecto."""
    return bool(
        record.get("url") and 
        record.get("imagenes") and 
        record.get("descripcion_anverso")
    )


def preprocess_main(raw_dir_str: str) -> None:
    """Función principal del pipeline de preprocesamiento y transformación."""
    raw_dir = Path(raw_dir_str)
    print(f"Iniciando preprocesamiento utilizando la ruta en crudo: {raw_dir}")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Cargamos únicamente los archivos de origen específicos, evitando procesados anteriores
    raw_records = []
    source_files = ["biddr.json", "ibercoin.json"]
    
    for file_name in source_files:
        json_file = PROCESSED_DATA_DIR / file_name
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    raw_records.extend(data)

    # Si no encuentra los archivos específicos por nombre, busca cualquier json que no sea el final
    if not raw_records:
        for json_file in PROCESSED_DATA_DIR.glob("*.json"):
            if json_file.name not in ["coins_dataset_final.json", "coins_dataset_preprocessed.json"]:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        raw_records.extend(data)

    # Aplicamos transformaciones, conversión de moneda y limpieza de nulos
    final_records = []
    for item in raw_records:
        converted = convert_currency(item)
        cleaned = clean_record(converted)
        
        if validate_minimum_requirements(cleaned):
            final_records.append(cleaned)

    # Guardamos el dataset final preprocesado
    output_path = PROCESSED_DATA_DIR / "coins_dataset_final.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)

    print(f"¡Preprocesamiento completado con éxito! Se han procesado y guardado {len(final_records)} registros en: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso correcto: python -m src.preprocess <ruta_carpeta_archivos_en_crudo>")
        sys.exit(1)
    
    preprocess_main(sys.argv[1])