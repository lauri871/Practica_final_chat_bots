from pathlib import Path
from src.configuracion.constants import TARGET_ITEMS_PER_SOURCE
from src.scrapers.ibercoin import scrape_ibercoin
from src.scrapers.biddr import scrape_biddr


def run_all_scrapers(limit: int = TARGET_ITEMS_PER_SOURCE) -> dict[str, list[Path]]:
    """Coordina y ejecuta la descarga de HTMLs en crudo de todas las fuentes."""
    print("Iniciando adquisición de Ibercoin...")
    ibercoin_files = scrape_ibercoin(limit=limit)

    print("Iniciando adquisición de Biddr...")
    biddr_files = scrape_biddr(limit=limit)

    return {
        "ibercoin": ibercoin_files,
        "biddr": biddr_files,
    }