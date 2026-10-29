import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from src.configuracion.constants import PROCESSED_DATA_DIR, RAW_DATA_DIR


def extract_url(soup: BeautifulSoup, file_path: Path) -> str:
    """Extrae la URL canónica o de respaldo del producto."""
    canon = soup.find("link", rel="canonical")
    if canon and canon.get("href"):
        return canon["href"].strip()
    og = soup.find("meta", property="og:url")
    if og and og.get("content"):
        return og["content"].strip()
    return f"https://www.ibercoin.com/es/tienda-numismatica/{file_path.stem}.html"


def is_valid_coin_image(url: str) -> bool:
    """Filtra imágenes para aceptar solo fotos originales de la moneda."""
    es_foto = "cdn.ibercoin.com/store" in url or "/img/p/" in url
    bad = ["logo", "icon", "theme", "payment", "svg", "pixel", "phone", 
           "email", "whatsapp", "pmg", "ngc", "vcoins", "six-bid", "numisbids", 
           "biddr", "location", "es.png", "en.png", "medium"]
    return es_foto and not any(k in url.lower() for k in bad)


def extract_images(soup: BeautifulSoup) -> list[str]:
    """Extrae fotos de la pieza descartando elementos de interfaz."""
    images: list[str] = []
    base_url = "https://www.ibercoin.com"
    for img in soup.find_all("img"):
        src = (img.get("data-image-large-src") or img.get("data-src") or img.get("src") or "").strip()
        if not src:
            continue
        full = urljoin(base_url, src)
        if is_valid_coin_image(full) and full not in images:
            images.append(full)
    return images


def clean_text(text: str) -> str:
    """Limpia y normaliza cadenas de texto."""
    return re.sub(r"\s+", " ", text).strip()


def extract_full_body_text(soup: BeautifulSoup, url: str) -> str:
    """Extrae el texto descriptivo real usando el selector exacto de la ficha."""
    p_desc = soup.select_one("p.card-text, .card-text")
    if p_desc and len(clean_text(p_desc.get_text())) > 20:
        return clean_text(p_desc.get_text())
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content") and len(clean_text(meta["content"])) > 20:
        return clean_text(meta["content"])
    slug = url.rstrip("/").split("/")[-1].replace(".html", "").replace("prod-", "")
    return clean_text(re.sub(r"^\d+-", "", slug).replace("-", " "))


def parse_numeric_price(raw_str: str) -> float | None:
    """Convierte una cadena monetaria a valor float."""
    match = re.search(r"(\d+[\d\.,]*)", raw_str)
    if match:
        clean = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(clean)
        except ValueError:
            pass
    return None


def extract_price(soup: BeautifulSoup) -> float | None:
    """Extrae el precio buscando selectores de moneda o texto en euros."""
    selectors = [".price", ".current-price", "[itemprop='price']", ".precio", ".salida", "#our_price_display"]
    for sel in selectors:
        elem = soup.select_one(sel)
        if elem and (val := parse_numeric_price(elem.get_text())):
            return val
    txt = soup.get_text()
    pattern = r"(?:precio(?:\s*de)?\s*salida|salida|pvp|precio|estimaci[oó]n)[:\s]*(\d+[\d\.,]*)\s*€?"
    match = re.search(pattern, txt, re.IGNORECASE)
    return parse_numeric_price(match.group(1)) if match else None


def extract_metadata(text: str) -> dict[str, Any]:
    """Extrae condicionalmente año, ceca e inscripciones."""
    meta: dict[str, Any] = {}
    leyendas = re.findall(r"['\"]([A-Z\s\.\+]{2,})['\"]", text)
    if leyendas:
        meta["inscripciones"] = list(dict.fromkeys(l.strip() for l in leyendas if l.strip()))
    y = re.search(r"\b(1\d{3}|20\d{2})\b|\b(\d{1,4}(?:-\d{1,4})?)\s*(?:a\.?C\.?|aC)\b", text)
    if y:
        meta["ano"] = y.group(0).strip()
    c = re.search(r"(?i)(?:ceca|acuñada\s*en|taller|mintmark)[:\s]*([A-Za-zÀ-ÿ]+)", text)
    if c and len(c.group(1).strip()) > 2 and c.group(1).lower() not in ["en", "de", "con"]:
        meta["ceca"] = c.group(1).strip()
    return meta


def parse_descriptions(text: str) -> dict[str, str]:
    """Separa anverso y reverso buscando los patrones A/ y R/ habituales."""
    res: dict[str, str] = {"descripcion_anverso": text}
    parts = re.split(r"(?i)\s+(?:r/|reverso[:\s])\s*", text, maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        anv = re.split(r"(?i)\s*(?:a/|anverso[:\s])\s*", parts[0], maxsplit=1)
        res["descripcion_anverso"] = clean_text(anv[-1] if len(anv) == 2 else parts[0])
        res["descripcion_reverso"] = clean_text(parts[1])
    return res


def parse_coin_details(soup: BeautifulSoup, url: str) -> dict[str, Any]:
    """Coordina la extracción de descripciones y metadatos opcionales."""
    text = extract_full_body_text(soup, url)
    if not text:
        return {}
    data: dict[str, Any] = parse_descriptions(text)
    data.update(extract_metadata(text))
    price = extract_price(soup)
    if price is not None:
        data["precio"] = price
    return data


def parse_ibercoin_file(file_path: Path) -> dict[str, Any] | None:
    """Parsea una ficha descartando categorías y guardando campos válidos."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(content, "html.parser")
        url = extract_url(soup, file_path)
        if any(bad in url for bad in ["/41-moneda-extranjera", "/44-billetes", "/48-bibliografia", "/49-lotes-y-colecciones", "/1-monedas"]):
            return None
        images = extract_images(soup)
        if not (1 <= len(images) <= 6):
            return None
        details = parse_coin_details(soup, url)
        if not url or "descripcion_anverso" not in details:
            return None
        record = {"url": url, "imagenes": images, "descripcion_anverso": details["descripcion_anverso"]}
        for k in ["descripcion_reverso", "inscripciones", "ceca", "ano", "precio"]:
            if k in details and details[k]:
                record[k] = details[k]
        return record
    except Exception:
        return None


def parse_all_ibercoin() -> list[dict[str, Any]]:
    """Genera el JSON final limpio con la estructura correcta."""
    raw_dir = RAW_DATA_DIR / "ibercoin"
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PROCESSED_DATA_DIR / "ibercoin.json"
    records = [res for f in raw_dir.glob("*.html") if (res := parse_ibercoin_file(f))]
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Ibercoin: {len(records)} registros validos guardados en {out_file}")
    return records


if __name__ == "__main__":
    parse_all_ibercoin()