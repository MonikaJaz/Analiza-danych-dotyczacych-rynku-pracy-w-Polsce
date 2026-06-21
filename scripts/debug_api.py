"""
Skrypt diagnostyczny – weryfikacja zmiennych BDL GUS używanych w projekcie.

Uruchamianie:
    python scripts/debug_api.py

Sekcje:
  1. Hierarchia tematów rynku pracy w BDL
  2. Wszystkie zmienne dla tematów używanych w projekcie
  3. Weryfikacja – czy ID w projekcie zwracają poprawne dane
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests
import pandas as pd

from src.api import (
    BASE_URL, DOMYSLNE_PARAMETRY, _naglowki, GusApiError,
    pobierz_tematy, pobierz_zmienne, pobierz_dane_wskaznika,
)


# ---------------------------------------------------------------------------
# Tematy (subject ID) używane w projekcie
# ---------------------------------------------------------------------------
TEMATY_PROJEKTU = {
    "P1364": "Bezrobotni zarejestrowani ogółem",
    "P1365": "Oferty pracy",
    "P1946": "Bezrobotni wg wieku",
    "P1947": "Bezrobotni wg wykształcenia",
    "P1949": "Bezrobotni wg stażu pracy",
    "P2392": "Stopa bezrobocia rejestrowanego",
    "P4334": "Napięcie rynku pracy",
    "P3972": "Wynagrodzenia (wynagrodzenie brutto)",
}

# ---------------------------------------------------------------------------
# Zmienne (variable ID) używane w projekcie
# Kolumny: (nazwa_w_kodzie, id, opis_w_projekcie, temat, używana_w_funkcji)
# ---------------------------------------------------------------------------
ZMIENNE_PROJEKTU = [
    # Bezrobotni
    ("bezrobotni_ogolem",        "33507",   "Bezrobotni ogółem",                 "P1364", True),
    ("bezrobotni_kobiety",       "33521",   "Bezrobotni – kobiety",              "P1364", True),
    ("bezrobotni_mezczyzni",     "33519",   "Bezrobotni – mężczyźni",            "P1364", True),
    # Oferty pracy
    ("oferty_koniec_roku",       "3285",    "Oferty pracy (koniec roku)",         "P1365", False),
    ("oferty_wciagu_roku",       "1610567", "Oferty pracy (w ciągu roku)",        "P1365", False),
    ("oferty_pracy",             "1702031", "Oferty pracy (P4334)",               "P4334", True),
    # Stopa bezrobocia / wynagrodzenie / napięcie
    ("stopa_bezrobocia",         "60270",   "Stopa bezrobocia rejestrowanego",    "P2392", True),
    ("wynagrodzenie",            "64428",   "Wynagrodzenie brutto [PLN]",         "P3972", True),
    ("napiecie_rynku",           "1702029", "Napięcie rynku – bezrob. na ofertę", "P4334", True),
    # Wykształcenie
    ("wyksztalcenie_ogolem",     "47058",   "Wykszt. ogółem",                    "P1947", False),
    ("wyksztalcenie_wyzsze",     "47053",   "Wykszt. wyższe",                    "P1947", True),
    ("wyksztalcenie_policealne", "47062",   "Wykszt. policealne i śr. zawodowe", "P1947", True),
    ("wyksztalcenie_srednie",    "47060",   "Wykszt. średnie ogólnokształcące",  "P1947", True),
    ("wyksztalcenie_zasadnicze", "47063",   "Wykszt. zasadnicze zawodowe",       "P1947", True),
    ("wyksztalcenie_podstawowe", "47049",   "Wykszt. podstawowe i niższe",       "P1947", True),
    # Wiek
    ("wiek_18_24",               "8813",    "Wiek 18–24 lata",                   "P1946", True),
    ("wiek_25_34",               "8815",    "Wiek 25–34 lata",                   "P1946", True),
    ("wiek_35_44",               "8817",    "Wiek 35–44 lata",                   "P1946", True),
    ("wiek_45_54",               "8819",    "Wiek 45–54 lata",                   "P1946", True),
    ("wiek_55plus",              "8821",    "Wiek 55 lat i więcej",              "P1946", True),
    # Staż pracy
    ("staz_bez",                 "47177",   "Staż: bez stażu",                   "P1949", True),
    ("staz_do1",                 "47167",   "Staż: do 1 roku",                   "P1949", True),
    ("staz_1do5",                "47182",   "Staż: 1–5 lat",                     "P1949", True),
    ("staz_1do10",               "47188",   "Staż: 5–10 lat",                    "P1949", True),
    ("staz_10do20",              "47190",   "Staż: 10–20 lat",                   "P1949", True),
    ("staz_20do30",              "47176",   "Staż: 20–30 lat",                   "P1949", True),
    ("staz_powyzej30",           "47171",   "Staż: powyżej 30 lat",              "P1949", True),
]

ROK_TEST = 2022   # rok używany do weryfikacji danych


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------

def pobierz_info_zmiennej(id_zmiennej: str) -> dict:
    """Pobiera metadane jednej zmiennej z BDL (/variables/{id})."""
    try:
        resp = requests.get(
            f"{BASE_URL}/variables/{id_zmiennej}",
            params=DOMYSLNE_PARAMETRY,
            headers=_naglowki(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def pobierz_info_tematu(id_tematu: str) -> dict:
    """Pobiera metadane jednego tematu z BDL (/subjects/{id})."""
    try:
        resp = requests.get(
            f"{BASE_URL}/subjects/{id_tematu}",
            params=DOMYSLNE_PARAMETRY,
            headers=_naglowki(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def separator(znak: str = "=", dlugosc: int = 80) -> None:
    print(znak * dlugosc)


def naglowek(tekst: str) -> None:
    print()
    separator()
    print(f"  {tekst}")
    separator()


# ---------------------------------------------------------------------------
# SEKCJA 1 – Hierarchia tematów rynku pracy
# ---------------------------------------------------------------------------

def sekcja_hierarchia_tematow() -> None:
    naglowek("SEKCJA 1 – HIERARCHIA TEMATÓW RYNKU PRACY W BDL")

    print("\n>> Pobieranie tematów głównych (root)...")
    try:
        df_root = pobierz_tematy()
    except GusApiError as e:
        print(f"  BŁĄD: {e}")
        return

    # Filtruj tematy związane z rynkiem pracy
    slowa_kluczowe = ["prac", "bezrobocie", "bezrobotn", "zatrudn", "wynagrodzeni", "zarobk"]
    mask = df_root["name"].str.lower().apply(
        lambda n: any(s in n for s in slowa_kluczowe)
    )
    df_praca = df_root[mask]

    if df_praca.empty:
        print("  Nie znaleziono tematów głównych związanych z rynkiem pracy.")
        print("  Wszystkie tematy główne:")
        for _, row in df_root.iterrows():
            print(f"    [{row['id']}] {row['name']}")
    else:
        print(f"\n  Znalezione tematy główne ({len(df_praca)}):")
        for _, row in df_praca.iterrows():
            print(f"    [{row['id']}] {row['name']}")
            try:
                df_dzieci = pobierz_tematy(row["id"])
                for _, dziecko in df_dzieci.iterrows():
                    print(f"        └─ [{dziecko['id']}] {dziecko['name']}")
            except GusApiError:
                print("        └─ (błąd pobierania podtematów)")

    # Sprawdź każdy temat projektu bezpośrednio
    print("\n>> Metadane tematów używanych w projekcie:")
    separator("-", 60)
    for id_t, opis in TEMATY_PROJEKTU.items():
        info = pobierz_info_tematu(id_t)
        if "error" in info:
            print(f"  [{id_t}] {opis}")
            print(f"        BŁĄD: {info['error']}")
        else:
            nazwa_api = info.get("name", "—")
            nadrzedny = info.get("parentId", "brak")
            print(f"  [{id_t}] Projekt: \"{opis}\"")
            print(f"        API:     \"{nazwa_api}\"  (nadrzędny: {nadrzedny})")
            dopasowanie = "✓ OK" if opis.lower()[:10] in nazwa_api.lower() else "△ sprawdź"
            print(f"        Dopasowanie nazwy: {dopasowanie}")
        print()


# ---------------------------------------------------------------------------
# SEKCJA 2 – Wszystkie zmienne dla tematów projektu
# ---------------------------------------------------------------------------

def sekcja_zmienne_wg_tematow() -> None:
    naglowek("SEKCJA 2 – WSZYSTKIE ZMIENNE DLA TEMATÓW PROJEKTU")
    print("  (Lista wszystkich zmiennych dostępnych pod danym tematem BDL)\n")

    for id_t, opis in TEMATY_PROJEKTU.items():
        separator("-", 60)
        print(f"  Temat [{id_t}]: {opis}")
        try:
            df = pobierz_zmienne(id_t)
        except GusApiError as e:
            print(f"    BŁĄD: {e}\n")
            continue

        if df.empty:
            print("    Brak zmiennych.\n")
            continue

        # Zmienne używane w projekcie dla tego tematu
        uzywane_w_projekcie = {z[1] for z in ZMIENNE_PROJEKTU if z[3] == id_t}

        for _, row in df.iterrows():
            oznaczenie = " ◄ PROJEKT" if str(row.get("id", "")) in uzywane_w_projekcie else ""
            print(f"    id={row.get('id', '?'):<12} | {row.get('name', '?')}{oznaczenie}")
        print(f"    Łącznie zmiennych: {len(df)}\n")


# ---------------------------------------------------------------------------
# SEKCJA 3 – Weryfikacja ID zmiennych projektu
# ---------------------------------------------------------------------------

def sekcja_weryfikacja_id() -> None:
    naglowek(f"SEKCJA 3 – WERYFIKACJA ID ZMIENNYCH PROJEKTU (rok testowy: {ROK_TEST})")
    print()

    wyniki = []

    for nazwa_kod, id_var, opis_projekt, temat, uzywana in ZMIENNE_PROJEKTU:
        print(f"  Sprawdzam: {nazwa_kod} (id={id_var})...", end=" ", flush=True)

        # 1) Metadane zmiennej z API
        info = pobierz_info_zmiennej(id_var)
        if "error" in info:
            print(f"BŁĄD metadanych: {info['error']}")
            wyniki.append({
                "zmienna":      nazwa_kod,
                "id":           id_var,
                "opis_projekt": opis_projekt,
                "nazwa_api":    "—",
                "temat_api":    "—",
                "ostatnia_wartosc": "—",
                "status":       f"BŁĄD: {info['error']}",
                "uzywana":      uzywana,
            })
            continue

        nazwa_api = info.get("name", "—")
        temat_api = info.get("subjectId", "—")

        # 2) Próbka danych – poziom 0 (Polska), rok testowy
        status = ""
        ostatnia_wartosc = "—"
        try:
            df = pobierz_dane_wskaznika(id_var, ROK_TEST, ROK_TEST, poziom_jednostki=0)
            if df.empty:
                # Spróbuj poziom 2 (województwa)
                df = pobierz_dane_wskaznika(id_var, ROK_TEST, ROK_TEST, poziom_jednostki=2)
                if df.empty:
                    status = "BRAK DANYCH"
                else:
                    val = df["wartosc"].dropna().iloc[0] if not df["wartosc"].dropna().empty else None
                    ostatnia_wartosc = f"{val:.2f}" if isinstance(val, float) else str(val)
                    status = "OK (tylko woj.)"
            else:
                val = df["wartosc"].dropna().iloc[0] if not df["wartosc"].dropna().empty else None
                ostatnia_wartosc = f"{val:.2f}" if isinstance(val, float) else str(val)
                status = "OK"
        except GusApiError as e:
            status = f"BŁĄD API: {e}"

        print(status)
        wyniki.append({
            "zmienna":          nazwa_kod,
            "id":               id_var,
            "opis_projekt":     opis_projekt,
            "nazwa_api":        nazwa_api,
            "temat_api":        temat_api,
            "ostatnia_wartosc": ostatnia_wartosc,
            "status":           status,
            "uzywana":          uzywana,
        })

    # Tabela podsumowująca
    print()
    separator()
    print("  PODSUMOWANIE WERYFIKACJI")
    separator()

    kolumny = ["zmienna", "id", "temat_api", "ostatnia_wartosc", "status", "uzywana"]
    df_wyniki = pd.DataFrame(wyniki)

    # Szerokości kolumn
    sz = {
        "zmienna":           24,
        "id":                10,
        "temat_api":          8,
        "ostatnia_wartosc":  16,
        "status":            20,
        "uzywana":            8,
    }
    naglowki_tab = {
        "zmienna":           "Zmienna (kod)",
        "id":                "ID",
        "temat_api":         "Temat",
        "ostatnia_wartosc":  f"Wartość ({ROK_TEST})",
        "status":            "Status",
        "uzywana":           "Używana",
    }

    linia_nagl = "  " + " | ".join(naglowki_tab[k].ljust(sz[k]) for k in kolumny)
    print(linia_nagl)
    separator("-", 80)

    for row in wyniki:
        uzywana_str = "TAK" if row["uzywana"] else "nie"
        wartosci = {
            "zmienna":          row["zmienna"],
            "id":               row["id"],
            "temat_api":        row["temat_api"],
            "ostatnia_wartosc": row["ostatnia_wartosc"],
            "status":           row["status"],
            "uzywana":          uzywana_str,
        }
        linia = "  " + " | ".join(str(wartosci[k]).ljust(sz[k]) for k in kolumny)
        print(linia)

    print()

    # Podsumowanie problemów
    problemy = [r for r in wyniki if "BŁĄD" in r["status"] or "BRAK" in r["status"]]
    nieuzywane = [r for r in wyniki if not r["uzywana"]]

    if not problemy:
        print("  ✓ Wszystkie weryfikowane zmienne zwróciły dane.")
    else:
        print(f"  ✗ Problemy ({len(problemy)}):")
        for p in problemy:
            print(f"    - {p['zmienna']} (id={p['id']}): {p['status']}")

    if nieuzywane:
        print(f"\n  ! Zmienne zdefiniowane w api.py, ale NIEUŻYWANE w żadnej funkcji ({len(nieuzywane)}):")
        for n in nieuzywane:
            print(f"    - {n['zmienna']} (id={n['id']}, temat={n['temat_api']})")

    # Porównanie nazw – wykrycie rozbieżności
    print()
    separator("-", 80)
    print("  PORÓWNANIE NAZW (projekt vs API)")
    separator("-", 80)
    print(f"  {'Zmienna':<24} | {'Opis w projekcie':<36} | Nazwa z API")
    separator("-", 80)
    for row in wyniki:
        print(f"  {row['zmienna']:<24} | {row['opis_projekt']:<36} | {row['nazwa_api']}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 80)
    print("  DIAGNOSTYKA BDL GUS – Weryfikacja zmiennych projektu")
    print("  API: https://bdl.stat.gov.pl/api/v1")
    print("=" * 80)

    sekcja_hierarchia_tematow()
    sekcja_zmienne_wg_tematow()
    sekcja_weryfikacja_id()

    print("\nDiagnostyka zakończona.\n")


if __name__ == "__main__":
    main()
