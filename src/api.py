"""Warstwa komunikacji z API Banku Danych Lokalnych GUS.

Dokumentacja API:
https://bdl.stat.gov.pl/api/v1/swagger/index.html
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_URL = "https://bdl.stat.gov.pl/api/v1"
TIMEOUT = 15
PAGE_SIZE = 100
DOMYSLNE_PARAMETRY = {
    "format": "json",
    "lang": "pl",
}

load_dotenv()
KLUCZ_API = os.getenv("GUS_API_KEY", "")


class GusApiError(RuntimeError):
    """Blad komunikacji z API BDL GUS."""


def _naglowki() -> dict[str, str]:
    if not KLUCZ_API:
        return {}
    return {"X-ClientId": KLUCZ_API}


def pobierz_json(endpoint: str, parametry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pobiera surowa odpowiedz JSON z API GUS BDL."""
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    wszystkie_parametry: dict[str, Any] = dict(DOMYSLNE_PARAMETRY)
    if parametry:
        wszystkie_parametry.update(parametry)

    try:
        odpowiedz = requests.get(
            f"{BASE_URL}{endpoint}",
            params=wszystkie_parametry,
            headers=_naglowki(),
            timeout=TIMEOUT,
        )
        odpowiedz.raise_for_status()
        return odpowiedz.json()
    except requests.exceptions.HTTPError as e:
        raise GusApiError(f"API GUS zwrocilo blad HTTP: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise GusApiError("Brak polaczenia z internetem lub API GUS.") from e
    except requests.exceptions.Timeout as e:
        raise GusApiError("Serwer GUS nie odpowiedzial w wyznaczonym czasie.") from e
    except requests.exceptions.RequestException as e:
        raise GusApiError(f"Blad zapytania do API GUS: {e}") from e
    except ValueError as e:
        status = getattr(odpowiedz, "status_code", "brak")
        tekst = getattr(odpowiedz, "text", "")
        raise GusApiError(
            f"API GUS nie zwrocilo poprawnego JSON. Status: {status}. "
            f"Fragment odpowiedzi: {tekst[:200]}"
        ) from e


def _pobierz_wszystkie_strony(
    endpoint: str,
    parametry: dict[str, Any] | None = None,
    rozmiar_strony: int = PAGE_SIZE,
) -> list[dict[str, Any]]:
    """Pobiera wszystkie strony endpointu, ktory zwraca pole `results`."""
    wyniki: list[dict[str, Any]] = []
    strona = 0

    while True:
        parametry_strony = dict(parametry or {})
        parametry_strony.update({"page": strona, "page-size": rozmiar_strony})

        dane = pobierz_json(endpoint, parametry_strony)
        rekordy = dane.get("results", [])
        if not isinstance(rekordy, list):
            raise GusApiError("Nieoczekiwany format odpowiedzi API: pole results nie jest lista.")

        wyniki.extend(rekordy)

        liczba_stron = dane.get("totalPages") or dane.get("total-pages")
        if liczba_stron is not None:
            if strona >= int(liczba_stron) - 1:
                break
        elif len(rekordy) < rozmiar_strony:
            break

        strona += 1

    return wyniki


def _dataframe_z_wynikow(rekordy: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rekordy)


def pobierz_tematy(id_nadrzedny: str | None = None) -> pd.DataFrame:
    """Zwraca liste tematow BDL, opcjonalnie dla tematu nadrzednego."""
    parametry = {"parent-id": id_nadrzedny} if id_nadrzedny else None
    rekordy = _pobierz_wszystkie_strony("/subjects", parametry=parametry)
    return _dataframe_z_wynikow(rekordy)


def pobierz_zmienne(id_tematu: str) -> pd.DataFrame:
    """Zwraca zmienne/wskazniki dostepne dla podanego tematu BDL."""
    rekordy = _pobierz_wszystkie_strony(
        "/variables",
        parametry={"subject-id": id_tematu},
    )
    return _dataframe_z_wynikow(rekordy)


def pobierz_dane_wskaznika(
    id_zmiennej: str,
    rok_od: int,
    rok_do: int,
    poziom_jednostki: int = 2,
) -> pd.DataFrame:
    """Zwraca dane wskaznika dla zakresu lat i poziomu jednostki terytorialnej."""
    if rok_od > rok_do:
        raise ValueError("Parametr 'rok_od' nie moze byc wiekszy niz 'rok_do'.")

    lata = [str(rok) for rok in range(rok_od, rok_do + 1)]
    rekordy = _pobierz_wszystkie_strony(
        f"/data/by-variable/{id_zmiennej}",
        parametry={
            "unit-level": poziom_jednostki,
            "year": lata,
        },
    )

    wiersze: list[dict[str, Any]] = []
    for rekord in rekordy:
        for wartosc in rekord.get("values", []):
            wiersze.append(
                {
                    "id_jednostki": rekord.get("id", ""),
                    "jednostka": rekord.get("name", ""),
                    "rok": wartosc.get("year"),
                    "wartosc": wartosc.get("val"),
                }
            )

    return pd.DataFrame(wiersze)


def pobierz_jednostki(poziom: int = 2) -> pd.DataFrame:
    """Zwraca jednostki terytorialne dla wskazanego poziomu BDL."""
    rekordy = _pobierz_wszystkie_strony("/units", parametry={"level": poziom})
    return _dataframe_z_wynikow(rekordy)
