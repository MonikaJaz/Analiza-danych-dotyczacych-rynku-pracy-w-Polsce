"""Dashboard tkinter – Analiza rynku pracy w Polsce (GUS BDL)."""
from __future__ import annotations

import json
from pathlib import Path
import threading
import tkinter as tk
import unicodedata
from tkinter import messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from .api import (
    GusApiError,
    WOJEWODZTWA,
    pobierz_kpi,
    pobierz_mape_stopy_bezrobocia,
    pobierz_mape_wynagrodzen,
    pobierz_napiecie_rynku,
    pobierz_strukture_plci,
    pobierz_strukture_stazu,
    pobierz_strukture_wieku,
    pobierz_strukture_wyksztalcenia,
    pobierz_trend_bezrobocia_plec,
    pobierz_trend_ofert_pracy,
    pobierz_trend_stopy_bezrobocia,
    pobierz_trend_wynagrodzen,
)

# ---------------------------------------------------------------------------
# Stałe globalne
# ---------------------------------------------------------------------------

KOLORY = {
    "tlo": "#eef8ed",
    "naglowek": "#6fbd62",
    "panel": "#8bd47d",
    "panel_ciemny": "#5ead51",
    "panel_jasny": "#b9ebb1",
    "obszar": "#d8f5d2",
    "bialy": "#ffffff",
    "akcent": "#79c86d",
    "linia": "#aee4a5",
    "akcent2": "#4ea8de",
    "akcent3": "#f4a261",
    "akcent4": "#e76f51",
    "akcent5": "#e9c46a",
    "panel2": "#d8f5d2",
    "tekst": "#1e3d17",
    "tekst2": "#4a703d",
    "kpi_tlo": "#c4edbc",
}

PALETA_WYKRESY = [
    KOLORY["akcent"], KOLORY["akcent2"], KOLORY["akcent3"],
    KOLORY["akcent4"], KOLORY["akcent5"],
    "#ff9f43", "#00d2d3", "#54a0ff", "#ff6b6b", "#1dd1a1",
]

LATA_DOST = list(range(2000, 2025))
NAZWY_WOJEW = ["Wszystkie"] + sorted(WOJEWODZTWA.values())
SCIEZKA_GEOJSON_WOJEWODZTWA = Path(__file__).resolve().parents[1] / "assets" / "wojewodztwa.geojson"

# ---------------------------------------------------------------------------
# Funkcje pomocnicze globalne
# ---------------------------------------------------------------------------

def _styl_matplotlib() -> None:
    plt.rcParams.update({
        "figure.facecolor": KOLORY["panel2"],
        "axes.facecolor": KOLORY["obszar"],
        "axes.edgecolor": KOLORY["linia"],
        "axes.labelcolor": KOLORY["tekst"],
        "xtick.color": KOLORY["tekst2"],
        "ytick.color": KOLORY["tekst2"],
        "text.color": KOLORY["tekst"],
        "grid.color": KOLORY["linia"],
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
        "legend.facecolor": KOLORY["panel"],
        "legend.edgecolor": KOLORY["linia"],
        "legend.labelcolor": KOLORY["tekst"],
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
    })


def _wyczysc(frame: tk.Frame) -> None:
    for w in frame.winfo_children():
        w.destroy()


def _osadz_figure(fig: plt.Figure, rodzic: tk.Widget) -> None:
    canvas = FigureCanvasTkAgg(fig, master=rodzic)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


def _normalizuj_nazwe(nazwa: str) -> str:
    bez_znakow = unicodedata.normalize("NFKD", nazwa)
    bez_znakow = "".join(znak for znak in bez_znakow if not unicodedata.combining(znak))
    return bez_znakow.upper().strip()


def _wczytaj_geojson_wojewodztw() -> dict:
    with open(SCIEZKA_GEOJSON_WOJEWODZTWA, encoding="utf-8") as plik:
        return json.load(plik)


def _pole_pierscienia(pierscien: list[list[float]]) -> float:
    pole = 0.0
    for i in range(len(pierscien) - 1):
        x1, y1 = pierscien[i]
        x2, y2 = pierscien[i + 1]
        pole += x1 * y2 - x2 * y1
    return abs(pole) / 2


def _srodek_pierscienia(pierscien: list[list[float]]) -> tuple[float, float]:
    xs = [punkt[0] for punkt in pierscien]
    ys = [punkt[1] for punkt in pierscien]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _formatuj_liczbe(v: float | str) -> str:
    if isinstance(v, str):
        return v
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} mln"
    if v >= 1_000:
        return f"{v / 1_000:.1f} tys."
    return f"{v:.1f}"


# ---------------------------------------------------------------------------
# Klasa główna
# ---------------------------------------------------------------------------

