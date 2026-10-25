from pathlib import Path

from sources.ibercoin import acquire_ibercoin


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def main() -> None:
    """Coordina la adquisición de datos de las fuentes."""

    ibercoin_dir = RAW_DIR / "ibercoin"
    ibercoin_dir.mkdir(parents=True, exist_ok=True)

    print("Iniciando adquisición de datos...")

    acquire_ibercoin(ibercoin_dir)

    print("Adquisición finalizada.")


if __name__ == "__main__":
    main()

