"""

Dokumentacja API: https://bdl.stat.gov.pl/api/v1/swagger/index.html

"""
from dotenv import load_dotenv
import os
import requests
import pandas as pd

#konfiguracja api i klucza
BASE_URL = "https://bdl.stat.gov.pl/api/v1"
load_dotenv()
KLUCZ_API = os.getenv("GUS_API_KEY", "")
DOMYSLNE_PARAMETRY = {
    "format": "json",
    "lang": "pl",
}


#funkcja do łączenia się z api
def _pobierz_dane(endpoint: str, parametry: dict = None) -> dict:

    wszystkie_parametry = {**DOMYSLNE_PARAMETRY}
    if parametry:
        wszystkie_parametry.update(parametry)

    url = f"{BASE_URL}{endpoint}"

    try:
        odpowiedz = requests.get(
            url,
            params=wszystkie_parametry,
            headers={"X-ClientId": KLUCZ_API} if KLUCZ_API else {},
            timeout=15
        )
        odpowiedz.raise_for_status() #check czy serwer nie zwróci błędu
        return odpowiedz.json()

    except requests.exceptions.ConnectionError:
        raise ConnectionError("Brak połączenia z internetem.")
    except requests.exceptions.Timeout:
        raise TimeoutError("Serwer GUS nie odpowiada (timeout).")
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"Błąd HTTP: {e}")
    except requests.exceptions.JSONDecodeError:
        raise ValueError(
            f"Serwer nie zwrócił JSON.\n"
            f"Status: {odpowiedz.status_code}\n"
            f"Odpowiedź: {odpowiedz.text[:200]}"
        )


# 4 funkcje do pobierania danych

#funkcja do pobierania kategori e.g. rynek pracy
def pobierz_tematy(id_nadrzedny: str = None) -> pd.DataFrame:

    parametry = {"parentId": id_nadrzedny} if id_nadrzedny else None
    dane = _pobierz_dane("/subjects", parametry=parametry)
    lista = dane.get("results", [])
    return pd.DataFrame(lista)

#funkcja do pobierania wskaźników z danej kategorii
def pobierz_zmienne(id_tematu: str, strona: int = 0) -> pd.DataFrame:
    dane = _pobierz_dane(
        "/variables",
        parametry={"subject-id": id_tematu, "page": strona, "page-size": 100}
    )
    lista = dane.get("results", [])
    return pd.DataFrame(lista)

#dane dla poszczególnych wskaźników
def pobierz_dane_wskaznika(id_zmiennej: str, rok_od: int, rok_do: int,
                           poziom_jednostki: int = 2) -> pd.DataFrame:

    lata = [str(r) for r in range(rok_od, rok_do + 1)]

    dane = _pobierz_dane(
        f"/data/by-variable/{id_zmiennej}",
        parametry={
            "unit-level": poziom_jednostki,
            "year": lata,
            "page-size": 100,
        }
    )

    lista = dane.get("results", [])
    if not lista:
        return pd.DataFrame()

    wiersze = []
    for rekord in lista:
        for wartosc in rekord.get("values", []):
            wiersze.append({
                "id_jednostki": rekord.get("id", ""),
                "jednostka":    rekord.get("name", ""),
                "rok":          wartosc.get("year"),
                "wartosc":      wartosc.get("val"),
            })

    return pd.DataFrame(wiersze)


#funkcja pobierająca jednostki administracyjne (województwa)
def pobierz_jednostki(poziom: int = 2) -> pd.DataFrame:

    dane = _pobierz_dane("/units", parametry={"level": poziom, "page-size": 100})
    lista = dane.get("results", [])
    return pd.DataFrame(lista)


if __name__ == "__main__":
    import json

    # Szukamy wskaźników dla wszystkich analiz
    do_sprawdzenia = {
        "P1364": "Bezrobotni wg płci i typu (analiza 1,2,4)",
        "P1947": "Bezrobotni wg wykształcenia (analiza 3)",
        "P1948": "Bezrobotni wg czasu bez pracy (analiza 6)",
        "P1365": "Oferty pracy (analiza 7)",
    }

    for id_p, opis in do_sprawdzenia.items():
        print(f"\n{'='*60}")
        print(f"{id_p} — {opis}")
        dane = _pobierz_dane("/variables", parametry={"subject-id": id_p, "page-size": 100})
        for w in dane.get("results", []):
            print(f"  id={w['id']}  |  {w.get('n1','')} / {w.get('n2','')}  |  {w.get('measureUnitName','')}")