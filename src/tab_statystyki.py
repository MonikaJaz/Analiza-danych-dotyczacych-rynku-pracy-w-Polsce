"""Zakładka Statystyki – tabela statystyk opisowych dla wybranych wskaźników i miar."""

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
)

NAZWY_WOJEW = ["Wszystkie"] + sorted(WOJEWODZTWA.values())

WSKAZNIKI = [
    "Bezrobotni ogółem [tys.]",
    "Bezrobotne kobiety [tys.]",
    "Bezrobotni mężczyźni [tys.]",
    "Różnica K–M [tys.]",
    "Stopa bezrobocia [%]",
    "Wynagrodzenie brutto [PLN]",
    "Oferty pracy [szt.]",
]

MIARY = [
    ("Średnia",           "mean"),
    ("Mediana",           "median"),
    ("Q1 (25%)",          "q1"),
    ("Q3 (75%)",          "q3"),
    ("Min",               "min"),
    ("Max",               "max"),
    ("Odch. std.",        "std"),
    ("Wariancja",         "var"),
    ("Zakres (Max–Min)",  "zakres"),
    ("Liczba obserwacji", "count"),
]


def uruchom(app) -> None:
    rok_od = app.rok_od_var.get()
    rok_do = app.rok_do_var.get()
    wojew_nazwa = app._stat_wojew_var.get()
    wojew = None if wojew_nazwa == "Wszystkie" else wojew_nazwa

    app.status_var.set(f"Statystyki {rok_od}–{rok_do}…")
    app.update_idletasks()
    wyczysc(app.tab_statystyki)
    app._stat_dane = {}
    _zbuduj_ui(app)

    def zadanie() -> None:
        try:
            df_plec   = pobierz_trend_bezrobocia_plec(rok_od, rok_do, wojew)
            df_stopa  = pobierz_trend_stopy_bezrobocia(rok_od, rok_do, wojew)
            df_wyn    = pobierz_trend_wynagrodzen(rok_od, rok_do, wojew)
            df_oferty = pobierz_trend_ofert_pracy(rok_od, rok_do, wojew)
            app._stat_dane = {
                "df_plec": df_plec, "df_stopa": df_stopa,
                "df_wyn": df_wyn, "df_oferty": df_oferty,
            }
            app.after(0, lambda: odswiez_widok(app))
            app.after(0, lambda: app.status_var.set("Gotowe."))
        except GusApiError as e:
            app.after(0, lambda: messagebox.showerror("Błąd API", str(e)))

    threading.Thread(target=zadanie, daemon=True).start()


def _zbuduj_ui(app) -> None:
    outer = tk.Frame(app.tab_statystyki, bg=KOLORY["obszar"])
    outer.pack(fill="both", expand=True, padx=8, pady=8)
    outer.grid_columnconfigure(0, weight=1)
    outer.grid_rowconfigure(1, weight=1)

    tk.Label(outer, text="Statystyki opisowe",
             bg=KOLORY["obszar"], fg=KOLORY["tekst"],
             font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w", pady=(4, 8))

    table_frame = tk.Frame(outer, bg=KOLORY["panel"])
    table_frame.grid(row=1, column=0, sticky="nsew")
    table_frame.grid_columnconfigure(0, weight=1)
    table_frame.grid_rowconfigure(0, weight=1)

    app._stat_tabela_frame = table_frame

    app._stat_tree_frame = tk.Frame(table_frame, bg=KOLORY["panel"])
    app._stat_tree_frame.pack(fill="both", expand=True, padx=6, pady=6)
    app._stat_tree_frame.grid_columnconfigure(0, weight=1)
    app._stat_tree_frame.grid_rowconfigure(0, weight=1)


def odswiez_widok(app) -> None:
    if not app._stat_dane:
        return

    df_plec   = app._stat_dane["df_plec"]
    df_stopa  = app._stat_dane["df_stopa"]
    df_wyn    = app._stat_dane["df_wyn"]
    df_oferty = app._stat_dane["df_oferty"]

    wszystkie: dict[str, pd.Series] = {}
    if "Ogółem" in df_plec.columns:
        wszystkie["Bezrobotni ogółem [tys.]"] = df_plec["Ogółem"] / 1000
    if "Kobiety" in df_plec.columns:
        wszystkie["Bezrobotne kobiety [tys.]"] = df_plec["Kobiety"] / 1000
    if "Mężczyźni" in df_plec.columns:
        wszystkie["Bezrobotni mężczyźni [tys.]"] = df_plec["Mężczyźni"] / 1000
    if "Różnica (K–M)" in df_plec.columns:
        wszystkie["Różnica K–M [tys.]"] = df_plec["Różnica (K–M)"] / 1000
    if not df_stopa.empty:
        wszystkie["Stopa bezrobocia [%]"] = df_stopa["wartosc"]
    if not df_wyn.empty:
        wszystkie["Wynagrodzenie brutto [PLN]"] = df_wyn["wartosc"]
    if not df_oferty.empty:
        wszystkie["Oferty pracy [szt.]"] = df_oferty["wartosc"]

    aktywne = {
        n: s for n, s in wszystkie.items()
        if app._stat_wskaznik_vars.get(n, tk.BooleanVar(value=False)).get()
    }
    aktywne_miary = [
        (nazwa, klucz) for nazwa, klucz in MIARY
        if app._stat_miara_vars.get(klucz, tk.BooleanVar(value=False)).get()
    ]

    for w in app._stat_tree_frame.winfo_children():
        w.destroy()

    if aktywne and aktywne_miary:
        kol_ids  = ["wskaznik"] + [k for _, k in aktywne_miary]
        kol_nagl = {"wskaznik": "Wskaźnik"}
        kol_nagl.update({k: n for n, k in aktywne_miary})

        tree = ttk.Treeview(app._stat_tree_frame, show="headings", columns=kol_ids)
        for cid in kol_ids:
            tree.heading(cid, text=kol_nagl[cid])
            tree.column(cid, width=88, anchor="center")
        tree.column("wskaznik", width=195, anchor="w")

        def _obl(s: pd.Series, k: str) -> str:
            sc = pd.to_numeric(s, errors="coerce").dropna()
            if sc.empty:
                return "—"
            return {
                "mean":   f"{sc.mean():.2f}",
                "median": f"{sc.median():.2f}",
                "q1":     f"{sc.quantile(0.25):.2f}",
                "q3":     f"{sc.quantile(0.75):.2f}",
                "min":    f"{sc.min():.2f}",
                "max":    f"{sc.max():.2f}",
                "std":    f"{sc.std():.2f}",
                "var":    f"{sc.var():.2f}",
                "zakres": f"{sc.max() - sc.min():.2f}",
                "count":  str(int(sc.count())),
            }.get(k, "—")

        for nazwa, seria in aktywne.items():
            wiersz = [nazwa] + [_obl(seria, k) for _, k in aktywne_miary]
            tree.insert("", "end", values=wiersz)

        sb_y = ttk.Scrollbar(app._stat_tree_frame, orient="vertical", command=tree.yview)
        sb_x = ttk.Scrollbar(app._stat_tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_x.grid(row=1, column=0, sticky="ew")
        sb_y.grid(row=0, column=1, sticky="ns")
        tree.grid(row=0, column=0, sticky="nsew")
    else:
        tk.Label(app._stat_tree_frame,
                 text="Wybierz wskaźniki i miary w panelu bocznym.",
                 bg=KOLORY["panel"], fg=KOLORY["tekst2"],
                 font=("Segoe UI", 10)).grid(row=0, column=0, padx=20, pady=40)
