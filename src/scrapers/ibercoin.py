from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from src.configuracion.constants import (
    DEFAULT_HEADERS,
    BIDDR_BASE_URL,
    RAW_DATA_DIR,
    TARGET_ITEMS_PER_SOURCE,
)
from src.utils.helpers import pause
from src.utils.storage import save_raw_html


def fetch_html(url: str, retries: int = 3) -> str | None:
    """Descarga el HTML de Biddr gestionando reintentos y esperas."""
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=DEFAULT_HEADERS, timeout=25)
            res.raise_for_status()
            return res.text
        except requests.RequestException:
            pause(2.0 * (attempt + 1))
    return None


def extract_coin_urls(catalog_html: str, base_url: str = BIDDR_BASE_URL) -> list[str]:
    """Extrae las URLs de cada lote/moneda descartando enlaces duplicados."""
    soup = BeautifulSoup(catalog_html, "html.parser")
    links: list[str] = []
    base_domain = "https://www.biddr.com"

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_domain, href)
        es_lote = "a=7528" in full_url and ("&l=" in full_url or "/lot/" in full_url)
        if es_lote and full_url not in links:
            links.append(full_url)
    return links


def save_single_coin(url: str, output_dir: Path) -> Path | None:
    """Descarga y almacena el HTML en crudo del lote si no existe localmente."""
    lot_id = url.split("l=")[-1].split("&")[0] if "l=" in url else url.rstrip("/").split("/")[-1]
    file_path = output_dir / f"lot_{lot_id}.html"

    if file_path.exists():
        return file_path

    pause()
    coin_html = fetch_html(url)
    if not coin_html:
        return None

    save_raw_html(coin_html, file_path)
    return file_path


def scrape_biddr(limit: int = 200) -> list[Path]:
    """Descarga páginas en crudo de Biddr indicando si se agotan los registros."""
    output_dir = RAW_DATA_DIR / "biddr"
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = list(output_dir.glob("*.html"))
    page = 1

    while len(saved_files) < limit:
        catalog_url = f"{BIDDR_BASE_URL}&p={page}"
        catalog_html = fetch_html(catalog_url)

        if not catalog_html:
            print(f"[Biddr] No se pudo acceder a la página {page}. Fin del catálogo.")
            break

        coin_urls = extract_coin_urls(catalog_html)
        if not coin_urls:
            print(f"[Biddr] Página {page} sin más lotes. Catálogo completado.")
            break

        for url in coin_urls:
            if len(saved_files) >= limit:
                break
            lot_id = url.split("l=")[-1].split("&")[0] if "l=" in url else url.rstrip("/").split("/")[-1]
            file_path = output_dir / f"lot_{lot_id}.html"

            if not file_path.exists():
                file_path = save_single_coin(url, output_dir)
                if file_path:
                    saved_files.append(file_path)
                    print(f"Biddr: {len(saved_files)}/{limit} descargadas.")

        page += 1
        pause()

    print(f"[Biddr] Proceso finalizado. Total de archivos disponibles: {len(saved_files)}.")
    return saved_files


if __name__ == "__main__":
    scrape_biddr(limit=200)