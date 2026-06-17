"""Dashboard – Analiza rynku pracy w Polsce (GUS BDL)."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")

from .api import GusApiError, WOJEWODZTWA, pobierz_kpi
from .config import KOLORY, LATA_DOST
from .utils import styl_matplotlib, formatuj_liczbe
from .tab_statystyki import WSKAZNIKI, MIARY
from .tab_dane import ZRODLA
from . import tab_trendy, tab_mapa, tab_struktura, tab_statystyki, tab_dane

NAZWY_WOJEW = ["Wszystkie"] + sorted(WOJEWODZTWA.values())


def _scroll_container(rodzic: tk.Frame, wiersz: int) -> tuple[tk.Frame, tk.Frame]:
    """Tworzy scrollowany kontener w sidebarze; zwraca (outer, inner)."""
    outer = tk.Frame(rodzic, bg=KOLORY["panel"])
    outer.grid(row=wiersz, column=0, sticky="nsew", padx=8, pady=(2, 4))
    outer.grid_columnconfigure(0, weight=1)
    outer.grid_rowconfigure(0, weight=1)

    canvas = tk.Canvas(outer, bg=KOLORY["panel"], highlightthickness=0)
    sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.grid(row=0, column=1, sticky="ns")
    canvas.grid(row=0, column=0, sticky="nsew")

    inner = tk.Frame(canvas, bg=KOLORY["panel"])
    win = canvas.create_window((0, 0), window=inner, anchor="nw")

    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

    def _wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<MouseWheel>", _wheel)
    inner.bind("<MouseWheel>", _wheel)

    return outer, inner


class AplikacjaRynkuPracy(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("Analiza rynku pracy w Polsce – GUS BDL")
        self.geometry("1400x820")
        self.minsize(1100, 700)
        self.configure(bg=KOLORY["tlo"])

        styl_matplotlib()

        self.rok_od_var     = tk.IntVar(value=2010)
        self.rok_do_var     = tk.IntVar(value=2023)
        self.rok_mapy_var   = tk.IntVar(value=2022)
        self.rok_str_var    = tk.IntVar(value=2022)
        self.rok_kpi_var    = tk.IntVar(value=2022)
        self.wojew_var      = tk.StringVar(value="Wszystkie")
        self.plec_trend_var = tk.StringVar(value="Ogółem + płcie")
        self.typ_mapy_var   = tk.StringVar(value="Stopa bezrobocia")
        self.status_var     = tk.StringVar(value="Wybierz zakładkę i kliknij Pobierz dane.")

        # zmienne filtrów dla Statystyk
        self._stat_wojew_var     = tk.StringVar(value="Wszystkie")
        self._stat_wskaznik_vars: dict[str, tk.BooleanVar] = {}
        self._stat_miara_vars:    dict[str, tk.BooleanVar] = {}
        self._stat_dane:          dict = {}

        # zmienne filtrów dla Danych
        self._dane_zrodlo_vars: dict[str, tk.BooleanVar] = {}
        self._dane_cache:       dict = {}

        self._zbuduj_style()
        self._zbuduj_ui()
        self.protocol("WM_DELETE_WINDOW", self._zamknij)

    def _zbuduj_style(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook", background=KOLORY["tlo"], borderwidth=0)
        s.configure(
            "TNotebook.Tab",
            background=KOLORY["panel"],
            foreground=KOLORY["tekst"],
            borderwidth=0, padding=(18, 8),
            font=("Segoe UI", 10),
        )
        s.map("TNotebook.Tab",
              background=[("selected", KOLORY["naglowek"])],
              foreground=[("selected", KOLORY["bialy"])])
        s.configure(
            "Treeview",
            background=KOLORY["panel2"], fieldbackground=KOLORY["panel2"],
            foreground=KOLORY["tekst"], borderwidth=0, rowheight=28,
            font=("Segoe UI", 9),
        )
        s.configure(
            "Treeview.Heading",
            background=KOLORY["panel"], foreground=KOLORY["tekst"],
            borderwidth=0, font=("Segoe UI Semibold", 9),
        )
        s.map("Treeview",
              background=[("selected", KOLORY["panel_ciemny"])],
              foreground=[("selected", KOLORY["bialy"])])

    def _zbuduj_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._zbuduj_naglowek()
        self._zbuduj_kpi_bar()
        cialo = tk.Frame(self, bg=KOLORY["tlo"])
        cialo.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        cialo.grid_columnconfigure(1, weight=1)
        cialo.grid_rowconfigure(0, weight=1)
        self._zbuduj_sidebar(cialo)
        self._zbuduj_notebook(cialo)
        self._zbuduj_pasek_statusu()

    def _zbuduj_naglowek(self) -> None:
        bar = tk.Frame(self, bg=KOLORY["naglowek"], height=70)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        tk.Label(bar, text="  📊  ANALIZA RYNKU PRACY W POLSCE",
                 bg=KOLORY["naglowek"], fg=KOLORY["bialy"],
                 font=("Segoe UI Light", 22)).grid(row=0, column=0, sticky="w", padx=24, pady=18)
        tk.Label(bar, text="Źródło: Bank Danych Lokalnych GUS (bdl.stat.gov.pl)",
                 bg=KOLORY["naglowek"], fg=KOLORY["bialy"],
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="e", padx=24)

    def _zbuduj_kpi_bar(self) -> None:
        self.kpi_frame = tk.Frame(self, bg=KOLORY["kpi_tlo"], height=72)
        self.kpi_frame.grid(row=1, column=0, sticky="ew")
        self.kpi_frame.grid_propagate(False)

        self.kpi_labels: dict[str, tk.Label] = {}
        kpi_defs = [
            ("stopa_bezrobocia", "Stopa bezrobocia",  "%"),
            ("wynagrodzenie",    "Śr. wynagrodzenie", " PLN"),
            ("bezrobotni",       "Bezrobotni",         " os."),
            ("oferty",           "Oferty pracy",       " szt."),
        ]
        akcenty = [KOLORY["panel_ciemny"], KOLORY["akcent2"], KOLORY["akcent3"], KOLORY["akcent4"]]
        for i, (klucz, nazwa, jednostka) in enumerate(kpi_defs):
            karta = tk.Frame(self.kpi_frame, bg=akcenty[i])
            karta.grid(row=0, column=i, padx=(16 if i == 0 else 8, 0), pady=12, sticky="ns")
            tk.Frame(karta, bg=akcenty[i], height=4).pack(fill="x")
            ramka = tk.Frame(karta, bg=KOLORY["panel"], padx=20, pady=8)
            ramka.pack(fill="both", expand=True)
            tk.Label(ramka, text=nazwa, bg=KOLORY["panel"], fg=KOLORY["tekst2"],
                     font=("Segoe UI", 8)).pack(anchor="w")
            lbl = tk.Label(ramka, text="—", bg=KOLORY["panel"], fg=akcenty[i],
                           font=("Segoe UI Semibold", 18))
            lbl.pack(anchor="w")
            self.kpi_labels[klucz] = lbl
            self.kpi_labels[klucz + "_jednostka"] = jednostka  # type: ignore[assignment]

        tk.Button(
            self.kpi_frame, text="⟳  Odśwież KPI",
            command=self._odswiez_kpi,
            bg=KOLORY["panel_ciemny"], fg=KOLORY["bialy"],
            activebackground=KOLORY["naglowek"], activeforeground=KOLORY["bialy"],
            relief="flat", font=("Segoe UI", 9), padx=12, pady=6, cursor="hand2",
        ).grid(row=0, column=len(kpi_defs), padx=16, pady=20, sticky="ns")

        tk.Label(self.kpi_frame, text="Rok KPI:",
                 bg=KOLORY["kpi_tlo"], fg=KOLORY["tekst2"],
                 font=("Segoe UI", 9)).grid(row=0, column=len(kpi_defs) + 1, padx=(16, 4), pady=20)

        ttk.Combobox(self.kpi_frame, textvariable=self.rok_kpi_var,
                     values=list(range(2005, 2025)), width=6, state="readonly").grid(
            row=0, column=len(kpi_defs) + 2, padx=4, pady=20)

    def _odswiez_kpi(self) -> None:
        rok = self.rok_kpi_var.get()
        self.status_var.set(f"Aktualizacja KPI ({rok})…")
        self.update_idletasks()

        def zadanie() -> None:
            try:
                kpi = pobierz_kpi(rok)
                self.after(0, lambda: self._pokaz_kpi(kpi))
            except GusApiError as e:
                self.after(0, lambda: self.status_var.set(f"Błąd KPI: {e}"))

        threading.Thread(target=zadanie, daemon=True).start()

    def _pokaz_kpi(self, kpi: dict) -> None:
        for klucz, lbl in self.kpi_labels.items():
            if not isinstance(lbl, tk.Label):
                continue
            wartosc = kpi.get(klucz, "brak")
            if isinstance(wartosc, (int, float)):
                jednostka = self.kpi_labels.get(klucz + "_jednostka", "")
                lbl.config(text=f"{formatuj_liczbe(float(wartosc))}{jednostka}")
            else:
                lbl.config(text=str(wartosc))
        self.status_var.set("KPI zaktualizowane.")
        self.kpi_frame.update_idletasks()

    def _zbuduj_sidebar(self, rodzic: tk.Widget) -> None:
        sb = tk.Frame(rodzic, bg=KOLORY["panel"], width=260)
        self.sidebar = sb
        self.filtry_trendow_widgets:    list[tk.Widget] = []
        self.filtry_mapy_widgets:       list[tk.Widget] = []
        self.filtry_struktury_widgets:  list[tk.Widget] = []
        self.filtry_statystyki_widgets: list[tk.Widget] = []
        self.filtry_dane_widgets:       list[tk.Widget] = []
        sb.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        wiersz = 0

        def sekcja(tekst: str) -> None:
            nonlocal wiersz
            blok = tk.Frame(sb, bg=KOLORY["panel_ciemny"])
            blok.grid(row=wiersz, column=0, sticky="ew", padx=0, pady=(12, 0))
            tk.Label(blok, text=tekst, bg=KOLORY["panel_ciemny"], fg=KOLORY["bialy"],
                     font=("Segoe UI Semibold", 8), anchor="w",
                     padx=16, pady=5).pack(fill="x")
            wiersz += 1

        def lbl(tekst: str) -> None:
            nonlocal wiersz
            tk.Label(sb, text=tekst, bg=KOLORY["panel"], fg=KOLORY["tekst2"],
                     font=("Segoe UI", 8), anchor="w").grid(
                row=wiersz, column=0, sticky="ew", padx=16, pady=(8, 1))
            wiersz += 1

        def combo(zmienna, wartosci, szerok: int = 14) -> None:
            nonlocal wiersz
            ttk.Combobox(sb, textvariable=zmienna, values=wartosci,
                         width=szerok, state="readonly").grid(
                row=wiersz, column=0, sticky="ew", padx=16, pady=(0, 2))
            wiersz += 1

        # Trendy (rows 0–6)
        sekcja("TRENDY")
        lbl("Rok od");   combo(self.rok_od_var, LATA_DOST)
        lbl("Rok do");   combo(self.rok_do_var, LATA_DOST)
        lbl("Widok płci")
        combo(self.plec_trend_var, ["Ogółem + płcie", "Tylko kobiety", "Tylko mężczyźni", "Ogółem"])

        # Mapy (rows 7–11)
        sekcja("MAPY")
        lbl("Rok mapy");    combo(self.rok_mapy_var, list(range(2005, 2025)))
        lbl("Rodzaj mapy"); combo(self.typ_mapy_var, ["Stopa bezrobocia", "Wynagrodzenie", "Napięcie rynku"])

        # Struktura (rows 12–16)
        sekcja("STRUKTURA")
        lbl("Rok struktury"); combo(self.rok_str_var, list(range(2005, 2025)))
        lbl("Województwo");   combo(self.wojew_var, NAZWY_WOJEW, szerok=18)

        # Statystyki (rows 17–23)
        sekcja("STATYSTYKI")
        lbl("Rok od");        combo(self.rok_od_var, LATA_DOST)
        lbl("Rok do");        combo(self.rok_do_var, LATA_DOST)
        lbl("Województwo");   combo(self._stat_wojew_var, NAZWY_WOJEW, szerok=18)

        # Dane (rows 24–32)
        sekcja("DANE")
        lbl("Rok od");                combo(self.rok_od_var, LATA_DOST)
        lbl("Rok do");                combo(self.rok_do_var, LATA_DOST)
        lbl("Rok (mapa / struktura)"); combo(self.rok_str_var, list(range(2005, 2025)))
        lbl("Województwo");           combo(self.wojew_var, NAZWY_WOJEW, szerok=18)

        # przypisz widgety do grup po numere wiersza
        for widget in sb.grid_slaves():
            row = int(widget.grid_info()["row"])
            if   0 <= row <=  6: self.filtry_trendow_widgets.append(widget)
            elif 7 <= row <= 11: self.filtry_mapy_widgets.append(widget)
            elif 12 <= row <= 16: self.filtry_struktury_widgets.append(widget)
            elif 17 <= row <= 23: self.filtry_statystyki_widgets.append(widget)
            elif 24 <= row <= 32: self.filtry_dane_widgets.append(widget)

        # rząd rozciągający — przewijane listy checkboxów
        expanding_row = wiersz
        sb.grid_rowconfigure(expanding_row, weight=1)

        # scrollowana lista filtrów Statystyki
        stat_outer, stat_inner = _scroll_container(sb, expanding_row)
        self.filtry_statystyki_widgets.append(stat_outer)

        tk.Label(stat_inner, text="Wskaźniki:", bg=KOLORY["panel"], fg=KOLORY["tekst"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=10, pady=(8, 2))
        for nazwa in WSKAZNIKI:
            var = tk.BooleanVar(value=True)
            self._stat_wskaznik_vars[nazwa] = var
            tk.Checkbutton(
                stat_inner, text=nazwa, variable=var,
                bg=KOLORY["panel"], fg=KOLORY["tekst"],
                activebackground=KOLORY["panel_jasny"],
                selectcolor=KOLORY["panel_jasny"],
                font=("Segoe UI", 8), anchor="w",
                command=lambda: tab_statystyki.odswiez_widok(self),
            ).pack(fill="x", padx=8, pady=1)

        tk.Frame(stat_inner, bg=KOLORY["linia"], height=1).pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(stat_inner, text="Miary statystyczne:", bg=KOLORY["panel"], fg=KOLORY["tekst"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=10, pady=(4, 2))
        for nazwa, klucz in MIARY:
            var = tk.BooleanVar(value=klucz in ("mean", "median", "min", "max", "std"))
            self._stat_miara_vars[klucz] = var
            tk.Checkbutton(
                stat_inner, text=nazwa, variable=var,
                bg=KOLORY["panel"], fg=KOLORY["tekst"],
                activebackground=KOLORY["panel_jasny"],
                selectcolor=KOLORY["panel_jasny"],
                font=("Segoe UI", 8), anchor="w",
                command=lambda: tab_statystyki.odswiez_widok(self),
            ).pack(fill="x", padx=8, pady=1)

        # scrollowana lista źródeł danych
        dane_outer, dane_inner = _scroll_container(sb, expanding_row)
        self.filtry_dane_widgets.append(dane_outer)

        tk.Label(dane_inner, text="Źródła danych:", bg=KOLORY["panel"], fg=KOLORY["tekst"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=10, pady=(8, 2))
        for etykieta, klucz, domyslnie in ZRODLA:
            var = tk.BooleanVar(value=domyslnie)
            self._dane_zrodlo_vars[klucz] = var
            tk.Checkbutton(
                dane_inner, text=etykieta, variable=var,
                bg=KOLORY["panel"], fg=KOLORY["tekst"],
                activebackground=KOLORY["panel_jasny"],
                selectcolor=KOLORY["panel_jasny"],
                font=("Segoe UI", 8), anchor="w", wraplength=185,
                command=lambda: tab_dane.odswiez_widok(self),
            ).pack(fill="x", padx=8, pady=2)

        wiersz += 1

        tk.Button(
            sb, text="▶  POBIERZ DANE",
            command=self._uruchom,
            bg=KOLORY["panel_ciemny"], fg=KOLORY["bialy"],
            activebackground=KOLORY["naglowek"], activeforeground=KOLORY["bialy"],
            relief="flat", font=("Segoe UI Semibold", 11),
            padx=16, pady=12, cursor="hand2",
        ).grid(row=wiersz, column=0, sticky="ew", padx=16, pady=20)

    def _zbuduj_notebook(self, rodzic: tk.Widget) -> None:
        self.nb = ttk.Notebook(rodzic)
        self.nb.grid(row=0, column=1, sticky="nsew")
        rodzic.grid_rowconfigure(0, weight=1)
        rodzic.grid_columnconfigure(1, weight=1)

        self.tab_trendy     = self._nowa_zakladka("📈  Trendy")
        self.tab_mapa       = self._nowa_zakladka("🗺  Mapa")
        self.tab_struktura  = self._nowa_zakladka("🥧  Struktura bezrobocia")
        self.tab_statystyki = self._nowa_zakladka("📐  Statystyki")
        self.tab_dane       = self._nowa_zakladka("📋  Dane")

        self.nb.bind("<<NotebookTabChanged>>", self._aktualizuj_filtry_sidebaru)
        self._aktualizuj_filtry_sidebaru()

    def _nowa_zakladka(self, nazwa: str) -> tk.Frame:
        ramka = tk.Frame(self.nb, bg=KOLORY["obszar"])
        self.nb.add(ramka, text=nazwa)
        ramka.grid_columnconfigure(0, weight=1)
        ramka.grid_rowconfigure(0, weight=1)
        return ramka

    def _zbuduj_pasek_statusu(self) -> None:
        tk.Label(
            self, textvariable=self.status_var,
            bg=KOLORY["naglowek"], fg=KOLORY["bialy"],
            font=("Segoe UI", 9), anchor="w",
        ).grid(row=3, column=0, sticky="ew", ipady=4)

    def _uruchom(self) -> None:
        aktywna = self.nb.index("current")
        [
            tab_trendy.uruchom,
            tab_mapa.uruchom,
            tab_struktura.uruchom,
            tab_statystyki.uruchom,
            tab_dane.uruchom,
        ][aktywna](self)

    def _aktualizuj_filtry_sidebaru(self, _event: tk.Event | None = None) -> None:
        aktywna = self.nb.index("current")
        for widget in self.filtry_trendow_widgets:
            widget.grid() if aktywna == 0 else widget.grid_remove()
        for widget in self.filtry_mapy_widgets:
            widget.grid() if aktywna == 1 else widget.grid_remove()
        for widget in self.filtry_struktury_widgets:
            widget.grid() if aktywna == 2 else widget.grid_remove()
        for widget in self.filtry_statystyki_widgets:
            widget.grid() if aktywna == 3 else widget.grid_remove()
        for widget in self.filtry_dane_widgets:
            widget.grid() if aktywna == 4 else widget.grid_remove()

    def _zamknij(self) -> None:
        self.quit()
        self.destroy()


def uruchom_gui() -> None:
    app = AplikacjaRynkuPracy()
    app.mainloop()
