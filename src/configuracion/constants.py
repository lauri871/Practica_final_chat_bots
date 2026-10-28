from pathlib import Path

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Configuración de adquisición
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY = 1.5  # Pausa mínima en segundos para evitar bloqueos
TARGET_ITEMS_PER_SOURCE = 100

# URLs base de las fuentes
IBERCOIN_BASE_URL = "https://www.ibercoin.com/es/tienda-numismatica/1-monedas"
BIDDR_BASE_URL = "https://www.biddr.com/leu/auction?a=7528"