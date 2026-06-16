"""Pomocniczy skrypt do sprawdzenia komunikacji z API GUS BDL."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.api import pobierz_tematy, pobierz_zmienne


def main() -> None:
    id_tematu1 = "G623"
    print(f"\nPierwsze zmienne dla tematu {id_tematu1}:")
    zmienne = pobierz_tematy(id_tematu1)
    print(zmienne.to_string(index=False))


    id_tematu = "P1947"
    print(f"\nPierwsze zmienne dla tematu {id_tematu}:")
    zmienne = pobierz_zmienne(id_tematu)
    print(zmienne.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
