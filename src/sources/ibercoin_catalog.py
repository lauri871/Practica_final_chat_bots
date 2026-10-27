
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


CATALOG_URL = (
    "https://www.ibercoin.com/es/tienda-numismatica/1-monedas"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NumismaticCourseProject/1.0)"
}


def get_session() -> requests.Session:
    """Crea una sesión HTTP reutilizable."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get_product_links(
    session: requests.Session,
    catalog_url: str,
) -> list[str]:
    """Obtiene los enlaces de producto de una página del catálogo."""
    response = session.get(catalog_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    links = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]

        if "/prod-" not in href:
            continue

        absolute_url = urljoin(catalog_url, href)
        parsed = urlparse(absolute_url)

        if parsed.netloc != "www.ibercoin.com":
            continue

        links.append(absolute_url)

    return list(dict.fromkeys(links))


def get_catalog_pages(
    session: requests.Session,
    first_url: str,
) -> list[str]:
    """Descubre las páginas de catálogo enlazadas."""
    response = session.get(first_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    pages = {first_url}

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]

        if "page=" not in href:
            continue

        page_url = urljoin(first_url, href)

        if urlparse(page_url).netloc == "www.ibercoin.com":
            pages.add(page_url)

    def page_number(url: str) -> int:
        from urllib.parse import parse_qs

        return int(parse_qs(urlparse(url).query).get("page", ["1"])[0])

    return sorted(pages, key=page_number)


def acquire_catalog(output_dir: Path) -> None:
    """Guarda los HTML originales de las fichas encontradas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    session = get_session()

    catalog_pages = get_catalog_pages(session, CATALOG_URL)
    print(f"Páginas de catálogo encontradas: {len(catalog_pages)}")

    product_urls = []

    for page_url in catalog_pages:
        print(f"Consultando catálogo: {page_url}")
        product_urls.extend(get_product_links(session, page_url))
        time.sleep(1)

    product_urls = list(dict.fromkeys(product_urls))
    print(f"Fichas únicas encontradas: {len(product_urls)}")

    for index, product_url in enumerate(product_urls, start=1):
        filename = f"moneda_{index:04d}.html"
        output_file = output_dir / filename

        if output_file.exists():
            print(f"[{index}/{len(product_urls)}] Ya existe: {filename}")
            continue

        try:
            response = session.get(product_url, timeout=30)
            response.raise_for_status()
            output_file.write_text(response.text, encoding="utf-8")
            print(f"[{index}/{len(product_urls)}] Guardada: {filename}")
        except requests.RequestException as error:
            print(f"No se pudo descargar {product_url}: {error}")

        time.sleep(1)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw" / "ibercoin"
    acquire_catalog(raw_dir)
