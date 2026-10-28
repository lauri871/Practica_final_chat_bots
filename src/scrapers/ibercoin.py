from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from src.configuracion.constants import (
    DEFAULT_HEADERS,
    IBERCOIN_BASE_URL,
    RAW_DATA_DIR,
    TARGET_ITEMS_PER_SOURCE,
)
from src.utils.helpers import pause
from src.utils.storage import save_raw_html


def fetch_html(url: str) -> str:
    """Descarga el contenido HTML de una URL con cabeceras estándar."""
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def extract_coin_urls(catalog_html: str, base_url: str = IBERCOIN_BASE_URL) -> list[str]:
    """Extrae enlaces únicos a fichas de monedas descartando filtros y páginas."""
    soup = BeautifulSoup(catalog_html, "html.parser")
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_url, href)
        es_moneda = "/es/tienda-numismatica/" in full_url and full_url != base_url
        es_filtro = any(p in full_url for p in ["?page=", "&page=", "/1-monedas?"])

        if es_moneda and not es_filtro and full_url not in links:
            links.append(full_url)

    return links


def save_single_coin(url: str, output_dir: Path) -> Path:
    """Descarga el HTML de una moneda y lo guarda en disco."""
    pause()
    coin_html = fetch_html(url)
    item_id = url.rstrip("/").split("/")[-1].replace(".html", "")
    file_path = output_dir / f"{item_id}.html"
    save_raw_html(coin_html, file_path)
    return file_path


def scrape_ibercoin(limit: int = TARGET_ITEMS_PER_SOURCE) -> list[Path]:
    """Recorre el catálogo y almacena hasta 'limit' páginas de producto."""
    output_dir = RAW_DATA_DIR / "ibercoin"
    saved_files: list[Path] = []
    page = 1

    while len(saved_files) < limit:
        catalog_url = f"{IBERCOIN_BASE_URL}?page={page}"
        catalog_html = fetch_html(catalog_url)
        coin_urls = extract_coin_urls(catalog_html, catalog_url)

        if not coin_urls:
            break

        for url in coin_urls:
            if len(saved_files) >= limit:
                break
            file_path = save_single_coin(url, output_dir)
            saved_files.append(file_path)

        page += 1
        pause()

    return saved_files


if __name__ == "__main__":
    print("Iniciando descarga en Ibercoin...")
    archivos = scrape_ibercoin(limit=200)
    print(f"Descargados: {len(archivos)} archivos.")