import threading
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd

from .config import KOLORY
from .utils import wyczysc
from .api import (
    GusApiError,
    WOJEWODZTWA,
    pobierz_trend_bezrobocia_plec,
    pobierz_trend_stopy_bezrobocia,
    pobierz_trend_wynagrodzen,
    pobierz_trend_ofert_pracy,
    pobierz_mape_stopy_bezrobocia,
    pobierz_mape_wynagrodzen,
    pobierz_napiecie_rynku,
    pobierz_strukture_wyksztalcenia,
    pobierz_strukture_wieku,
    pobierz_strukture_stazu,
    pobierz_strukture_plci,
)

NAZWY_WOJEW = ["Wszystkie"] + sorted(WOJEWODZTWA.values())

ZRODLA = [
    ("Bezrobotni wg płci (ogółem, K, M)",  "plec",          True),
    ("Stopa bezrobocia [%]",               "stopa",         True),
    ("Wynagrodzenie brutto [PLN]",         "wynagrodzenie", True),
    ("Oferty pracy [szt.]",                "oferty",        True),
    ("Mapa – stopa bezrobocia (woj.)",     "mapa_stopa",    False),
    ("Mapa – wynagrodzenia (woj.)",        "mapa_wyn",      False),
    ("Napięcie rynku pracy (woj.)",        "mapa_napiecie", False),
    ("Struktura – wykształcenie",          "str_wyk",       False),
    ("Struktura – wiek",                   "str_wiek",      False),
    ("Struktura – staż pracy",             "str_staz",      False),
    ("Struktura – płeć",                   "str_plec",      False),
]


def uruchom(app) -> None:
    app.status_var.set("Przygotowywanie widoku…")
    app.update_idletasks()
    wyczysc(app.tab_dane)
    app._dane_cache = {}
    _zbuduj_ui(app)
    pobierz(app)


def _zbuduj_ui(app) -> None:
    outer = tk.Frame(app.tab_dane, bg=KOLORY["obszar"])
    outer.pack(fill="both", expand=True, padx=8, pady=8)
    outer.grid_columnconfigure(0, weight=1)
    outer.grid_rowconfigure(1, weight=1)

    app._dane_info_lbl = tk.Label(
        outer,
        text="Pobieranie danych…",
        bg=KOLORY["obszar"], fg=KOLORY["tekst2"], font=("Segoe UI", 10))
    app._dane_info_lbl.grid(row=0, column=0, pady=16)

    app._dane_nb = ttk.Notebook(outer)
    app._dane_nb.grid(row=1, column=0, sticky="nsew")
    app._dane_tabs: dict[str, tk.Frame] = {}


