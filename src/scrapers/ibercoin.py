import re
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


def fetch_html(url: str, retries: int = 3) -> str | None:
    """Descarga el HTML de Ibercoin gestionando reintentos y esperas."""
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=DEFAULT_HEADERS, timeout=25)
            res.raise_for_status()
            return res.text
        except requests.RequestException:
            pause(2.0 * (attempt + 1))
    return None


def extract_coin_urls(catalog_html: str, base_url: str = IBERCOIN_BASE_URL) -> list[str]:
    """Extrae las URLs de las monedas inspeccionando enlaces y contenedores de producto."""
    soup = BeautifulSoup(catalog_html, "html.parser")
    links: list[str] = []
    base_domain = "https://www.ibercoin.com"

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_domain, href).split("?")[0]

        # Evitar el catálogo raíz y enlaces vacíos
        if full_url in [base_domain, f"{base_domain}/", base_url]:
            continue

        # En Ibercoin las monedas cuelgan de tienda-numismatica o lote
        es_candidato = (
            "/tienda-numismatica/" in full_url or "/lote/" in full_url
        ) and not any(
            bad in full_url for bad in ["/categoria", "/section", "1-monedas", "javascript:"]
        )

        if es_candidato and full_url not in links:
            links.append(full_url)

    return links


def save_single_coin(url: str, output_dir: Path) -> Path | None:
    """Descarga y almacena el HTML en crudo de la moneda si no existe localmente."""
    slug = url.rstrip("/").split("/")[-1].replace(".html", "")
    safe_name = re.sub(r"[^\w\-]", "_", slug)
    file_path = output_dir / f"{safe_name}.html"

    if file_path.exists():
        return file_path

    pause()
    coin_html = fetch_html(url)
    if not coin_html:
        return None

    save_raw_html(coin_html, file_path)
    return file_path


def scrape_ibercoin(limit: int = TARGET_ITEMS_PER_SOURCE) -> list[Path]:
    """Descarga páginas en crudo de Ibercoin hasta alcanzar el límite fijado."""
    output_dir = RAW_DATA_DIR / "ibercoin"
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = [p for p in output_dir.glob("*.html")]
    page = 1

    while len(saved_files) < limit:
        catalog_url = f"{IBERCOIN_BASE_URL}?page={page}"
        catalog_html = fetch_html(catalog_url)
        if not catalog_html:
            break

        coin_urls = extract_coin_urls(catalog_html)
        if not coin_urls:
            break

        for url in coin_urls:
            if len(saved_files) >= limit:
                break
            file_path = save_single_coin(url, output_dir)
            if file_path and file_path not in saved_files:
                saved_files.append(file_path)
                print(f"Ibercoin: {len(saved_files)}/{limit} descargadas.")

        page += 1
        pause()

    return saved_files


if __name__ == "__main__":
    print("Iniciando descarga en Ibercoin...")
    archivos = scrape_ibercoin(limit=200)
    print(f"Descargados: {len(archivos)} archivos.")