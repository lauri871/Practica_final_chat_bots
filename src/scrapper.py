import sys
from src.configuracion.constants import TARGET_ITEMS_PER_SOURCE
from src.scrapers.manager import run_all_scrapers


def main() -> None:
    """Punto de entrada general para ejecutar la adquisición de datos."""
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else TARGET_ITEMS_PER_SOURCE
    results = run_all_scrapers(limit=limit)
    total = sum(len(files) for files in results.values())
    print(f"\nAdquisición finalizada con éxito.")
    print(f"Total de archivos brutos disponibles en disco: {total}")


if __name__ == "__main__":
    main()