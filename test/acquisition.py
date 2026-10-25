from pathlib import Path
import requests 
from bs4 import BeautifulSoup

# ibercoin

URL = (
    "https://www.ibercoin.com/es/tienda-numismatica/"
    "monedas/2-grecia-antigua/prod-7329-ATTICA-Atenas"
)

OUTPUT_DIR = Path("../data/raw/ibercoin")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_page(url: str) -> str:
    """Descarga una página y devuelve su HTML original."""
    response = requests.get(
        url,
        headers={
            "User-Agent": "NumismaticAcademicProject/1.0"
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def main() -> None:
    try:
        html = download_page(URL)

        # Conservamos el HTML original para poder reprocesarlo.
        output_file = OUTPUT_DIR / "moneda_prueba.html"
        output_file.write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")

        print("\n--- TITULO DE LA PAGINA ---")
        print(soup.title.get_text(strip=True) if soup.title else "No encontrado")

        print("\n--- PRIMEROS 5000 CARACTERES DE TEXTO ---")
        print(soup.get_text(" ", strip=True)[:5000])

        print("Página descargada correctamente.")
        print(f"Título HTML: {soup.title.get_text(strip=True) if soup.title else 'No encontrado'}")
        print(f"Archivo guardado: {output_file}")
        print(f"Tamaño HTML: {len(html)} caracteres")

    except requests.RequestException as error:
        print(f"No se pudo descargar la página: {error}")


if __name__ == "__main__":
    main()


