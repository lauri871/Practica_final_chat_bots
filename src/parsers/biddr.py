import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from src.configuracion.constants import PROCESSED_DATA_DIR, RAW_DATA_DIR


def extract_url(soup: BeautifulSoup, file_path: Path) -> str:
    """Extrae la URL canonica o de respaldo del lote."""
    canon = soup.find("link", rel="canonical")
    if canon and canon.get("href"):
        return canon["href"].strip()
    og = soup.find("meta", property="og:url")
    if og and og.get("content"):
        return og["content"].strip()
    lot_id = file_path.stem.replace("lot_", "")
    return f"https://www.biddr.com/auctions/leu/browse?a=0&l={lot_id}"


def is_valid_biddr_image(url: str) -> bool:
    """Valida fotos numismaticas del CDN de Biddr."""
    es_foto = "media.biddr.com/media/img/auction_lots" in url or "/lots/" in url
    bad = ["logo", "icon", "theme", "payment", "svg", "pixel", "company_logos", "profile"]
    return es_foto and not any(k in url.lower() for k in bad)


def extract_images(soup: BeautifulSoup) -> list[str]:
    """Extrae fotografias del lote asegurando protocolo HTTPS."""
    images: list[str] = []
    base_url = "https://www.biddr.com"
    for img in soup.find_all("img"):
        src = (img.get("data-large") or img.get("data-src") or img.get("src") or "").strip()
        if not src:
            continue
        full = f"https:{src}" if src.startswith("//") else urljoin(base_url, src)
        if is_valid_biddr_image(full) and full not in images:
            images.append(full)
    return images


def clean_text(text: str) -> str:
    """Limpia y normaliza cadenas de texto."""
    return re.sub(r"\s+", " ", text).strip()


def extract_lot_text(soup: BeautifulSoup) -> str:
    """Obtiene el texto tecnico completo de la ficha del lote."""
    for sel in [".lot-description", ".item-description", "#lot-description", "div[class*='description']"]:
        node = soup.select_one(sel)
        if node and len(clean_text(node.get_text())) > 25:
            return clean_text(node.get_text())
    title_tag = soup.find("title")
    if title_tag:
        raw_title = clean_text(title_tag.get_text())
        parts = re.split(r"(?i)\blot\s*\d+\.\s*", raw_title)
        return clean_text(parts[-1] if len(parts) > 1 else raw_title)
    return ""


def parse_chf_price(raw_str: str) -> float | None:
    """Convierte importes en formato suizo (ej. 800 CHF, 2'000 CHF) a float."""
    match = re.search(r"(\d+(?:['\s.,]\d{3})*|\d+)\s*(?:CHF|€|\$)", raw_str, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d+(?:['\s.,]\d{3})*|\d+)", raw_str)
    if not match:
        return None
    val = re.sub(r"[^\d]", "", match.group(1))
    try:
        num = float(val)
        return num if num > 0 else None
    except ValueError:
        return None


def extract_price(soup: BeautifulSoup) -> float | None:
    """Extrae el precio del lote mediante su selector CSS exacto."""
    elem = soup.select_one(".lot-bidding-info-starting-price")
    if elem and (val := parse_chf_price(elem.get_text())):
        return val
    txt = soup.get_text()
    pattern = r"(?:starting\s*price|startpreis|salida)[:\s]*(\d+(?:['\s.,]\d{3})*|\d+)\s*CHF"
    match = re.search(pattern, txt, re.IGNORECASE)
    return parse_chf_price(match.group(1)) if match else None


def extract_metadata(text: str) -> dict[str, Any]:
    """Extrae condicionalmente ano, ceca e inscripciones."""
    meta: dict[str, Any] = {}
    leyendas = re.findall(r"['\"]([A-Z\s\.\+]{2,})['\"]", text)
    if leyendas:
        meta["inscripciones"] = list(dict.fromkeys(l.strip() for l in leyendas if l.strip()))
    
    y = re.search(r"\b(1\d{3}|20\d{2})\b|\b(\d{1,4}(?:-\d{1,4})?)\s*(?:a\.?C\.?|aC|BC|BCE)\b", text, re.IGNORECASE)
    if y:
        meta["ano"] = y.group(0).strip()
    
    c = re.search(r"(?i)(?:ceca|mintmark|mint|taller)[:\s]*([A-Za-zÀ-ÿ]+)", text)
    if c and len(c.group(1).strip()) > 2 and c.group(1).lower() not in ["en", "de", "con", "the", "and"]:
        meta["ceca"] = c.group(1).strip()
    return meta


def parse_descriptions(text: str) -> dict[str, str]:
    """Separa anverso y reverso segun marcas A/, R/, Obv, Rev."""
    res: dict[str, str] = {"descripcion_anverso": text}
    parts = re.split(r"(?i)\s+(?:r/|rev[:\.\s]|reverso[:\s])\s*", text, maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        anv = re.split(r"(?i)\s*(?:a/|obv[:\.\s]|anverso[:\s])\s*", parts[0], maxsplit=1)
        res["descripcion_anverso"] = clean_text(anv[-1] if len(anv) == 2 else parts[0])
        res["descripcion_reverso"] = clean_text(parts[1])
    return res


def parse_coin_details(soup: BeautifulSoup) -> dict[str, Any]:
    """Coordina descripcion y atributos del lote."""
    text = extract_lot_text(soup)
    if not text:
        return {}
    data: dict[str, Any] = parse_descriptions(text)
    data.update(extract_metadata(text))
    price = extract_price(soup)
    if price is not None:
        data["precio"] = price
    return data


def parse_biddr_file(file_path: Path) -> dict[str, Any] | None:
    """Parsea una ficha de Biddr con guardado condicional."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(content, "html.parser")
        images = extract_images(soup)
        if not (1 <= len(images) <= 6):
            return None
        url = extract_url(soup, file_path)
        details = parse_coin_details(soup)
        if not url or "descripcion_anverso" not in details:
            return None
        record = {"url": url, "imagenes": images, "descripcion_anverso": details["descripcion_anverso"]}
        for k in ["descripcion_reverso", "inscripciones", "ceca", "ano", "precio"]:
            if k in details and details[k]:
                record[k] = details[k]
        return record
    except Exception:
        return None


def parse_all_biddr() -> list[dict[str, Any]]:
    """Procesa los archivos de Biddr y genera data/processed/biddr.json."""
    raw_dir = RAW_DATA_DIR / "biddr"
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PROCESSED_DATA_DIR / "biddr.json"

    records = [res for f in raw_dir.glob("*.html") if (res := parse_biddr_file(f))]
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Biddr: {len(records)} registros validos guardados en {out_file}")
    return records


if __name__ == "__main__":
    parse_all_biddr()