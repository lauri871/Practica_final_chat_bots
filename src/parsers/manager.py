from src.parsers.biddr import parse_all_biddr
from src.parsers.ibercoin import parse_all_ibercoin


def run_all_parsers() -> None:
    """Ejecuta de forma secuencial todos los parsers del proyecto."""
    print("Iniciando procesamiento de Ibercoin...")
    parse_all_ibercoin()
    
    print("Iniciando procesamiento de Biddr...")
    parse_all_biddr()
    
    print("Todos los parsers han finalizado con éxito.")


if __name__ == "__main__":
    run_all_parsers()