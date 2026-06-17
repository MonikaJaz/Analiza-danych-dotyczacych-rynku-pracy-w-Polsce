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


# ID zmiennych BDL

# P1364 – Bezrobotni zarejestrowani ogółem
bezrobotni_kobiety   = "33521"   # kobiety
bezrobotni_mezczyzni = "33519"   # mężczyźni
bezrobotni_ogolem    = "33507"   # ogółem
#
# P1365 – Oferty pracy
oferty_koniec_roku = "3285"      # ogółem, w końcu roku
oferty_wciagu_roku  = "1610567"   # ogółem, w ciągu roku
#
# P1947 – Bezrobotni wg wykształcenia (ogółem)
wyksztalcenie_ogolem      = "47058"
wyksztalcenie_wyzsze      = "47053"
wyksztalcenie_policealne  = "47062"
wyksztalcenie_srednie     = "47060"
wyksztalcenie_zasadnicze  = "47063"
wyksztalcenie_podstawowe  = "47049"
#
# P1946 – Bezrobotni wg wieku (ogółem, bez podziału na płeć)
wiek_18_24  = "8813"
wiek_25_34  = "8815"
wiek_35_44  = "8817"
wiek_45_54  = "8819"
wiek_55plus = "8821"
#
# P1949 – Bezrobotni wg stażu pracy (ogółem)
staz_bez        = "47177"
staz_do1        = "47167"
staz_1do5       = "47182"
staz_1do10      = "47188"
staz_10do20     = "47190"
staz_20do30     = "47176"
staz_powyzej30  = "47171"

# P4334 – Napięcie rynku pracy
napiecie_rynku       = "1702029"   # bezrobotni na 1 ofertę pracy [osoba]
oferty_pracy         = "1702031"   # P1365
stopa_bezrobocia     = "60270"   # P2392
wynagrodzenie        = "64428"   # przeciętne miesięczne wynagrodzenie brutto [PLN]

# Słownik województw
WOJEWODZTWA = {
    "020000000000": "DOLNOŚLĄSKIE",
    "040000000000": "KUJAWSKO-POMORSKIE",
    "060000000000": "LUBELSKIE",
    "080000000000": "LUBUSKIE",
    "100000000000": "ŁÓDZKIE",
    "120000000000": "MAŁOPOLSKIE",
    "140000000000": "MAZOWIECKIE",
    "160000000000": "OPOLSKIE",
    "180000000000": "PODKARPACKIE",
    "200000000000": "PODLASKIE",
    "220000000000": "POMORSKIE",
    "240000000000": "ŚLĄSKIE",
    "260000000000": "ŚWIĘTOKRZYSKIE",
    "280000000000": "WARMIŃSKO-MAZURSKIE",
    "300000000000": "WIELKOPOLSKIE",
    "320000000000": "ZACHODNIOPOMORSKIE",
}

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

    df = pd.DataFrame(wiersze)
    if not df.empty:
        df["wartosc"] = pd.to_numeric(df["wartosc"], errors="coerce")
        df["rok"] = pd.to_numeric(df["rok"], errors="coerce").astype("Int64")
    return df

def pobierz_jednostki(poziom: int = 2) -> pd.DataFrame:
    """Zwraca jednostki terytorialne dla wskazanego poziomu BDL."""
    rekordy = _pobierz_wszystkie_strony("/units", parametry={"level": poziom})
    return _dataframe_z_wynikow(rekordy)

def pobierz_trend_bezrobocia_plec(rok_od: int, rok_do: int, wojew: str | None = None) -> pd.DataFrame:
    poziom = 2 if wojew else 0
    filtr = wojew.upper() if wojew else "POLSKA"
    dfs = {}
    for etykieta, id_var in [
        ("Ogółem", bezrobotni_ogolem),
        ("Kobiety", bezrobotni_kobiety),
        ("Mężczyźni", bezrobotni_mezczyzni),
    ]:
        df = pobierz_dane_wskaznika(id_var, rok_od, rok_do, poziom_jednostki=poziom)
        df = df[df["jednostka"].str.upper() == filtr].copy()
        df = df.groupby("rok")["wartosc"].sum().reset_index()
        df.columns = ["rok", etykieta]
        dfs[etykieta] = df

    wynik = dfs["Ogółem"]
    for klucz in ["Kobiety", "Mężczyźni"]:
        wynik = wynik.merge(dfs[klucz], on="rok", how="outer")

    wynik = wynik.sort_values("rok").reset_index(drop=True)
    if "Kobiety" in wynik.columns and "Mężczyźni" in wynik.columns:
        wynik["Różnica (K–M)"] = wynik["Kobiety"] - wynik["Mężczyźni"]
    return wynik

def pobierz_trend_stopy_bezrobocia(rok_od: int, rok_do: int, wojew: str | None = None) -> pd.DataFrame:
    poziom = 2 if wojew else 0
    filtr = wojew.upper() if wojew else "POLSKA"
    df = pobierz_dane_wskaznika(stopa_bezrobocia, rok_od, rok_do, poziom_jednostki=poziom)
    df = df[df["jednostka"].str.upper() == filtr].copy()
    return df.sort_values("rok").reset_index(drop=True)

def pobierz_trend_wynagrodzen(rok_od: int, rok_do: int, wojew: str | None = None) -> pd.DataFrame:
    poziom = 2 if wojew else 0
    filtr = wojew.upper() if wojew else "POLSKA"
    df = pobierz_dane_wskaznika(wynagrodzenie, rok_od, rok_do, poziom_jednostki=poziom)
    df = df[df["jednostka"].str.upper() == filtr].copy()
    return df.sort_values("rok").reset_index(drop=True)

