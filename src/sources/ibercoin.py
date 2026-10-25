import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def extract_coin_data(html: str, url: str) -> dict:
    """Extrae los datos disponibles de una ficha de Ibercoin."""
    soup = BeautifulSoup(html, "lxml")

    data = {
        "url": url,
        "fuente": "ibercoin",
    }

    # Obtener la descripción completa de la moneda.
    description_tag = soup.find(
        "meta", attrs={"itemprop": "description"}
    )

    description = ""
    if description_tag and description_tag.get("content"):
        description = description_tag["content"].strip()

    # Usar la descripción completa como título.
    if description:
        data["titulo"] = description
        data["descripcion_original"] = description

    # Extraer anverso y reverso dividiendo el texto.
    if "Anv:" in description and "Rev:" in description:
        partes = description.split("Anv:", 1)
        texto_anverso_y_reverso = partes[1]

        partes_reverso = texto_anverso_y_reverso.split("Rev:", 1)

        anverso = partes_reverso[0].strip()
        reverso = partes_reverso[1].strip()

        if anverso:
            data["descripcion_anverso"] = anverso

        # Retirar la conservación y los comentarios posteriores.
        reverso = re.split(
            r"\s+(?:EBC|MBC|BC)\b",
            reverso,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if reverso:
            data["descripcion_reverso"] = reverso

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

    # Extraer la imagen principal de la moneda.
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

    # Extraer peso y diámetro cuando estén disponibles.
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
    """Lee el HTML guardado y escribe los datos extraídos en JSON."""
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

    # Validar los campos esenciales.
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


if __name__ == "__main__":
    # Permite ejecutar este archivo directamente para probarlo.
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw" / "ibercoin"
    acquire_ibercoin(raw_dir)