def pobierz(app) -> None:
    rok_od = app.rok_od_var.get()
    rok_do = app.rok_do_var.get()
    rok_str = app.rok_str_var.get()
    wojew_nazwa = app.wojew_var.get()
    wojew = None if wojew_nazwa == "Wszystkie" else wojew_nazwa

    zaznaczone = [k for k, v in app._dane_zrodlo_vars.items() if v.get()]
    if not zaznaczone:
        messagebox.showinfo("Filtry", "Zaznacz przynajmniej jedno źródło danych.")
        return

    app.status_var.set("Pobieranie danych…")
    app.update_idletasks()

    def zadanie() -> None:
        nowe: dict[str, pd.DataFrame] = {}
        try:
            if "plec" in zaznaczone:
                nowe["plec"] = pobierz_trend_bezrobocia_plec(rok_od, rok_do)

            if "stopa" in zaznaczone:
                df = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)
                nowe["stopa"] = df.rename(columns={
                    "wartosc": "Stopa bezrobocia [%]",
                    "jednostka": "Jednostka",
                    "id_jednostki": "ID jednostki",
                })

            if "wynagrodzenie" in zaznaczone:
                df = pobierz_trend_wynagrodzen(rok_od, rok_do)
                nowe["wynagrodzenie"] = df.rename(columns={
                    "wartosc": "Wynagrodzenie brutto [PLN]",
                    "jednostka": "Jednostka",
                    "id_jednostki": "ID jednostki",
                })

            if "oferty" in zaznaczone:
                df = pobierz_trend_ofert_pracy(rok_od, rok_do)
                nowe["oferty"] = df.rename(columns={
                    "wartosc": "Oferty pracy [szt.]",
                    "jednostka": "Jednostka",
                    "id_jednostki": "ID jednostki",
                })

            if "mapa_stopa" in zaznaczone:
                df = pobierz_mape_stopy_bezrobocia(rok_str)
                nowe["mapa_stopa"] = df.rename(columns={
                    "wartosc": "Stopa bezrobocia [%]",
                    "jednostka": "Województwo",
                    "id_jednostki": "ID jednostki",
                })

            if "mapa_wyn" in zaznaczone:
                df = pobierz_mape_wynagrodzen(rok_str)
                nowe["mapa_wyn"] = df.rename(columns={
                    "wartosc": "Wynagrodzenie brutto [PLN]",
                    "jednostka": "Województwo",
                    "id_jednostki": "ID jednostki",
                })

            if "mapa_napiecie" in zaznaczone:
                df = pobierz_napiecie_rynku(rok_str)
                nowe["mapa_napiecie"] = df.rename(columns={
                    "wartosc": "Bezrobotni/ofertę [os.]",
                    "jednostka": "Województwo",
                    "id_jednostki": "ID jednostki",
                })

            if "str_wyk" in zaznaczone:
                df = pobierz_strukture_wyksztalcenia(rok_str, wojew)
                df.insert(0, "rok", rok_str)
                df.insert(1, "województwo", wojew_nazwa)
                nowe["str_wyk"] = df

            if "str_wiek" in zaznaczone:
                df = pobierz_strukture_wieku(rok_str, wojew)
                df.insert(0, "rok", rok_str)
                df.insert(1, "województwo", wojew_nazwa)
                nowe["str_wiek"] = df

            if "str_staz" in zaznaczone:
                df = pobierz_strukture_stazu(rok_str, wojew)
                df.insert(0, "rok", rok_str)
                df.insert(1, "województwo", wojew_nazwa)
                nowe["str_staz"] = df

            if "str_plec" in zaznaczone:
                df = pobierz_strukture_plci(rok_str, wojew)
                df.insert(0, "rok", rok_str)
                df.insert(1, "województwo", wojew_nazwa)
                nowe["str_plec"] = df

            app._dane_cache.update(nowe)
            lacznie = sum(len(v) for v in nowe.values())
            app.after(0, lambda: odswiez_widok(app))
            app.after(0, lambda: app.status_var.set(
                f"Załadowano {lacznie} wierszy ({len(nowe)} zbiorów)."))

        except GusApiError as e:
            app.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
            app.after(0, lambda: app.status_var.set(f"Błąd: {e}"))

    threading.Thread(target=zadanie, daemon=True).start()


def odswiez_widok(app) -> None:
    if not hasattr(app, "_dane_cache") or not app._dane_cache:
        return

    if hasattr(app, "_dane_info_lbl"):
        app._dane_info_lbl.grid_remove()

    for tab_id in app._dane_nb.tabs():
        app._dane_nb.forget(tab_id)
    app._dane_tabs.clear()

    etykiety_klucze = {k: e for e, k, _ in ZRODLA}

    for klucz, df in app._dane_cache.items():
        if not app._dane_zrodlo_vars.get(klucz, tk.BooleanVar(value=True)).get():
            continue
        etykieta = etykiety_klucze.get(klucz, klucz)
        skrot = etykieta[:28] + "…" if len(etykieta) > 28 else etykieta
        ramka = tk.Frame(app._dane_nb, bg=KOLORY["obszar"])
        ramka.grid_columnconfigure(0, weight=1)
        ramka.grid_rowconfigure(0, weight=1)
        app._dane_nb.add(ramka, text=skrot)
        _pokaz_df(df, ramka)


def _pokaz_df(df: pd.DataFrame, ramka: tk.Frame) -> None:
    kolumny = list(df.columns)
    tree = ttk.Treeview(ramka, show="headings", columns=kolumny)
    for kol in kolumny:
        tree.heading(kol, text=kol)
        szerokosc = max(100, min(200, len(str(kol)) * 11))
        tree.column(kol, width=szerokosc, anchor="center")
    for _, row in df.iterrows():
        wartosci = []
        for k in kolumny:
            v = row[k]
            wartosci.append("" if isinstance(v, float) and pd.isna(v) else
                            f"{v:.2f}" if isinstance(v, float) else str(v))
        tree.insert("", "end", values=wartosci)

    sb_y = ttk.Scrollbar(ramka, orient="vertical", command=tree.yview)
    sb_x = ttk.Scrollbar(ramka, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
    sb_x.grid(row=1, column=0, sticky="ew")
    sb_y.grid(row=0, column=1, sticky="ns")
    tree.grid(row=0, column=0, sticky="nsew")