def pobierz_trend_ofert_pracy(rok_od: int, rok_do: int, wojew: str | None = None) -> pd.DataFrame:
    poziom = 2 if wojew else 0
    filtr = wojew.upper() if wojew else "POLSKA"
    df = pobierz_dane_wskaznika(oferty_pracy, rok_od, rok_do, poziom_jednostki=poziom)
    df = df[df["jednostka"].str.upper() == filtr].copy()
    return df.sort_values("rok").reset_index(drop=True)

def pobierz_mape_stopy_bezrobocia(rok: int) -> pd.DataFrame:
    df = pobierz_dane_wskaznika(stopa_bezrobocia, rok, rok, poziom_jednostki=2)
    df = df[df["rok"] == rok].copy()
    return df.sort_values("wartosc", ascending=False).reset_index(drop=True)

def pobierz_mape_wynagrodzen(rok: int) -> pd.DataFrame:
    df = pobierz_dane_wskaznika(wynagrodzenie, rok, rok, poziom_jednostki=2)
    df = df[df["rok"] == rok].copy()
    return df.sort_values("wartosc", ascending=False).reset_index(drop=True)

def pobierz_napiecie_rynku(rok: int) -> pd.DataFrame:
    df = pobierz_dane_wskaznika(napiecie_rynku, rok, rok, poziom_jednostki=2)
    df = df[df["rok"] == rok].copy()
    return df.sort_values("wartosc", ascending=False).reset_index(drop=True)

def _agreguj_strukture(grupy: dict[str, str], kolumna: str,
                        rok: int, wojew: str | None) -> pd.DataFrame:
    wiersze = []
    for nazwa, id_var in grupy.items():
        df = pobierz_dane_wskaznika(id_var, rok, rok, poziom_jednostki=2)
        df = df[df["rok"] == rok]
        if wojew:
            df = df[df["jednostka"].str.upper() == wojew.upper()]
        wartosc = df["wartosc"].sum()
        wiersze.append({kolumna: nazwa, "liczba": wartosc})
    return pd.DataFrame(wiersze)


def pobierz_strukture_wyksztalcenia(rok: int, wojew: str | None = None) -> pd.DataFrame:
    return _agreguj_strukture({
        "Wyższe": wyksztalcenie_wyzsze,
        "Policealne i śr. zawodowe": wyksztalcenie_policealne,
        "Średnie ogólnokształcące": wyksztalcenie_srednie,
        "Zasadnicze zawodowe": wyksztalcenie_zasadnicze,
        "Podstawowe i niższe": wyksztalcenie_podstawowe,
    }, "wyksztalcenie", rok, wojew)


def pobierz_strukture_wieku(rok: int, wojew: str | None = None) -> pd.DataFrame:
    return _agreguj_strukture({
        "do 24 lat": wiek_18_24,
        "25–34 lata": wiek_25_34,
        "35–44 lata": wiek_35_44,
        "45–54 lata": wiek_45_54,
        "55 lat i więcej": wiek_55plus,
    }, "wiek", rok, wojew)


def pobierz_strukture_stazu(rok: int, wojew: str | None = None) -> pd.DataFrame:
    return _agreguj_strukture({
        "Bez stażu": staz_bez,
        "Do 1 roku": staz_do1,
        "1–5 lat": staz_1do5,
        "5–10 lat": staz_1do10,
        "10–20 lat": staz_10do20,
        "20–30 lat": staz_20do30,
        "Powyżej 30 lat": staz_powyzej30,
    }, "staz", rok, wojew)


def pobierz_strukture_plci(rok: int, wojew: str | None = None) -> pd.DataFrame:
    return _agreguj_strukture({
        "Kobiety": bezrobotni_kobiety,
        "Mężczyźni": bezrobotni_mezczyzni,
    }, "plec", rok, wojew)

def pobierz_kpi(rok: int) -> dict[str, float | str]:
    """Pobiera kluczowe wskaźniki dla wybranego roku – Polska."""
    wynik: dict[str, float | str] = {}

    try:
        df = pobierz_dane_wskaznika(stopa_bezrobocia, rok, rok, poziom_jednostki=0)
        df = df[df["jednostka"].str.upper() == "POLSKA"]
        wynik["stopa_bezrobocia"] = round(float(df["wartosc"].iloc[0]), 1) if not df.empty else "brak"
    except (KeyError, IndexError, ValueError):
        wynik["stopa_bezrobocia"] = "brak"

    try:
        df = pobierz_dane_wskaznika(wynagrodzenie, rok, rok, poziom_jednostki=0)
        df = df[df["jednostka"].str.upper() == "POLSKA"]
        wynik["wynagrodzenie"] = round(float(df["wartosc"].iloc[0]), 0) if not df.empty else "brak"
    except (KeyError, IndexError, ValueError):
        wynik["wynagrodzenie"] = "brak"

    try:
        df = pobierz_dane_wskaznika(bezrobotni_ogolem, rok, rok, poziom_jednostki=0)
        df = df[df["jednostka"].str.upper() == "POLSKA"]
        wynik["bezrobotni"] = int(df["wartosc"].iloc[0]) if not df.empty else "brak"
    except (KeyError, IndexError, ValueError):
        wynik["bezrobotni"] = "brak"

    try:
        df = pobierz_dane_wskaznika(oferty_pracy, rok, rok, poziom_jednostki=0)
        df = df[df["jednostka"].str.upper() == "POLSKA"]
        wynik["oferty"] = int(df["wartosc"].iloc[0]) if not df.empty else "brak"
    except (KeyError, IndexError, ValueError):
        wynik["oferty"] = "brak"

    return wynik