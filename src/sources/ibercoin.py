
import json
import re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def extract_coin_data(html: str, url: str) -> dict:
    """Extrae los datos disponibles de una ficha de Ibercoin."""
    soup = BeautifulSoup(html, "lxml")

    # Extraer la descripción original.
    description_tag = soup.find(
        "meta",
        attrs={"itemprop": "description"},
    )

    description = ""

    if description_tag and description_tag.get("content"):
        description = description_tag["content"].strip()

    data = {
        "URL": url,
    }

    if description:
        data["titulo"] = description
        data["descripcion_original"] = description

    # Extraer las descripciones del anverso y del reverso.
    if "Anv:" in description and "Rev:" in description:
        partes = description.split("Anv:", 1)
        texto_anverso_y_reverso = partes[1]

        partes_reverso = texto_anverso_y_reverso.split("Rev:", 1)

        anverso = partes_reverso[0].strip()
        reverso = partes_reverso[1].strip()

        if anverso:
            data["descripcion_imagen_anverso"] = anverso

        # Eliminar la conservación y los comentarios posteriores.
        reverso = re.split(
            r"\s+(?:EBC|MBC|BC)\b",
            reverso,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if reverso:
            data["descripcion_imagen_reverso"] = reverso

    # Extraer el precio (si existe)
    price_tag = soup.find(
        "meta",
        attrs={"itemprop": "price"},
    )

    if price_tag and price_tag.get("content"):
        try:
            data["precio"] = float(
                price_tag["content"].replace(",", ".")
            )

        except (ValueError, AttributeError):
            pass

    # Extraer la imagen principal.
    image_tag = soup.find(
        "meta",
        attrs={"itemprop": "image"},
    )

    if image_tag and image_tag.get("content"):
        data["imagenes"] = [
            urljoin(url, image_tag["content"])
        ]

    else:
        image_tag = soup.find(
            "link",
            attrs={"itemprop": "image"},
        )

        if image_tag and image_tag.get("href"):
            data["imagenes"] = [
                urljoin(url, image_tag["href"])
            ]

    # Extraer los años en los que se acuña.
    year_match = re.search(
        r"(\b\d+(?:-\d+)?\s*(?:a\.C\.|d\.C\.|BC|AD)\b|\bSiglo\s+[IVXLCDM]+(?:\s*-\s*Siglo\s+[IVXLCDM]+)?\s*(?:a\.C\.|d\.C\.)?\b|\b\d{4}(?:-\d{4})?\b)",
        description,
        re.IGNORECASE,
    )

    if year_match:
        data["años en las que se acuña"] = year_match.group(1).strip()

    # Extraer inscripción del reverso.
    rev_insc = re.search(
        r"leyenda:\s*([^,.\n]+)",
        description,
        re.IGNORECASE,
    )

    if rev_insc:
        data["inscripción reverso"] = rev_insc.group(1).strip()

    # Extraer mintmark.
    mint_match = re.search(
        r"(?:a\.C\.|d\.C\.)\s+([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[a-z]+)?)\.\s*\(",
        description,
    )

    if mint_match:
        data["mintmark"] = mint_match.group(1).strip()

    return data



def get_coin_url(soup: BeautifulSoup) -> str:
    """Intenta recuperar la URL original de la ficha."""

    canonical = soup.find(
        "link",
        rel="canonical",
    )

    if canonical and canonical.get("href"):
        return canonical["href"].strip()

    og_url = soup.find(
        "meta",
        property="og:url",
    )

    if og_url and og_url.get("content"):
        return og_url["content"].strip()

    return ""


def acquire_ibercoin(output_dir: Path) -> None:
    """Procesa todas las fichas HTML guardadas y genera un JSON."""

    project_root = Path(__file__).resolve().parents[2]

    raw_dir = (
        project_root
        / "data"
        / "raw"
        / "ibercoin"
    )

    # Buscar las fichas descargadas por el catálogo.
    html_files = sorted(raw_dir.glob("moneda_*.html"))

    # Si no hay fichas del catálogo, intentar la ficha de prueba.
    if not html_files:
        test_file = raw_dir / "moneda_prueba.html"

        if test_file.exists():
            html_files = [test_file]

    print(f"Fichas HTML encontradas: {len(html_files)}")

    monedas = []
    descartadas = 0
    errores = 0

    for index, html_file in enumerate(html_files, start=1):
        try:
            html = html_file.read_text(
                encoding="utf-8",
                errors="replace",
            )

            soup = BeautifulSoup(html, "lxml")
            url = get_coin_url(soup)

            if not url:
                print(
                    f"[{index}] No se pudo recuperar la URL: "
                    f"{html_file.name}"
                )
                descartadas += 1
                continue

            moneda = extract_coin_data(html, url)

            # Comprobar los campos esenciales del proyecto.
            if (
                moneda.get("URL")
                and moneda.get("imagenes")
                and moneda.get("descripcion_imagen_anverso")
            ):
                monedas.append(moneda)

            else:
                descartadas += 1
                print(
                    f"[{index}] Ficha incompleta: "
                    f"{html_file.name}"
                )

        except Exception as error:
            errores += 1
            print(
                f"[{index}] Error en {html_file.name}: {error}"
            )

        if index % 25 == 0 or index == len(html_files):
            print(
                f"Progreso: {index}/{len(html_files)}"
            )

    # Guardar el resultado en data/processed.
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = output_dir / "ibercoin.json"

    output_file.write_text(
        json.dumps(
            monedas,
            ensure_ascii=False,
            indent=2,
        ),
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

    output_dir = (
        project_root
        / "data"
        / "processed"
    )

    acquire_ibercoin(output_dir)
