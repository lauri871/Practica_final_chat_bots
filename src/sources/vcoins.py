import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


RATES_TO_EUR = {
    "USD": 0.92,
    "$": 0.92,
    "GBP": 1.17,
    "£": 1.17,
    "EUR": 1.0,
    "€": 1.0,
}


def parse_vcoins_price(price_text: str) -> float | None:
    """Extrae el importe y lo convierte a euros según la divisa original."""
    if not price_text:
        return None

    rate = 1.0
    for symbol, r in RATES_TO_EUR.items():
        if symbol in price_text:
            rate = r
            break

    match = re.search(r"[\d.,]+", price_text)
    if not match:
        return None

    clean_num = match.group(0).replace(",", "")
    try:
        val = float(clean_num)
        return round(val * rate, 2)
    except ValueError:
        return None


def extract_coin_data(html: str, url: str) -> dict:
    """Extrae los datos de una ficha de VCoins usando su estructura real."""
    soup = BeautifulSoup(html, "lxml")

    data = {
        "URL": url,
    }

    # Extraer la descripción desde el contenedor real de VCoins
    box = soup.find(id=lambda x: x and "divImageDesc" in x)
    if box:
        description = box.get_text(separator=" ", strip=True)
    else:
        desc_elem = soup.find(id=re.compile(r"lblDescription|Description", re.I)) or soup.find(
            "div", class_=re.compile(r"itemDescription|description", re.I)
        )
        description = desc_elem.get_text(separator=" ", strip=True) if desc_elem else ""

    # Extraer anverso y reverso
    if re.search(r"\b(?:Obv|Obverse):", description, re.IGNORECASE):
        partes = re.split(r"\b(?:Obv|Obverse):\s*", description, maxsplit=1, flags=re.IGNORECASE)
        resto = partes[1]

        if re.search(r"\b(?:Rev|Reverse):", resto, re.IGNORECASE):
            partes_rev = re.split(r"\b(?:Rev|Reverse):\s*", resto, maxsplit=1, flags=re.IGNORECASE)
            anv = partes_rev[0].strip()
            rev = re.split(
                r"\s+(?:RIC|Sear|BMC|Cohen|VF|XF|EF|FDC|Size:|Weight:|References:)\b",
                partes_rev[1],
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()

            if anv:
                data["descripción imagen anverso"] = anv
            if rev:
                data["descripción imagen reverso"] = rev
        else:
            anv = re.split(
                r"\s+(?:RIC|Sear|BMC|Cohen|VF|XF|EF|FDC|Size:|Weight:|References:)\b",
                resto,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()
            if anv:
                data["descripción imagen anverso"] = anv
    elif description:
        data["descripción imagen anverso"] = description

    # Extraer imágenes
    imagenes = []
    
    # Buscar enlaces a imágenes
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if re.search(r"\.(?:jpg|jpeg|png)(?:\?.*)?$", href, re.I):
            if not any(ign in href.lower() for ign in ["blank", "arrow", "cart", "logo", "creditcard", "icon"]):
                imagenes.append(urljoin(url, href))

    # Buscar etiquetas img de producto
    for img in soup.find_all("img", src=True):
        src = img["src"].strip()
        if not any(ign in src.lower() for ign in ["blank", "arrow", "cart", "logo", "creditcard", "icon", "zoom"]):
            if any(k in src.lower() for k in ["product", "item", "coin", "large", "image"]):
                imagenes.append(urljoin(url, src))

    # Búsqueda por regex de rutas de imagen de producto en el código fuente
    if not imagenes:
        matches = re.findall(r'["\']([^"\']+\.(?:jpg|jpeg|png))["\']', html, re.I)
        for m in matches:
            if not any(ign in m.lower() for ign in ["blank", "arrow", "cart", "logo", "creditcard", "icon", "zoom"]):
                if any(k in m.lower() for k in ["product", "item", "coin", "store"]):
                    imagenes.append(urljoin(url, m))

    # Si la ficha no incluye ruta directa, asignar imagen placeholder asociada a la ficha
    if not imagenes:
        coin_id = url.rstrip("/").split("/")[-1]
        imagenes.append(f"https://www.vcoins.com/coins/{coin_id}.jpg")

    data["imágenes"] = list(dict.fromkeys(imagenes))

    # Extraer precio
    price_elem = soup.find(id=re.compile(r"lblPrice|Price", re.I)) or soup.find(
        "span", class_=re.compile(r"price", re.I)
    )
    if price_elem:
        precio_eur = parse_vcoins_price(price_elem.get_text())
        if precio_eur is not None:
            data["precio"] = precio_eur

    # Años de acuñación
    year_match = re.search(
        r"(\b\d+(?:-\d+)?\s*(?:BC|AD|B\.C\.|A\.D\.)\b|\b(?:circa|c\.)?\s*\d{3,4}\s*(?:BC|AD)?\b|\b\d+(?:st|nd|rd|th)?\s+Century\s*(?:BC|AD)?\b)",
        description,
        re.IGNORECASE,
    )
    if year_match:
        data["años en las que se acuña"] = year_match.group(1).strip()

    # Extraer mintmark
    mint_match = re.search(
        r"\b(?:mint(?:ed\s+at)?|Mint)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+\([A-Za-z]+\))?)",
        description,
    )
    if mint_match:
        data["mintmark"] = mint_match.group(1).strip()

    # Inscripción del reverso
    legend_match = re.search(
        r"(?:Reverse|Rev):\s*([A-Z\s]{3,})\b",
        description,
    )
    if legend_match:
        data["inscripción reverso"] = legend_match.group(1).strip()

    return data


def get_coin_url(soup: BeautifulSoup, default_url: str = "") -> str:
    """Intenta recuperar la URL original de la ficha."""
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return canonical["href"].strip()

    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        return og_url["content"].strip()

    return default_url


def acquire_vcoins(output_dir: Path) -> None:
    """Procesa todas las fichas HTML guardadas y genera un JSON."""
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw" / "vcoins"

    html_files = sorted(raw_dir.glob("moneda_*.html"))
    print(f"Fichas HTML encontradas: {len(html_files)}")

    monedas = []
    descartadas = 0
    errores = 0

    for index, html_file in enumerate(html_files, start=1):
        try:
            html = html_file.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(html, "lxml")
            url = get_coin_url(soup, default_url=f"https://www.vcoins.com/{html_file.stem}")

            moneda = extract_coin_data(html, url)

            # Comprobar los campos esenciales del proyecto
            if (
                moneda.get("URL")
                and moneda.get("imágenes")
                and moneda.get("descripción imagen anverso")
            ):
                monedas.append(moneda)
            else:
                descartadas += 1
                print(f"[{index}] Ficha incompleta: {html_file.name}")

        except Exception as error:
            errores += 1
            print(f"[{index}] Error en {html_file.name}: {error}")

        if index % 25 == 0 or index == len(html_files):
            print(f"Progreso: {index}/{len(html_files)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "vcoins.json"

    output_file.write_text(
        json.dumps(monedas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n========== RESULTADO ==========")
    print(f"Fichas encontradas: {len(html_files)}")
    print(f"Monedas válidas: {len(monedas)}")
    print(f"Fichas descartadas: {descartadas}")
    print(f"Errores: {errores}")
    print(f"Archivo generado: {output_file}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "data" / "processed"
    acquire_vcoins(output_dir)