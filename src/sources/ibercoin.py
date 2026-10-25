import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def extract_coin_data(html: str, url: str) -> dict:
    """Extrae los datos disponibles de una moneda de Ibercoin."""
    soup = BeautifulSoup(html, "lxml")

    data = {
        "url": url,
        "fuente": "ibercoin",
    }

    # Nombre de la moneda.
    name_tag = soup.find("meta", attrs={"itemprop": "name"})
    if name_tag and name_tag.get("content"):
        data["titulo"] = name_tag["content"].strip()

    # Descripción completa de la moneda.
    description_tag = soup.find(
        "meta", attrs={"itemprop": "description"}
    )
    description = ""

    if description_tag and description_tag.get("content"):
        description = description_tag["content"].strip()

    # Extraer las descripciones del anverso y del reverso.
    obverse_match = re.search(
        r"Anv:(.*?)Rev:",
        description,
        re.IGNORECASE | re.DOTALL,
)

    reverse_match = re.search(
        r"Rev:\s(.?)(?=\s(?:EBC|MBC|BC|Precio)\b|$)",
        description,
        re.IGNORECASE,
    )

    if obverse_match:
        data["descripcion_anverso"] = obverse_match.group(1).strip()

    if reverse_match:
        data["descripcion_reverso"] = reverse_match.group(1).strip()

    # Guardar también la descripción original completa.
    if description:
        data["descripcion_original"] = description

    # Precio y moneda.
    price_tag = soup.find("meta", attrs={"itemprop": "price"})
    currency_tag = soup.find(
        "meta", attrs={"itemprop": "priceCurrency"}
    )

    if price_tag and price_tag.get("content"):
        try:
            data["precio"] = float(price_tag["content"])
            data["moneda_precio"] = (
                currency_tag.get("content", "EUR")
                if currency_tag
                else "EUR"
            )
        except ValueError:
            pass


    image_tag = soup.find("meta", attrs={"itemprop": "image"})

    if image_tag and image_tag.get("content"):
        data["imagenes"] = [
            urljoin(url, image_tag["content"])
        ]
    else:
        image_tag = soup.find("link", attrs={"itemprop": "image"})

        if image_tag and image_tag.get("href"):
            data["imagenes"] = [
                urljoin(url, image_tag["href"])
            ]

    # Peso y diámetro, cuando están disponibles.
    measurements = re.search(
        r"((?:Ar.\s)?([\d,]+)\sg\s/\s([\d,]+)\s*mm)",
        description,
        re.IGNORECASE,
    )

    if measurements:
        data["peso_g"] = float(
            measurements.group(1).replace(",", ".")
        )
        data["diametro_mm"] = float(
            measurements.group(2).replace(",", ".")
        )

    return data


def acquire_ibercoin(output_dir: Path) -> None:
    """Lee el HTML de prueba y guarda los datos extraídos en JSON."""
    project_root = Path(__file__).resolve().parents[2]

    html_file = (
        project_root
        / "data"
        / "raw"
        / "ibercoin"
        / "moneda_prueba.html"
    )

    if not html_file.exists():
        raise FileNotFoundError(
            f"No se encuentra el HTML: {html_file}"
        )

    html = html_file.read_text(encoding="utf-8")

    url = (
        "https://www.ibercoin.com/es/tienda-numismatica/"
        "monedas/2-grecia-antigua/prod-7329-ATTICA-Atenas"
    )

    coin = extract_coin_data(html, url)
    if not coin.get("url") or not coin.get("imagenes"):
        raise ValueError(
            "La ficha no contiene URL o imagen de la moneda."
        )

    if not coin.get("descripcion_anverso"):
        raise ValueError(
            "No se ha podido extraer la descripción del anverso."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "moneda_prueba.json"
    output_file.write_text(
        json.dumps(coin, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Datos extraídos y guardados en: {output_file}")
    print(json.dumps(coin, ensure_ascii=False, indent=2))