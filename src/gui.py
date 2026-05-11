"""Dashboard tkinter – Analiza rynku pracy w Polsce (GUS BDL)."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
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
        self.tab_struktura = self._nowa_zakladka("🥧  Struktura")
        self.tab_statystyki = self._nowa_zakladka("📐  Statystyki")
        self.tab_dane = self._nowa_zakladka("📋  Dane")
        self.tab_o = self._nowa_zakladka("ℹ  O programie")

        self._wypelnij_o_programie()

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

        fig, ax = plt.subplots(figsize=(13, 7))
        norma = plt.Normalize(df["wartosc"].min(), df["wartosc"].max())
        cmap = plt.cm.Greens
        kolory = [cmap(norma(v)) for v in df["wartosc"]]

        bars = ax.barh(df["jednostka"], df["wartosc"], color=kolory,
                       edgecolor=KOLORY["linia"], linewidth=0.5, height=0.7)
        for bar, val in zip(bars, df["wartosc"]):
            ax.text(bar.get_width() + df["wartosc"].max() * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", ha="left", fontsize=8, color=KOLORY["tekst"])

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norma)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, label="Wartość", pad=0.02)

        ax.set_title(tytul, fontsize=12)
        ax.grid(True, axis="x", alpha=0.3)
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
        fig = plt.figure(figsize=(14, 8))
        fig.suptitle(f"Struktura bezrobocia – {wojew_nazwa} – {rok}", fontsize=13, y=0.98)

        # Kołowy: płeć
        ax1 = fig.add_subplot(2, 2, 1)
        if not df_plec.empty and df_plec["liczba"].sum() > 0:
            ax1.pie(
                df_plec["liczba"], labels=df_plec["plec"],
                autopct="%1.1f%%", startangle=90,
                colors=[KOLORY["akcent2"], KOLORY["panel_ciemny"]],
                pctdistance=0.75,
                wedgeprops=dict(linewidth=1.5, edgecolor=KOLORY["bialy"]),
            )
        ax1.set_title("Bezrobotni wg płci")

        # Słupkowy poziomy: wykształcenie
        ax2 = fig.add_subplot(2, 2, 2)
        if not df_wyk.empty and df_wyk["liczba"].sum() > 0:
            df_s = df_wyk.sort_values("liczba")
            bars = ax2.barh(df_s["wyksztalcenie"], df_s["liczba"] / 1000,
                            color=PALETA_WYKRESY[:len(df_s)], height=0.6,
                            edgecolor=KOLORY["linia"])
            for bar, val in zip(bars, df_s["liczba"] / 1000):
                ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                         f"{val:.1f} tys.", va="center", fontsize=7.5, color=KOLORY["tekst"])
            ax2.set_xlabel("Liczba [tys.]")
            ax2.grid(True, axis="x", alpha=0.3)
        ax2.set_title("Bezrobotni wg wykształcenia")

        # Słupkowy pionowy: wiek
        ax3 = fig.add_subplot(2, 2, 3)
        if not df_wiek.empty and df_wiek["liczba"].sum() > 0:
            ax3.bar(df_wiek["wiek"], df_wiek["liczba"] / 1000,
                    color=PALETA_WYKRESY[:len(df_wiek)],
                    edgecolor=KOLORY["linia"], width=0.65)
            ax3.set_ylabel("Liczba [tys.]")
            ax3.tick_params(axis="x", rotation=20)
            ax3.grid(True, axis="y", alpha=0.3)
        ax3.set_title("Bezrobotni wg grup wiekowych")

        # Słupkowy poziomy: staż
        ax4 = fig.add_subplot(2, 2, 4)
        if not df_staz.empty and df_staz["liczba"].sum() > 0:
            df_s2 = df_staz.sort_values("liczba")
            bars2 = ax4.barh(df_s2["staz"], df_s2["liczba"] / 1000,
                             color=PALETA_WYKRESY[:len(df_s2)], height=0.6,
                             edgecolor=KOLORY["linia"])
            for bar, val in zip(bars2, df_s2["liczba"] / 1000):
                ax4.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                         f"{val:.1f} tys.", va="center", fontsize=7.5, color=KOLORY["tekst"])
            ax4.set_xlabel("Liczba [tys.]")
            ax4.grid(True, axis="x", alpha=0.3)
        ax4.set_title("Bezrobotni wg stażu pracy")

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        _osadz_figure(fig, self.tab_struktura)

    # ================================================================
    # ZAKŁADKA 4 – STATYSTYKI
    # ================================================================

    def _uruchom_statystyki(self) -> None:
        rok_od = self.rok_od_var.get()
        rok_do = self.rok_do_var.get()
        self.status_var.set(f"Pobieram dane statystyk {rok_od}–{rok_do}…")
        self.update_idletasks()
        _wyczysc(self.tab_statystyki)

        def zadanie() -> None:
            try:
                df_plec = pobierz_trend_bezrobocia_plec(rok_od, rok_do)
                df_stopa = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)
                df_wyn = pobierz_trend_wynagrodzen(rok_od, rok_do)
                self.after(0, lambda: self._rysuj_statystyki(df_plec, df_stopa, df_wyn))
                self.after(0, lambda: self.status_var.set("Statystyki gotowe."))
            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))

        threading.Thread(target=zadanie, daemon=True).start()

    def _rysuj_statystyki(self, df_plec, df_stopa, df_wyn) -> None:
        _wyczysc(self.tab_statystyki)

        frame = tk.Frame(self.tab_statystyki, bg=KOLORY["obszar"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Lewa: tabela
        tabela_frame = tk.Frame(frame, bg=KOLORY["panel"])
        tabela_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(tabela_frame, text="Statystyki opisowe", bg=KOLORY["panel"],
                 fg=KOLORY["tekst"], font=("Segoe UI Semibold", 11)).pack(pady=10)

        tree = ttk.Treeview(tabela_frame, show="headings")
        tree["columns"] = ("wskaznik", "srednia", "mediana", "q1", "q3", "min", "max", "std")
        for col, nagl in {
            "wskaznik": "Wskaźnik", "srednia": "Średnia", "mediana": "Mediana",
            "q1": "Q1 (25%)", "q3": "Q3 (75%)", "min": "Min",
            "max": "Max", "std": "Odch. std.",
        }.items():
            tree.heading(col, text=nagl)
            tree.column(col, width=90, anchor="center")
        tree.column("wskaznik", width=180, anchor="w")

        def dodaj_wiersz(nazwa: str, s: pd.Series) -> None:
            s_clean = pd.to_numeric(s, errors="coerce").dropna()
            if s_clean.empty:
                return
            tree.insert("", "end", values=(
                nazwa,
                f"{s_clean.mean():.2f}",
                f"{s_clean.median():.2f}",
                f"{s_clean.quantile(0.25):.2f}",
                f"{s_clean.quantile(0.75):.2f}",
                f"{s_clean.min():.2f}",
                f"{s_clean.max():.2f}",
                f"{s_clean.std():.2f}",
            ))

        if "Ogółem" in df_plec.columns:
            dodaj_wiersz("Bezrobotni ogółem [tys.]", df_plec["Ogółem"] / 1000)
        if "Kobiety" in df_plec.columns:
            dodaj_wiersz("Bezrobotne kobiety [tys.]", df_plec["Kobiety"] / 1000)
        if "Mężczyźni" in df_plec.columns:
            dodaj_wiersz("Bezrobotni mężczyźni [tys.]", df_plec["Mężczyźni"] / 1000)
        if not df_stopa.empty:
            dodaj_wiersz("Stopa bezrobocia [%]", df_stopa["wartosc"])
        if not df_wyn.empty:
            dodaj_wiersz("Wynagrodzenie brutto [PLN]", df_wyn["wartosc"])

        tree.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        # Prawa: boxplot
        prawy = tk.Frame(frame, bg=KOLORY["obszar"])
        prawy.grid(row=0, column=1, sticky="nsew")

        dane_box: dict[str, pd.Series] = {}
        if "Ogółem" in df_plec.columns:
            dane_box["Bezrobotni\n[tys.]"] = df_plec["Ogółem"].dropna() / 1000
        if not df_stopa.empty:
            dane_box["Stopa bezr.\n[%]"] = df_stopa["wartosc"].dropna()
        if not df_wyn.empty:
            dane_box["Wynagrodzenie\n[PLN/100]"] = df_wyn["wartosc"].dropna() / 100

        if dane_box:
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.boxplot(
                [s.values for s in dane_box.values()],
                labels=list(dane_box.keys()),
                patch_artist=True,
                medianprops=dict(color=KOLORY["akcent3"], linewidth=2),
                boxprops=dict(facecolor=KOLORY["akcent"] + "88", color=KOLORY["panel_ciemny"]),
                whiskerprops=dict(color=KOLORY["tekst2"]),
                capprops=dict(color=KOLORY["tekst2"]),
                flierprops=dict(marker="o", color=KOLORY["akcent2"], alpha=0.5),
            )
            ax.set_title("Wykresy pudełkowe kluczowych wskaźników")
            ax.grid(True, axis="y", alpha=0.4)
            _osadz_figure(fig, prawy)

    # ================================================================
    # ZAKŁADKA 5 – DANE SUROWE
    # ================================================================

    def _uruchom_dane(self) -> None:
        rok_od = self.rok_od_var.get()
        rok_do = self.rok_do_var.get()
        self.status_var.set(f"Pobieram surowe dane {rok_od}–{rok_do}…")
        self.update_idletasks()
        _wyczysc(self.tab_dane)

        def zadanie() -> None:
            try:
                df = pobierz_trend_bezrobocia_plec(rok_od, rok_do)
                df2 = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)[["rok", "wartosc"]].rename(
                    columns={"wartosc": "Stopa [%]"})
                df3 = pobierz_trend_wynagrodzen(rok_od, rok_do)[["rok", "wartosc"]].rename(
                    columns={"wartosc": "Wynagrodzenie [PLN]"})
                polaczone = df.merge(df2, on="rok", how="outer").merge(df3, on="rok", how="outer")
                self.after(0, lambda: self._pokaz_dane(polaczone))
                self.after(0, lambda: self.status_var.set(f"Załadowano {len(polaczone)} wierszy."))
            except GusApiError as e:
                self.after(0, lambda: messagebox.showerror("Błąd API", str(e)))

        threading.Thread(target=zadanie, daemon=True).start()

    def _pokaz_dane(self, df: pd.DataFrame) -> None:
        _wyczysc(self.tab_dane)
        frame = tk.Frame(self.tab_dane, bg=KOLORY["obszar"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(frame, show="headings")
        kolumny = list(df.columns)
        tree["columns"] = kolumny
        for kol in kolumny:
            tree.heading(kol, text=kol)
            tree.column(kol, width=130, anchor="center")
        for _, row in df.iterrows():
            wartosci = [f"{row[k]:.1f}" if isinstance(row[k], float) else str(row[k])
                        for k in kolumny]
            tree.insert("", "end", values=wartosci)

        sb_y = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=sb_y.set)
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
            "  🥧  Struktura – płeć, wykształcenie, wiek, staż pracy\n"
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