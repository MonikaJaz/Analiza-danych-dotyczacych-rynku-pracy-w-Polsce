"""Estetyczny dashboard tkinter do analizy danych z API GUS BDL."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

import threading
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import pandas as pd

from .api import GusApiError, pobierz_tematy, pobierz_zmienne

from .api import (
    GusApiError, WOJEWODZTWA,
    pobierz_kpi, pobierz_mape_stopy_bezrobocia, pobierz_mape_wynagrodzen,
    pobierz_napiecie_rynku, pobierz_strukture_plci, pobierz_strukture_stazu,
    pobierz_strukture_wieku, pobierz_strukture_wyksztalcenia,
    pobierz_trend_bezrobocia_plec, pobierz_trend_ofert_pracy,
    pobierz_trend_stopy_bezrobocia, pobierz_trend_wynagrodzen, GusApiError, pobierz_tematy, pobierz_zmienne
)

class AplikacjaRynkuPracy(tk.Tk):
    """Glowne okno aplikacji dashboardowej."""

    KOLORY = {
        "tlo": "#eef8ed",
        "naglowek": "#6fbd62",
        "panel": "#8bd47d",
        "panel_ciemny": "#5ead51",
        "panel_jasny": "#b9ebb1",
        "obszar": "#d8f5d2",
        "obszar_2": "#c4edbc",
        "bialy": "#ffffff",
        "akcent": "#79c86d",
        "linia": "#aee4a5",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("Analiza rynku pracy w Polsce")
        self.geometry("1120x720")
        self.minsize(980, 620)
        self.configure(bg=self.KOLORY["tlo"])

        self.status_var = tk.StringVar(value="Gotowe do uruchomienia analizy.")
        self.id_nadrzedne_var = tk.StringVar(value="")
        self.id_tematu_var = tk.StringVar(value="P1364")
        self.kategoria_var = tk.StringVar(value="Wykres slupkowy")
        self.typ_wykresu_var = tk.StringVar(value="Wykres slupkowy")

        self._zbuduj_style()
        self._zbuduj_interfejs()

    def _zbuduj_style(self) -> None:
        styl = ttk.Style(self)
        styl.theme_use("clam")

        styl.configure(
            "Dashboard.TNotebook",
            background=self.KOLORY["tlo"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        styl.configure(
            "Dashboard.TNotebook.Tab",
            background=self.KOLORY["naglowek"],
            foreground=self.KOLORY["bialy"],
            borderwidth=0,
            padding=(18, 8),
            font=("Segoe UI", 10),
        )
        styl.map(
            "Dashboard.TNotebook.Tab",
            background=[("selected", self.KOLORY["panel_ciemny"])],
            foreground=[("selected", self.KOLORY["bialy"])],
        )
        styl.configure(
            "Dashboard.Treeview",
            background=self.KOLORY["obszar"],
            fieldbackground=self.KOLORY["obszar"],
            foreground=self.KOLORY["bialy"],
            borderwidth=0,
            rowheight=30,
            font=("Segoe UI", 10),
        )
        styl.configure(
            "Dashboard.Treeview.Heading",
            background=self.KOLORY["panel_ciemny"],
            foreground=self.KOLORY["bialy"],
            borderwidth=0,
            font=("Segoe UI Semibold", 10),
        )
        styl.map(
            "Dashboard.Treeview",
            background=[("selected", self.KOLORY["panel_ciemny"])],
            foreground=[("selected", self.KOLORY["bialy"])],
        )
        styl.configure(
            "Vertical.TScrollbar",
            background=self.KOLORY["panel"],
            troughcolor=self.KOLORY["obszar"],
            bordercolor=self.KOLORY["obszar"],
            arrowcolor=self.KOLORY["bialy"],
        )

    def _zbuduj_interfejs(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._zbuduj_naglowek()

        cialo = tk.Frame(self, bg=self.KOLORY["tlo"])
        cialo.grid(row=1, column=0, sticky="nsew", padx=18, pady=(16, 18))
        cialo.grid_columnconfigure(1, weight=1)
        cialo.grid_rowconfigure(0, weight=1)

        self._zbuduj_panel_boczny(cialo)
        self._zbuduj_panel_glowny(cialo)

    def _zbuduj_naglowek(self) -> None:
        naglowek = tk.Frame(self, bg=self.KOLORY["naglowek"], height=86)
        naglowek.grid(row=0, column=0, sticky="ew")
        naglowek.grid_propagate(False)
        naglowek.grid_columnconfigure(0, weight=1)

        tytul = tk.Label(
            naglowek,
            text="ANALIZA RYNKU PRACY",
            bg=self.KOLORY["naglowek"],
            fg=self.KOLORY["bialy"],
            font=("Segoe UI Light", 28),
        )
        tytul.grid(row=0, column=0, sticky="w", padx=(64, 0), pady=(18, 0))

        ikona = tk.Canvas(
            naglowek,
            width=86,
            height=58,
            bg=self.KOLORY["naglowek"],
            highlightthickness=0,
        )
        ikona.grid(row=0, column=1, padx=(18, 0), pady=15)
        for x, h in [(8, 25), (20, 36), (32, 29), (44, 46), (56, 55)]:
            ikona.create_rectangle(x, 56 - h, x + 6, 56, outline=self.KOLORY["bialy"], width=2)
        ikona.create_line(4, 56, 70, 56, fill=self.KOLORY["bialy"], width=2)

        zrodlo = tk.Label(
            naglowek,
            text="Zrodlo: Bank Danych Lokalnych BDL (GUS)",
            bg=self.KOLORY["naglowek"],
            fg=self.KOLORY["bialy"],
            font=("Segoe UI", 10),
        )
        zrodlo.grid(row=0, column=2, sticky="ne", padx=(18, 28), pady=14)

    def _zbuduj_panel_boczny(self, rodzic: tk.Widget) -> None:
        self.panel_boczny = tk.Frame(rodzic, bg=self.KOLORY["panel"], width=276)
        self.panel_boczny.grid(row=0, column=0, sticky="ns", padx=(0, 18))
        self.panel_boczny.grid_propagate(False)
        self.panel_boczny.grid_columnconfigure(0, weight=1)

        self._dodaj_tytul_sekcji(self.panel_boczny, "rodzaj analizy", 0)
        self._dodaj_menu(
            self.panel_boczny,
            self.kategoria_var,
            ("Wykres slupkowy", "Wykres liniowy", "Mapa", "Ranking"),
            1,
        )

        self._dodaj_tytul_sekcji(self.panel_boczny, "filtry danych", 2, pady=(30, 8))
        self.ramka_filtry_danych = tk.Frame(
            self.panel_boczny,
            bg=self.KOLORY["panel_jasny"],
            highlightthickness=1,
            highlightbackground=self.KOLORY["linia"],
        )
        self.ramka_filtry_danych.grid(row=3, column=0, sticky="ew", padx=22)
        self.ramka_filtry_danych.configure(height=170)
        self.ramka_filtry_danych.grid_propagate(False)

        self.ramka_dodatkowe = tk.Frame(self.panel_boczny, bg=self.KOLORY["panel"])
        self.ramka_dodatkowe.grid(row=4, column=0, sticky="ew", padx=22, pady=(26, 0))
        self.ramka_dodatkowe.grid_columnconfigure(0, weight=1)
        self._dodaj_tytul_sekcji(self.ramka_dodatkowe, "dodatkowe filtry", 0, pady=(0, 8))
        self.puste_dodatkowe = tk.Frame(
            self.ramka_dodatkowe,
            bg=self.KOLORY["panel_jasny"],
            highlightthickness=1,
            highlightbackground=self.KOLORY["linia"],
        )
        self.puste_dodatkowe.grid(row=1, column=0, sticky="ew")
        self.puste_dodatkowe.configure(height=120)
        self.puste_dodatkowe.grid_propagate(False)

        self.panel_boczny.grid_rowconfigure(5, weight=1)
        przycisk = tk.Button(
            self.panel_boczny,
            text="uruchom analize",
            command=self.uruchom_analize,
            bg=self.KOLORY["panel_ciemny"],
            fg=self.KOLORY["bialy"],
            activebackground=self.KOLORY["naglowek"],
            activeforeground=self.KOLORY["bialy"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 12),
            padx=16,
            pady=12,
        )
        przycisk.grid(row=6, column=0, sticky="ew", padx=22, pady=(18, 26))

    def _zbuduj_panel_glowny(self, rodzic: tk.Widget) -> None:
        panel = tk.Frame(rodzic, bg=self.KOLORY["akcent"])
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        self.notebook = ttk.Notebook(panel, style="Dashboard.TNotebook")
        self.notebook.grid(row=0, column=0, sticky="ew", padx=14, pady=(0, 0))
        self.notebook.bind("<<NotebookTabChanged>>", self._po_zmianie_zakladki)

        self.zakladki: dict[str, tk.Frame] = {}
        for nazwa in ("wizualizacja", "statystyki opisowe", "surowe dane", "o programie"):
            ramka = tk.Frame(self.notebook, bg=self.KOLORY["akcent"])
            self.notebook.add(ramka, text=nazwa)
            self.zakladki[nazwa] = ramka

        zawartosc = tk.Frame(panel, bg=self.KOLORY["obszar"])
        zawartosc.grid(row=1, column=0, sticky="nsew", padx=14, pady=(14, 18))
        zawartosc.grid_columnconfigure(0, weight=1)
        zawartosc.grid_rowconfigure(0, weight=1)

        self.obszar_wyniku = tk.Frame(zawartosc, bg=self.KOLORY["obszar"])
        self.obszar_wyniku.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.obszar_wyniku.grid_columnconfigure(0, weight=1)
        self.obszar_wyniku.grid_rowconfigure(0, weight=1)

        self.status = tk.Label(
            panel,
            textvariable=self.status_var,
            bg=self.KOLORY["akcent"],
            fg=self.KOLORY["bialy"],
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.status.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))

    def _dodaj_tytul_sekcji(
        self,
        rodzic: tk.Widget,
        tekst: str,
        wiersz: int,
        pady: tuple[int, int] = (18, 8),
    ) -> None:
        tk.Label(
            rodzic,
            text=tekst,
            bg=self.KOLORY["panel"],
            fg=self.KOLORY["bialy"],
            font=("Segoe UI Semibold", 11),
            anchor="w",
        ).grid(row=wiersz, column=0, sticky="ew", padx=22 if rodzic is self.panel_boczny else 0, pady=pady)

    def _dodaj_menu(
        self,
        rodzic: tk.Widget,
        zmienna: tk.StringVar,
        wartosci: tuple[str, ...],
        wiersz: int,
        komenda: Callable[[str], None] | None = None,
    ) -> tk.OptionMenu:
        menu = tk.OptionMenu(rodzic, zmienna, *wartosci, command=komenda)
        menu.configure(
            bg=self.KOLORY["panel_ciemny"],
            fg=self.KOLORY["bialy"],
            activebackground=self.KOLORY["naglowek"],
            activeforeground=self.KOLORY["bialy"],
            highlightthickness=0,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            padx=10,
            pady=6,
        )
        menu["menu"].configure(
            bg=self.KOLORY["panel_ciemny"],
            fg=self.KOLORY["bialy"],
            activebackground=self.KOLORY["naglowek"],
            activeforeground=self.KOLORY["bialy"],
            bd=0,
            font=("Segoe UI", 10),
        )
        menu.grid(row=wiersz, column=0, sticky="ew", padx=22 if rodzic is self.panel_boczny else 0)
        return menu

    def _dodaj_pole(self, rodzic: tk.Widget, etykieta: str, zmienna: tk.StringVar, wiersz: int) -> None:
        tk.Label(
            rodzic,
            text=etykieta,
            bg=self.KOLORY["panel"],
            fg=self.KOLORY["bialy"],
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=wiersz, column=0, sticky="ew", pady=(8, 4))
        tk.Entry(
            rodzic,
            textvariable=zmienna,
            bg=self.KOLORY["panel_ciemny"],
            fg=self.KOLORY["bialy"],
            insertbackground=self.KOLORY["bialy"],
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
        ).grid(row=wiersz + 1, column=0, sticky="ew", ipady=7)

    def _po_zmianie_zakladki(self, _event: tk.Event) -> None:
        self._wyczysc_obszar_wyniku()

    def uruchom_analize(self) -> None:
        self._wyczysc_obszar_wyniku()
        self.status_var.set(f"Wybrano: {self.kategoria_var.get()}. Miejsce na analize jest przygotowane.")

    def _bezpiecznie(self, opis: str, funkcja: Callable[[], pd.DataFrame]) -> None:
        try:
            self.status_var.set(f"Pobieram: {opis}...")
            self.update_idletasks()
            df = funkcja()
            self._pokaz_dataframe(df)
            self.status_var.set(f"Pobrano {len(df)} rekordow: {opis}.")
        except (GusApiError, ValueError) as exc:
            self.status_var.set("Blad pobierania danych.")
            messagebox.showerror("Blad", str(exc))

    def _wyczysc_obszar_wyniku(self) -> None:
        for widget in self.obszar_wyniku.winfo_children():
            widget.destroy()

    def _pokaz_dataframe(self, df: pd.DataFrame) -> None:
        self._wyczysc_obszar_wyniku()

        tabela_frame = tk.Frame(self.obszar_wyniku, bg=self.KOLORY["obszar"])
        tabela_frame.grid(row=0, column=0, sticky="nsew")
        tabela_frame.grid_columnconfigure(0, weight=1)
        tabela_frame.grid_rowconfigure(0, weight=1)

        tabela = ttk.Treeview(tabela_frame, show="headings", style="Dashboard.Treeview")
        tabela.grid(row=0, column=0, sticky="nsew")

        pasek_y = ttk.Scrollbar(tabela_frame, orient="vertical", command=tabela.yview)
        pasek_y.grid(row=0, column=1, sticky="ns")
        tabela.configure(yscrollcommand=pasek_y.set)

        kolumny = list(df.columns[:8])
        tabela["columns"] = kolumny

        for kolumna in kolumny:
            tabela.heading(kolumna, text=kolumna)
            tabela.column(kolumna, width=150, anchor="w")

        for _, rekord in df.head(200).iterrows():
            wartosci = [rekord.get(kolumna, "") for kolumna in kolumny]
            tabela.insert("", "end", values=wartosci)

    def pokaz_glowne_kategorie(self) -> None:
        self.id_nadrzedne_var.set("")
        self._bezpiecznie("glowne kategorie BDL", pobierz_tematy)

    def pokaz_podtematy(self) -> None:
        id_nadrzedne = self.id_nadrzedne_var.get().strip()
        if not id_nadrzedne:
            messagebox.showwarning("Brak ID", "Podaj ID z tabeli, np. K1 albo P1364.")
            return
        self._bezpiecznie(
            f"podtematy dla {id_nadrzedne}",
            lambda: pobierz_tematy(id_nadrzedne),
        )

    def pokaz_zmienne(self) -> None:
        id_tematu = self.id_tematu_var.get().strip()
        if not id_tematu:
            messagebox.showwarning("Brak ID", "Podaj ID tematu, np. P1364.")
            return
        self._bezpiecznie(f"zmienne dla tematu {id_tematu}", lambda: pobierz_zmienne(id_tematu))


def uruchom_gui() -> None:
    app = AplikacjaRynkuPracy()
    app.mainloop()