class AplikacjaRynkuPracy(tk.Tk):
    """Główne okno dashboardu."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Analiza rynku pracy w Polsce – GUS BDL")
        self.geometry("1400x820")
        self.minsize(1100, 700)
        self.configure(bg=KOLORY["tlo"])

        _styl_matplotlib()

        self.rok_od_var = tk.IntVar(value=2010)
        self.rok_do_var = tk.IntVar(value=2023)
        self.rok_mapy_var = tk.IntVar(value=2022)
        self.rok_str_var = tk.IntVar(value=2022)
        self.rok_kpi_var = tk.IntVar(value=2022)
        self.wojew_var = tk.StringVar(value="Wszystkie")
        self.plec_trend_var = tk.StringVar(value="Ogółem + płcie")
        self.typ_mapy_var = tk.StringVar(value="Stopa bezrobocia")
        self.status_var = tk.StringVar(value="Gotowe. Wybierz zakładkę i kliknij 'Pobierz dane'.")

        self._zbuduj_style()
        self._zbuduj_ui()
        self.protocol("WM_DELETE_WINDOW", self._zamknij)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _zbuduj_style(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook", background=KOLORY["tlo"], borderwidth=0)
        s.configure(
            "TNotebook.Tab",
            background=KOLORY["panel"],
            foreground=KOLORY["tekst"],
            borderwidth=0,
            padding=(20, 9),
            font=("Segoe UI", 10),
        )
        s.map(
            "TNotebook.Tab",
            background=[("selected", KOLORY["panel_ciemny"])],
            foreground=[("selected", KOLORY["bialy"])],
        )
        s.configure(
            "Treeview",
            background=KOLORY["panel2"],
            fieldbackground=KOLORY["panel2"],
            foreground=KOLORY["tekst"],
            borderwidth=0,
            rowheight=28,
            font=("Segoe UI", 9),
        )
        s.configure(
            "Treeview.Heading",
            background=KOLORY["panel"],
            foreground=KOLORY["tekst"],
            borderwidth=0,
            font=("Segoe UI Semibold", 9),
        )
        s.map("Treeview", background=[("selected", KOLORY["panel_ciemny"])],
              foreground=[("selected", KOLORY["bialy"])])

    # ------------------------------------------------------------------
    # Główny układ
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Nagłówek
    # ------------------------------------------------------------------

    def _zbuduj_naglowek(self) -> None:
        bar = tk.Frame(self, bg=KOLORY["naglowek"], height=70)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        tk.Label(
            bar, text="  📊  ANALIZA RYNKU PRACY W POLSCE",
            bg=KOLORY["naglowek"], fg=KOLORY["bialy"],
            font=("Segoe UI Light", 22),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=18)
        tk.Label(
            bar, text="Źródło: Bank Danych Lokalnych GUS (bdl.stat.gov.pl)",
            bg=KOLORY["naglowek"], fg=KOLORY["bialy"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=2, sticky="e", padx=24)

    # ------------------------------------------------------------------
    # Pasek KPI
    # ------------------------------------------------------------------

    def _zbuduj_kpi_bar(self) -> None:
        self.kpi_frame = tk.Frame(self, bg=KOLORY["kpi_tlo"], height=72)
        self.kpi_frame.grid(row=1, column=0, sticky="ew")
        self.kpi_frame.grid_propagate(False)

        self.kpi_labels: dict[str, tk.Label] = {}
        kpi_defs = [
            ("stopa_bezrobocia", "Stopa bezrobocia", "%"),
            ("wynagrodzenie", "Śr. wynagrodzenie", " PLN"),
            ("bezrobotni", "Bezrobotni", " os."),
            ("oferty", "Oferty pracy", " szt."),
        ]
        for i, (klucz, nazwa, jednostka) in enumerate(kpi_defs):
            ramka = tk.Frame(self.kpi_frame, bg=KOLORY["panel"], padx=22, pady=8)
            ramka.grid(row=0, column=i, padx=(16 if i == 0 else 8, 0), pady=12, sticky="ns")
            tk.Label(ramka, text=nazwa, bg=KOLORY["panel"], fg=KOLORY["tekst2"],
                     font=("Segoe UI", 8)).pack(anchor="w")
            lbl = tk.Label(ramka, text="—", bg=KOLORY["panel"], fg=KOLORY["panel_ciemny"],
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

        tk.Label(
            self.kpi_frame, text="Rok KPI:",
            bg=KOLORY["kpi_tlo"], fg=KOLORY["tekst2"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=len(kpi_defs) + 1, padx=(16, 4), pady=20)

        ttk.Combobox(
            self.kpi_frame, textvariable=self.rok_kpi_var,
            values=list(range(2005, 2025)), width=6, state="readonly",
        ).grid(row=0, column=len(kpi_defs) + 2, padx=4, pady=20)

    def _odswiez_kpi(self) -> None:
        rok = self.rok_kpi_var.get()
        self.status_var.set(f"Pobieram KPI dla {rok}…")
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
                tekst = _formatuj_liczbe(float(wartosc))
                jednostka = self.kpi_labels.get(klucz + "_jednostka", "")
                lbl.config(text=f"{tekst}{jednostka}")
            else:
                lbl.config(text=str(wartosc))
        self.status_var.set("KPI zaktualizowane.")

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _zbuduj_sidebar(self, rodzic: tk.Widget) -> None:
        sb = tk.Frame(rodzic, bg=KOLORY["panel"], width=240)
        self.sidebar = sb
        self.filtry_trendow_widgets: list[tk.Widget] = []
        self.filtry_mapy_widgets: list[tk.Widget] = []
        self.filtry_struktury_widgets: list[tk.Widget] = []
        sb.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        wiersz = 0

        def lbl(tekst: str, kolor_fg: str = KOLORY["tekst"]) -> None:
            nonlocal wiersz
            tk.Label(sb, text=tekst, bg=KOLORY["panel"], fg=kolor_fg,
                     font=("Segoe UI Semibold", 9), anchor="w").grid(
                row=wiersz, column=0, sticky="ew", padx=16, pady=(14, 4))
            wiersz += 1

        def combo(zmienna: tk.StringVar | tk.IntVar, wartosci: list, szerok: int = 14) -> None:
            nonlocal wiersz
            ttk.Combobox(sb, textvariable=zmienna, values=wartosci,
                         width=szerok, state="readonly").grid(
                row=wiersz, column=0, sticky="ew", padx=16, pady=(0, 2))
            wiersz += 1

        lbl("── TRENDY ──", KOLORY["panel_ciemny"])
        lbl("Rok od")
        combo(self.rok_od_var, LATA_DOST)
        lbl("Rok do")
        combo(self.rok_do_var, LATA_DOST)
        lbl("Widok płci")
        combo(self.plec_trend_var, ["Ogółem + płcie", "Tylko kobiety", "Tylko mężczyźni", "Ogółem"])

        lbl("── MAPY ──", KOLORY["panel_ciemny"])
        lbl("Rok mapy")
        combo(self.rok_mapy_var, list(range(2005, 2025)))
        lbl("Rodzaj mapy")
        combo(self.typ_mapy_var, ["Stopa bezrobocia", "Wynagrodzenie", "Napięcie rynku"])

        lbl("── STRUKTURA ──", KOLORY["panel_ciemny"])
        lbl("Rok struktury")
        combo(self.rok_str_var, list(range(2005, 2025)))
        lbl("Województwo")
        combo(self.wojew_var, NAZWY_WOJEW, szerok=18)

        for widget in sb.grid_slaves():
            row = int(widget.grid_info()["row"])
            if 0 <= row <= 6:
                self.filtry_trendow_widgets.append(widget)
            elif 7 <= row <= 11:
                self.filtry_mapy_widgets.append(widget)
            elif 12 <= row <= 16:
                self.filtry_struktury_widgets.append(widget)

        sb.grid_rowconfigure(wiersz + 1, weight=1)
        tk.Button(
            sb, text="▶  POBIERZ DANE",
            command=self._uruchom,
            bg=KOLORY["panel_ciemny"], fg=KOLORY["bialy"],
            activebackground=KOLORY["naglowek"], activeforeground=KOLORY["bialy"],
            relief="flat", font=("Segoe UI Semibold", 11),
            padx=16, pady=12, cursor="hand2",
        ).grid(row=wiersz + 2, column=0, sticky="ew", padx=16, pady=20)

    # ------------------------------------------------------------------
    # Notebook
    # ------------------------------------------------------------------

    def _zbuduj_notebook(self, rodzic: tk.Widget) -> None:
        self.nb = ttk.Notebook(rodzic)
        self.nb.grid(row=0, column=1, sticky="nsew")
        rodzic.grid_rowconfigure(0, weight=1)
        rodzic.grid_columnconfigure(1, weight=1)

        self.tab_trendy = self._nowa_zakladka("📈  Trendy")
        self.tab_mapa = self._nowa_zakladka("🗺  Mapa")
        self.tab_struktura = self._nowa_zakladka("🥧  Struktura bezrobocia")
        self.tab_statystyki = self._nowa_zakladka("📐  Statystyki")
        self.tab_dane = self._nowa_zakladka("📋  Dane")
        self.tab_o = self._nowa_zakladka("ℹ  O programie")

        self._wypelnij_o_programie()
        self.nb.bind("<<NotebookTabChanged>>", self._aktualizuj_filtry_sidebaru)
        self._aktualizuj_filtry_sidebaru()

    def _nowa_zakladka(self, nazwa: str) -> tk.Frame:
        ramka = tk.Frame(self.nb, bg=KOLORY["obszar"])
        self.nb.add(ramka, text=nazwa)
        ramka.grid_columnconfigure(0, weight=1)
        ramka.grid_rowconfigure(0, weight=1)
        return ramka

    # ------------------------------------------------------------------
    # Pasek statusu
    # ------------------------------------------------------------------

    def _zbuduj_pasek_statusu(self) -> None:
        tk.Label(
            self, textvariable=self.status_var,
            bg=KOLORY["naglowek"], fg=KOLORY["bialy"],
            font=("Segoe UI", 9), anchor="w",
        ).grid(row=3, column=0, sticky="ew", ipady=4)

    # ------------------------------------------------------------------
    # Dispatcher – który tab jest aktywny
    # ------------------------------------------------------------------

    def _uruchom(self) -> None:
        aktywna = self.nb.index("current")
        [
            self._uruchom_trendy,
            self._uruchom_mapy,
            self._uruchom_struktura,
            self._uruchom_statystyki,
            self._uruchom_dane,
            lambda: None,
        ][aktywna]()

    def _aktualizuj_filtry_sidebaru(self, _event: tk.Event | None = None) -> None:
        aktywna = self.nb.index("current")
        for widget in self.filtry_trendow_widgets:
            widget.grid() if aktywna == 0 else widget.grid_remove()
        for widget in self.filtry_mapy_widgets:
            widget.grid() if aktywna == 1 else widget.grid_remove()
        for widget in self.filtry_struktury_widgets:
            widget.grid() if aktywna == 2 else widget.grid_remove()

    def _zamknij(self) -> None:
        self.quit()
        self.destroy()

    # ================================================================
    # ZAKŁADKA 1 – TRENDY
    # ================================================================

    def _uruchom_trendy(self) -> None:
        rok_od = self.rok_od_var.get()
        rok_do = self.rok_do_var.get()
        if rok_od > rok_do:
            messagebox.showwarning("Filtry", "'Rok od' nie może być większy niż 'Rok do'.")
            return
        self.status_var.set(f"Pobieram dane trendów {rok_od}–{rok_do}…")
        self.update_idletasks()
        _wyczysc(self.tab_trendy)
        widok = self.plec_trend_var.get()

        def zadanie() -> None:
            try:
                df_plec = pobierz_trend_bezrobocia_plec(rok_od, rok_do)
                df_stopa = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)
                df_wyn = pobierz_trend_wynagrodzen(rok_od, rok_do)
                df_oferty = pobierz_trend_ofert_pracy(rok_od, rok_do)
                self.after(0, lambda: self._rysuj_trendy(df_plec, df_stopa, df_wyn, df_oferty, widok))
                self.after(0, lambda: self.status_var.set("Trendy załadowane."))
            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
                self.after(0, lambda: self.status_var.set(f"Błąd: {e}"))

        threading.Thread(target=zadanie, daemon=True).start()

    def _rysuj_trendy(self, df_plec, df_stopa, df_wyn, df_oferty, widok) -> None:
        _wyczysc(self.tab_trendy)
        fig, axs = plt.subplots(2, 2, figsize=(13, 8))
        fig.tight_layout(pad=3.5)

        # Wykres 1: Bezrobotni wg płci
        ax = axs[0, 0]
        ax.set_title("Liczba bezrobotnych wg płci")
        kolumny_mapa = {
            "Ogółem + płcie": ["Ogółem", "Kobiety", "Mężczyźni"],
            "Tylko kobiety": ["Kobiety"],
            "Tylko mężczyźni": ["Mężczyźni"],
            "Ogółem": ["Ogółem"],
        }
        kolumny = [k for k in kolumny_mapa.get(widok, ["Ogółem"]) if k in df_plec.columns]
        kolory = [KOLORY["panel_ciemny"], KOLORY["akcent2"], KOLORY["akcent3"]]
        for i, kol in enumerate(kolumny):
            ax.plot(df_plec["rok"], df_plec[kol] / 1000, marker="o", markersize=4,
                    color=kolory[i % len(kolory)], linewidth=2, label=kol)
        if "Różnica (K–M)" in df_plec.columns and widok == "Ogółem + płcie":
            ax2 = ax.twinx()
            ax2.bar(df_plec["rok"], df_plec["Różnica (K–M)"] / 1000,
                    alpha=0.18, color=KOLORY["akcent3"], label="Różnica K–M")
            ax2.set_ylabel("Różnica [tys.]", color=KOLORY["tekst2"], fontsize=8)
            ax2.tick_params(colors=KOLORY["tekst2"])
        ax.set_xlabel("Rok")
        ax.set_ylabel("Liczba bezrobotnych [tys.]")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.4)

        # Wykres 2: Stopa bezrobocia
        ax = axs[0, 1]
        ax.set_title("Stopa bezrobocia rejestrowanego [%]")
        if not df_stopa.empty:
            ax.fill_between(df_stopa["rok"], df_stopa["wartosc"],
                            alpha=0.2, color=KOLORY["akcent2"])
            ax.plot(df_stopa["rok"], df_stopa["wartosc"], color=KOLORY["akcent2"],
                    linewidth=2.5, marker="o", markersize=4)
            if 2020 in df_stopa["rok"].values:
                val = df_stopa.loc[df_stopa["rok"] == 2020, "wartosc"].values[0]
                ax.annotate("COVID-19", xy=(2020, val), xytext=(2020 - 1.5, val + 1.5),
                            arrowprops=dict(arrowstyle="->", color=KOLORY["akcent3"]),
                            color=KOLORY["akcent3"], fontsize=8)
        ax.set_xlabel("Rok")
        ax.set_ylabel("Stopa [%]")
        ax.grid(True, alpha=0.4)

        # Wykres 3: Wynagrodzenie
        ax = axs[1, 0]
        ax.set_title("Przeciętne miesięczne wynagrodzenie brutto [PLN]")
        if not df_wyn.empty:
            ax.fill_between(df_wyn["rok"], df_wyn["wartosc"],
                            alpha=0.2, color=KOLORY["akcent4"])
            ax.plot(df_wyn["rok"], df_wyn["wartosc"], color=KOLORY["akcent4"],
                    linewidth=2.5, marker="s", markersize=4)
        ax.set_xlabel("Rok")
        ax.set_ylabel("PLN")
        ax.grid(True, alpha=0.4)

        # Wykres 4: Oferty pracy
        ax = axs[1, 1]
        ax.set_title("Liczba ofert pracy")
        if not df_oferty.empty:
            ax.bar(df_oferty["rok"], df_oferty["wartosc"] / 1000,
                   color=KOLORY["akcent5"], alpha=0.85, width=0.7)
        ax.set_xlabel("Rok")
        ax.set_ylabel("Oferty [tys.]")
        ax.grid(True, alpha=0.4, axis="y")

        _osadz_figure(fig, self.tab_trendy)

    # ================================================================
    # ZAKŁADKA 2 – MAPA
    # ================================================================

    def _uruchom_mapy(self) -> None:
        rok = self.rok_mapy_var.get()
        typ = self.typ_mapy_var.get()
        self.status_var.set(f"Pobieram dane mapy: {typ} ({rok})…")
        self.update_idletasks()
        _wyczysc(self.tab_mapa)

        def zadanie() -> None:
            try:
                if typ == "Stopa bezrobocia":
                    df = pobierz_mape_stopy_bezrobocia(rok)
                    tytul = f"Stopa bezrobocia wg województw [{rok}] [%]"
                    kolor = KOLORY["akcent2"]
                elif typ == "Wynagrodzenie":
                    df = pobierz_mape_wynagrodzen(rok)
                    tytul = f"Śr. wynagrodzenie brutto wg województw [{rok}] [PLN]"
                    kolor = KOLORY["akcent4"]
                else:
                    df = pobierz_napiecie_rynku(rok)
                    tytul = f"Bezrobotni na 1 ofertę pracy wg województw [{rok}]"
                    kolor = KOLORY["akcent3"]
                self.after(0, lambda: self._rysuj_mape(df, tytul, kolor))
                self.after(0, lambda: self.status_var.set(f"Mapa gotowa: {typ} ({rok})."))
            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
                self.after(0, lambda: self.status_var.set(f"Błąd: {e}"))

        threading.Thread(target=zadanie, daemon=True).start()

    def _rysuj_mape(self, df: pd.DataFrame, tytul: str, kolor_bazy: str) -> None:
        _wyczysc(self.tab_mapa)

        df = df.dropna(subset=["wartosc"]).copy()
        df = df[df["jednostka"].isin(WOJEWODZTWA.values())].copy()
        df = df.sort_values("wartosc", ascending=True).reset_index(drop=True)

        if df.empty:
            tk.Label(self.tab_mapa, text="Brak danych dla wybranych parametrów.",
                     bg=KOLORY["obszar"], fg=KOLORY["tekst2"],
                     font=("Segoe UI", 12)).pack(pady=40)
            return

        geojson = _wczytaj_geojson_wojewodztw()
        df["klucz_wojew"] = df["jednostka"].map(_normalizuj_nazwe)
        wartosci = dict(zip(df["klucz_wojew"], df["wartosc"]))

        fig, ax = plt.subplots(figsize=(11.5, 8))
        norma = plt.Normalize(df["wartosc"].min(), df["wartosc"].max())
        cmap = LinearSegmentedColormap.from_list(
            "dashboard_green",
            [KOLORY["panel2"], KOLORY["panel_jasny"], KOLORY["panel"], KOLORY["panel_ciemny"]],
        )
        if kolor_bazy == KOLORY["akcent4"]:
            jednostka = "PLN"
        elif kolor_bazy == KOLORY["akcent2"]:
            jednostka = "%"
        else:
            jednostka = "wartosc"

        min_x, max_x = 180.0, -180.0
        min_y, max_y = 90.0, -90.0

        for cecha in geojson["features"]:
            nazwa = cecha["properties"]["nazwa"]
            klucz = _normalizuj_nazwe(nazwa)
            wartosc = wartosci.get(klucz)
            geometria = cecha["geometry"]
            wielokaty = geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]]
            najwiekszy_pierscien = None
            najwieksze_pole = -1.0

            for wielokat in wielokaty:
                pierscien = wielokat[0]
                xs = [punkt[0] for punkt in pierscien]
                ys = [punkt[1] for punkt in pierscien]
                min_x, max_x = min(min_x, min(xs)), max(max_x, max(xs))
                min_y, max_y = min(min_y, min(ys)), max(max_y, max(ys))

                pole = _pole_pierscienia(pierscien)
                if pole > najwieksze_pole:
                    najwieksze_pole = pole
                    najwiekszy_pierscien = pierscien

                kolor = cmap(norma(wartosc)) if wartosc is not None else KOLORY["panel2"]
                ax.add_patch(Polygon(
                    pierscien,
                    closed=True,
                    facecolor=kolor,
                    edgecolor=KOLORY["bialy"],
                    linewidth=1.2,
                    joinstyle="round",
                ))

            if najwiekszy_pierscien is not None:
                x, y = _srodek_pierscienia(najwiekszy_pierscien)
                if wartosc is None:
                    tekst = f"{nazwa.title()}\nbrak"
                elif jednostka == "PLN":
                    tekst = f"{nazwa.title()}\n{wartosc:,.0f}".replace(",", " ")
                elif jednostka == "%":
                    tekst = f"{nazwa.title()}\n{wartosc:.1f}%"
                else:
                    tekst = f"{nazwa.title()}\n{wartosc:.1f}"
                ax.text(
                    x, y, tekst,
                    ha="center", va="center",
                    fontsize=6.5,
                    color=KOLORY["tekst"],
                    fontweight="semibold",
                )

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norma)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
        cbar.set_label(jednostka)

        ax.set_title(tytul, fontsize=13, pad=12, color=KOLORY["tekst"], fontweight="bold")
        ax.set_xlim(min_x - 0.35, max_x + 0.35)
        ax.set_ylim(min_y - 0.25, max_y + 0.25)
        ax.set_aspect("equal")
        ax.set_facecolor(KOLORY["obszar"])
        ax.axis("off")
        fig.tight_layout()
        _osadz_figure(fig, self.tab_mapa)

    # ================================================================
    # ZAKŁADKA 3 – STRUKTURA
    # ================================================================

    def _uruchom_struktura(self) -> None:
        rok = self.rok_str_var.get()
        wojew_nazwa = self.wojew_var.get()
        wojew = None if wojew_nazwa == "Wszystkie" else wojew_nazwa
        self.status_var.set(f"Pobieram strukturę bezrobocia ({rok})…")
        self.update_idletasks()
        _wyczysc(self.tab_struktura)

        def zadanie() -> None:
            try:
                df_plec = pobierz_strukture_plci(rok, wojew)
                df_wyk = pobierz_strukture_wyksztalcenia(rok, wojew)
                df_wiek = pobierz_strukture_wieku(rok, wojew)
                df_staz = pobierz_strukture_stazu(rok, wojew)
                self.after(0, lambda: self._rysuj_strukturę(
                    df_plec, df_wyk, df_wiek, df_staz, rok, wojew_nazwa))
                self.after(0, lambda: self.status_var.set(f"Struktura ({rok}) gotowa."))
            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
                self.after(0, lambda: self.status_var.set(f"Błąd: {e}"))

        threading.Thread(target=zadanie, daemon=True).start()

    def _rysuj_strukturę(self, df_plec, df_wyk, df_wiek, df_staz, rok, wojew_nazwa) -> None:
        _wyczysc(self.tab_struktura)
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
            2, 2, figsize=(14, 9), layout="constrained",
        )
        fig.suptitle(f"Struktura bezrobocia – {wojew_nazwa} – {rok}", fontsize=13)

        # Kołowy: płeć
        if not df_plec.empty and df_plec["liczba"].sum() > 0:
            ax1.pie(
                df_plec["liczba"], labels=df_plec["plec"],
                autopct="%1.1f%%", startangle=90,
                colors=[KOLORY["akcent2"], KOLORY["panel_ciemny"]],
                pctdistance=0.75,
                wedgeprops=dict(linewidth=1.5, edgecolor=KOLORY["bialy"]),
            )
        ax1.set_title("Bezrobotni wg płci", pad=10)

        # Słupkowy poziomy: wykształcenie
        if not df_wyk.empty and df_wyk["liczba"].sum() > 0:
            df_s = df_wyk.sort_values("liczba")
            bars = ax2.barh(df_s["wyksztalcenie"], df_s["liczba"] / 1000,
                            color=PALETA_WYKRESY[:len(df_s)], height=0.6,
                            edgecolor=KOLORY["linia"])
            for bar, val in zip(bars, df_s["liczba"] / 1000):
                ax2.text(
                    bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f} tys.", va="center", fontsize=7, color=KOLORY["tekst"],
                )
            ax2.grid(True, axis="x", alpha=0.3)
            ax2.tick_params(axis="y", labelsize=8)
        ax2.set_title("Bezrobotni wg wykształcenia", pad=10)

        # Słupkowy pionowy: wiek
        if not df_wiek.empty and df_wiek["liczba"].sum() > 0:
            ax3.bar(df_wiek["wiek"], df_wiek["liczba"] / 1000,
                    color=PALETA_WYKRESY[:len(df_wiek)],
                    edgecolor=KOLORY["linia"], width=0.65)
            ax3.set_ylabel("Liczba [tys.]")
            ax3.tick_params(axis="x", rotation=25, labelsize=8)
            ax3.grid(True, axis="y", alpha=0.3)
        ax3.set_title("Bezrobotni wg grup wiekowych", pad=10)

        # Słupkowy poziomy: staż
        if not df_staz.empty and df_staz["liczba"].sum() > 0:
            df_s2 = df_staz.sort_values("liczba")
            bars2 = ax4.barh(df_s2["staz"], df_s2["liczba"] / 1000,
                             color=PALETA_WYKRESY[:len(df_s2)], height=0.6,
                             edgecolor=KOLORY["linia"])
            for bar, val in zip(bars2, df_s2["liczba"] / 1000):
                ax4.text(
                    bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f} tys.", va="center", fontsize=7, color=KOLORY["tekst"],
                )
            ax4.set_xlabel("Liczba [tys.]")
            ax4.grid(True, axis="x", alpha=0.3)
            ax4.tick_params(axis="y", labelsize=8)
        ax4.set_title("Bezrobotni wg stażu pracy", pad=10)

        _osadz_figure(fig, self.tab_struktura)

    # ================================================================
    # ZAKŁADKA 4 – STATYSTYKI
    # ================================================================

    STAT_WSKAZNIKI = [
        "Bezrobotni ogółem [tys.]",
        "Bezrobotne kobiety [tys.]",
        "Bezrobotni mężczyźni [tys.]",
        "Różnica K–M [tys.]",
        "Stopa bezrobocia [%]",
        "Wynagrodzenie brutto [PLN]",
        "Oferty pracy [szt.]",
    ]

    STAT_MIARY = [
        ("Średnia",             "mean"),
        ("Mediana",             "median"),
        ("Q1 (25%)",            "q1"),
        ("Q3 (75%)",            "q3"),
        ("Min",                 "min"),
        ("Max",                 "max"),
        ("Odch. std.",          "std"),
        ("Wariancja",           "var"),
        ("Zakres (Max–Min)",    "zakres"),
        ("Liczba obserwacji",   "count"),
    ]

    def _uruchom_statystyki(self) -> None:
        rok_od = self.rok_od_var.get()
        rok_do = self.rok_do_var.get()
        self.status_var.set(f"Pobieram dane statystyk {rok_od}–{rok_do}…")
        self.update_idletasks()
        _wyczysc(self.tab_statystyki)
        self._stat_dane: dict = {}
        self._zbuduj_statystyki_ui(rok_od, rok_do)

    def _zbuduj_statystyki_ui(self, rok_od: int, rok_do: int) -> None:
        outer = tk.Frame(self.tab_statystyki, bg=KOLORY["obszar"])
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        # ── LEWY PANEL FILTRÓW ──────────────────────────────────────
        filtr = tk.Frame(outer, bg=KOLORY["panel"], width=195)
        filtr.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        filtr.grid_propagate(False)
        filtr.grid_columnconfigure(0, weight=1)

        tk.Label(filtr, text="FILTRY", bg=KOLORY["panel"],
                 fg=KOLORY["panel_ciemny"],
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=12, pady=(12, 2))

        tk.Label(filtr, text="Wskaźniki:", bg=KOLORY["panel"],
                 fg=KOLORY["tekst"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=12, pady=(8, 2))

        self._stat_wskaznik_vars: dict[str, tk.BooleanVar] = {}
        for nazwa in self.STAT_WSKAZNIKI:
            var = tk.BooleanVar(value=True)
            self._stat_wskaznik_vars[nazwa] = var
            tk.Checkbutton(
                filtr, text=nazwa, variable=var,
                bg=KOLORY["panel"], fg=KOLORY["tekst"],
                activebackground=KOLORY["panel_jasny"],
                selectcolor=KOLORY["panel_jasny"],
                font=("Segoe UI", 8), anchor="w",
                command=self._odswiez_statystyki_widok,
            ).pack(fill="x", padx=10, pady=1)

        tk.Frame(filtr, bg=KOLORY["linia"], height=1).pack(
            fill="x", padx=12, pady=(8, 4))

        tk.Label(filtr, text="Miary statystyczne:", bg=KOLORY["panel"],
                 fg=KOLORY["tekst"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=12, pady=(4, 2))

        self._stat_miara_vars: dict[str, tk.BooleanVar] = {}
        for nazwa, klucz in self.STAT_MIARY:
            default = klucz in ("mean", "median", "min", "max", "std")
            var = tk.BooleanVar(value=default)
            self._stat_miara_vars[klucz] = var
            tk.Checkbutton(
                filtr, text=nazwa, variable=var,
                bg=KOLORY["panel"], fg=KOLORY["tekst"],
                activebackground=KOLORY["panel_jasny"],
                selectcolor=KOLORY["panel_jasny"],
                font=("Segoe UI", 8), anchor="w",
                command=self._odswiez_statystyki_widok,
            ).pack(fill="x", padx=10, pady=1)

        # ── PRAWA CZĘŚĆ: tabela + boxplot ───────────────────────────
        prawy_outer = tk.Frame(outer, bg=KOLORY["obszar"])
        prawy_outer.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        prawy_outer.grid_columnconfigure(0, weight=3)
        prawy_outer.grid_columnconfigure(1, weight=2)
        prawy_outer.grid_rowconfigure(0, weight=1)

        self._stat_tabela_frame = tk.Frame(prawy_outer, bg=KOLORY["panel"])
        self._stat_tabela_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(self._stat_tabela_frame, text="Statystyki opisowe",
                 bg=KOLORY["panel"], fg=KOLORY["tekst"],
                 font=("Segoe UI Semibold", 11)).pack(pady=8)

        self._stat_tree_frame = tk.Frame(self._stat_tabela_frame, bg=KOLORY["panel"])
        self._stat_tree_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        self._stat_tree_frame.grid_columnconfigure(0, weight=1)
        self._stat_tree_frame.grid_rowconfigure(0, weight=1)

        self._stat_box_frame = tk.Frame(prawy_outer, bg=KOLORY["obszar"])
        self._stat_box_frame.grid(row=0, column=1, sticky="nsew")

        def zadanie() -> None:
            try:
                df_plec = pobierz_trend_bezrobocia_plec(rok_od, rok_do)
                df_stopa = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)
                df_wyn = pobierz_trend_wynagrodzen(rok_od, rok_do)
                df_oferty = pobierz_trend_ofert_pracy(rok_od, rok_do)
                self._stat_dane = {
                    "df_plec": df_plec,
                    "df_stopa": df_stopa,
                    "df_wyn": df_wyn,
                    "df_oferty": df_oferty,
                }
                self.after(0, self._odswiez_statystyki_widok)
                self.after(0, lambda: self.status_var.set("Statystyki gotowe."))
            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))

        threading.Thread(target=zadanie, daemon=True).start()

    def _odswiez_statystyki_widok(self) -> None:
        if not self._stat_dane:
            return

        df_plec  = self._stat_dane["df_plec"]
        df_stopa = self._stat_dane["df_stopa"]
        df_wyn   = self._stat_dane["df_wyn"]
        df_oferty = self._stat_dane["df_oferty"]

        # Wszystkie dostępne serie
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
            if self._stat_wskaznik_vars.get(n, tk.BooleanVar(value=False)).get()
        }
        aktywne_miary = [
            (nazwa, klucz) for nazwa, klucz in self.STAT_MIARY
            if self._stat_miara_vars.get(klucz, tk.BooleanVar(value=False)).get()
        ]

        # Odśwież tabelę
        for w in self._stat_tree_frame.winfo_children():
            w.destroy()

        if aktywne and aktywne_miary:
            kol_ids  = ["wskaznik"] + [k for _, k in aktywne_miary]
            kol_nagl = {"wskaznik": "Wskaźnik"}
            kol_nagl.update({k: n for n, k in aktywne_miary})

            tree = ttk.Treeview(self._stat_tree_frame,
                                show="headings", columns=kol_ids)
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

            sb_y = ttk.Scrollbar(self._stat_tree_frame, orient="vertical",
                                 command=tree.yview)
            sb_x = ttk.Scrollbar(self._stat_tree_frame, orient="horizontal",
                                 command=tree.xview)
            tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
            sb_x.grid(row=1, column=0, sticky="ew")
            sb_y.grid(row=0, column=1, sticky="ns")
            tree.grid(row=0, column=0, sticky="nsew")
        else:
            tk.Label(self._stat_tree_frame,
                     text="Zaznacz wskaźniki i miary po lewej stronie.",
                     bg=KOLORY["panel"], fg=KOLORY["tekst2"],
                     font=("Segoe UI", 10)).grid(row=0, column=0, padx=20, pady=40)

        # Odśwież boxplot
        for w in self._stat_box_frame.winfo_children():
            w.destroy()

        if aktywne:
            fig, ax = plt.subplots(figsize=(5, 5))
            dane_box = {
                n: pd.to_numeric(s, errors="coerce").dropna().values
                for n, s in aktywne.items()
            }
            dane_box = {n: v for n, v in dane_box.items() if len(v) > 0}
            if dane_box:
                etykiety = [n.replace(" [", "\n[") for n in dane_box]
                ax.boxplot(
                    list(dane_box.values()),
                    labels=etykiety,
                    patch_artist=True,
                    medianprops=dict(color=KOLORY["akcent3"], linewidth=2),
                    boxprops=dict(facecolor=KOLORY["akcent"] + "88",
                                  color=KOLORY["panel_ciemny"]),
                    whiskerprops=dict(color=KOLORY["tekst2"]),
                    capprops=dict(color=KOLORY["tekst2"]),
                    flierprops=dict(marker="o", color=KOLORY["akcent2"], alpha=0.5),
                )
                ax.set_title("Wykresy pudełkowe", fontsize=10)
                ax.tick_params(axis="x", labelsize=7)
                ax.grid(True, axis="y", alpha=0.4)
            _osadz_figure(fig, self._stat_box_frame)

    # ================================================================
    # ZAKŁADKA 5 – DANE SUROWE
    # ================================================================

    # Wszystkie dostępne zbiory danych z opisem i typem pobierania
    DANE_ZRODLA = [
        ("Bezrobotni wg płci (ogółem, K, M)",   "plec",    True),
        ("Stopa bezrobocia [%]",                 "stopa",   True),
        ("Wynagrodzenie brutto [PLN]",           "wynagrodzenie", True),
        ("Oferty pracy [szt.]",                  "oferty",  True),
        ("Mapa – stopa bezrobocia (woj.)",       "mapa_stopa",   False),
        ("Mapa – wynagrodzenia (woj.)",          "mapa_wyn",     False),
        ("Napięcie rynku pracy (woj.)",          "mapa_napiecie", False),
        ("Struktura – wykształcenie",            "str_wyk",  False),
        ("Struktura – wiek",                     "str_wiek", False),
        ("Struktura – staż pracy",               "str_staz", False),
        ("Struktura – płeć",                     "str_plec", False),
    ]

    def _uruchom_dane(self) -> None:
        rok_od = self.rok_od_var.get()
        rok_do = self.rok_do_var.get()
        self.status_var.set(f"Budowanie zakładki danych…")
        self.update_idletasks()
        _wyczysc(self.tab_dane)
        self._dane_cache: dict[str, pd.DataFrame] = {}
        self._zbuduj_dane_ui(rok_od, rok_do)

    def _zbuduj_dane_ui(self, rok_od: int, rok_do: int) -> None:
        outer = tk.Frame(self.tab_dane, bg=KOLORY["obszar"])
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        # ── LEWY PANEL FILTRÓW ──────────────────────────────────────
        filtr = tk.Frame(outer, bg=KOLORY["panel"], width=220)
        filtr.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        filtr.grid_propagate(False)
        filtr.grid_columnconfigure(0, weight=1)

        tk.Label(filtr, text="ŹRÓDŁA DANYCH", bg=KOLORY["panel"],
                 fg=KOLORY["panel_ciemny"],
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=12, pady=(12, 2))

        tk.Label(filtr, text="Zaznacz co chcesz zobaczyć:", bg=KOLORY["panel"],
                 fg=KOLORY["tekst2"], font=("Segoe UI", 8)).pack(
            anchor="w", padx=12, pady=(4, 6))

        self._dane_zrodlo_vars: dict[str, tk.BooleanVar] = {}
        for etykieta, klucz, domyslnie in self.DANE_ZRODLA:
            var = tk.BooleanVar(value=domyslnie)
            self._dane_zrodlo_vars[klucz] = var
            tk.Checkbutton(
                filtr, text=etykieta, variable=var,
                bg=KOLORY["panel"], fg=KOLORY["tekst"],
                activebackground=KOLORY["panel_jasny"],
                selectcolor=KOLORY["panel_jasny"],
                font=("Segoe UI", 8), anchor="w",
                wraplength=185,
                command=lambda: self._odswiez_dane_widok(),
            ).pack(fill="x", padx=10, pady=2)

        tk.Frame(filtr, bg=KOLORY["linia"], height=1).pack(
            fill="x", padx=12, pady=(10, 6))

        # Rok dla danych strukturalnych (jednorazowych)
        tk.Label(filtr, text="Rok dla danych\nstrukturalnych / mapy:",
                 bg=KOLORY["panel"], fg=KOLORY["tekst"],
                 font=("Segoe UI", 8), justify="left").pack(
            anchor="w", padx=12, pady=(2, 2))

        self._dane_rok_str_var = tk.IntVar(value=self.rok_str_var.get())
        ttk.Combobox(filtr, textvariable=self._dane_rok_str_var,
                     values=list(range(2005, 2025)),
                     width=7, state="readonly").pack(anchor="w", padx=12, pady=(0, 6))

        self._dane_wojew_var = tk.StringVar(value=self.wojew_var.get())
        tk.Label(filtr, text="Województwo:", bg=KOLORY["panel"],
                 fg=KOLORY["tekst"], font=("Segoe UI", 8)).pack(
            anchor="w", padx=12, pady=(4, 2))
        ttk.Combobox(filtr, textvariable=self._dane_wojew_var,
                     values=NAZWY_WOJEW, width=16, state="readonly").pack(
            anchor="w", padx=12, pady=(0, 8))

        tk.Button(
            filtr, text="▶  Pobierz zaznaczone",
            command=lambda: self._pobierz_dane_zrodla(rok_od, rok_do),
            bg=KOLORY["panel_ciemny"], fg=KOLORY["bialy"],
            activebackground=KOLORY["naglowek"], activeforeground=KOLORY["bialy"],
            relief="flat", font=("Segoe UI", 9), padx=10, pady=6, cursor="hand2",
        ).pack(fill="x", padx=12, pady=(4, 12))

        # ── PRAWA CZĘŚĆ: notebook z zakładkami danych ───────────────
        prawa = tk.Frame(outer, bg=KOLORY["obszar"])
        prawa.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        prawa.grid_columnconfigure(0, weight=1)
        prawa.grid_rowconfigure(1, weight=1)

        self._dane_info_lbl = tk.Label(
            prawa,
            text="Zaznacz źródła danych i kliknij '▶ Pobierz zaznaczone'.",
            bg=KOLORY["obszar"], fg=KOLORY["tekst2"], font=("Segoe UI", 10))
        self._dane_info_lbl.grid(row=0, column=0, pady=16)

        self._dane_nb = ttk.Notebook(prawa)
        self._dane_nb.grid(row=1, column=0, sticky="nsew")
        self._dane_tabs: dict[str, tk.Frame] = {}

    def _pobierz_dane_zrodla(self, rok_od: int, rok_do: int) -> None:
        zaznaczone = [k for k, v in self._dane_zrodlo_vars.items() if v.get()]
        if not zaznaczone:
            messagebox.showinfo("Filtry", "Zaznacz przynajmniej jedno źródło danych.")
            return

        self.status_var.set("Pobieram dane…")
        self.update_idletasks()
        rok_str = self._dane_rok_str_var.get()
        wojew_nazwa = self._dane_wojew_var.get()
        wojew = None if wojew_nazwa == "Wszystkie" else wojew_nazwa

        def zadanie() -> None:
            nowe: dict[str, pd.DataFrame] = {}
            etykiety_map = {e: k for e, k, _ in self.DANE_ZRODLA}
            klucz_etykieta = {k: e for e, k, _ in self.DANE_ZRODLA}

            try:
                if "plec" in zaznaczone:
                    df = pobierz_trend_bezrobocia_plec(rok_od, rok_do)
                    nowe["plec"] = df

                if "stopa" in zaznaczone:
                    df = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)
                    df = df.rename(columns={"wartosc": "Stopa bezrobocia [%]",
                                            "jednostka": "Jednostka",
                                            "id_jednostki": "ID jednostki"})
                    nowe["stopa"] = df

                if "wynagrodzenie" in zaznaczone:
                    df = pobierz_trend_wynagrodzen(rok_od, rok_do)
                    df = df.rename(columns={"wartosc": "Wynagrodzenie brutto [PLN]",
                                            "jednostka": "Jednostka",
                                            "id_jednostki": "ID jednostki"})
                    nowe["wynagrodzenie"] = df

                if "oferty" in zaznaczone:
                    df = pobierz_trend_ofert_pracy(rok_od, rok_do)
                    df = df.rename(columns={"wartosc": "Oferty pracy [szt.]",
                                            "jednostka": "Jednostka",
                                            "id_jednostki": "ID jednostki"})
                    nowe["oferty"] = df

                if "mapa_stopa" in zaznaczone:
                    df = pobierz_mape_stopy_bezrobocia(rok_str)
                    df = df.rename(columns={"wartosc": "Stopa bezrobocia [%]",
                                            "jednostka": "Województwo",
                                            "id_jednostki": "ID jednostki"})
                    nowe["mapa_stopa"] = df

                if "mapa_wyn" in zaznaczone:
                    df = pobierz_mape_wynagrodzen(rok_str)
                    df = df.rename(columns={"wartosc": "Wynagrodzenie brutto [PLN]",
                                            "jednostka": "Województwo",
                                            "id_jednostki": "ID jednostki"})
                    nowe["mapa_wyn"] = df

                if "mapa_napiecie" in zaznaczone:
                    df = pobierz_napiecie_rynku(rok_str)
                    df = df.rename(columns={"wartosc": "Bezrobotni/ofertę [os.]",
                                            "jednostka": "Województwo",
                                            "id_jednostki": "ID jednostki"})
                    nowe["mapa_napiecie"] = df

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

                self._dane_cache.update(nowe)
                lacznie = sum(len(v) for v in nowe.values())
                self.after(0, lambda: self._odswiez_dane_widok())
                self.after(0, lambda: self.status_var.set(
                    f"Załadowano {lacznie} wierszy w {len(nowe)} zbiorach."))

            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
                self.after(0, lambda: self.status_var.set(f"Błąd: {e}"))

        threading.Thread(target=zadanie, daemon=True).start()

    def _odswiez_dane_widok(self) -> None:
        if not hasattr(self, "_dane_cache") or not self._dane_cache:
            return

        self._dane_info_lbl.grid_remove()

        # Wyczyść stare zakładki
        for tab_id in self._dane_nb.tabs():
            self._dane_nb.forget(tab_id)
        self._dane_tabs.clear()

        etykiety_klucze = {k: e for e, k, _ in self.DANE_ZRODLA}

        for klucz, df in self._dane_cache.items():
            if not self._dane_zrodlo_vars.get(klucz, tk.BooleanVar(value=True)).get():
                continue
            etykieta = etykiety_klucze.get(klucz, klucz)
            # Skróć etykietę zakładki
            skrot = etykieta[:28] + "…" if len(etykieta) > 28 else etykieta
            ramka = tk.Frame(self._dane_nb, bg=KOLORY["obszar"])
            ramka.grid_columnconfigure(0, weight=1)
            ramka.grid_rowconfigure(0, weight=1)
            self._dane_nb.add(ramka, text=skrot)
            self._pokaz_df_w_ramce(df, ramka)

    def _pokaz_df_w_ramce(self, df: pd.DataFrame, ramka: tk.Frame) -> None:
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
                if isinstance(v, float):
                    wartosci.append("" if pd.isna(v) else f"{v:.2f}")
                else:
                    wartosci.append(str(v))
            tree.insert("", "end", values=wartosci)

        sb_y = ttk.Scrollbar(ramka, orient="vertical", command=tree.yview)
        sb_x = ttk.Scrollbar(ramka, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_x.grid(row=1, column=0, sticky="ew")
        sb_y.grid(row=0, column=1, sticky="ns")
        tree.grid(row=0, column=0, sticky="nsew")

    # ================================================================
    # ZAKŁADKA 6 – O PROGRAMIE
    # ================================================================

    def _wypelnij_o_programie(self) -> None:
        frame = tk.Frame(self.tab_o, bg=KOLORY["panel"], padx=40, pady=30)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="📊  Analiza Rynku Pracy w Polsce",
                 bg=KOLORY["panel"], fg=KOLORY["panel_ciemny"],
                 font=("Segoe UI Light", 20)).pack(pady=(0, 12))

        tk.Label(frame, text=(
            "Aplikacja pobiera i wizualizuje dane z Banku Danych Lokalnych GUS (BDL).\n\n"
            "Dostępne analizy:\n"
            "  📈  Trendy – bezrobocie wg płci, stopa, wynagrodzenia, oferty pracy\n"
            "  🗺  Mapa – kartogram słupkowy wg województw\n"
            "  🥧  Struktura bezrobocia – płeć, wykształcenie, wiek, staż pracy\n"
            "  📐  Statystyki – średnia, mediana, kwartyle, odch. std., boxploty\n"
            "  📋  Dane – surowa tabela pobranych danych\n\n"
            "Dane: Bank Danych Lokalnych GUS\n"
            "API: https://bdl.stat.gov.pl/api/v1\n\n"
            "Technologie: Python · tkinter · pandas · matplotlib · requests"
        ), bg=KOLORY["panel"], fg=KOLORY["tekst"],
                 font=("Segoe UI", 10), justify="left").pack()

# ---------------------------------------------------------------------------
# UWAGA: Tuż pod spodem odpalamy program.
# ---------------------------------------------------------------------------

def uruchom_gui() -> None:
    app = AplikacjaRynkuPracy()
    app.mainloop()
