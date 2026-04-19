"""Prosty interfejs tkinter do uruchamiania analiz rynku pracy."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .analysis import AnalizatorRynkuPracy
from .visualization import (
    wykres_analiza_1,
    wykres_analiza_2,
    wykres_analiza_3,
    wykres_analiza_4,
    wykres_analiza_5,
    wykres_analiza_6,
    wykres_analiza_7,
)


class AplikacjaRynkuPracy(tk.Tk):
    """Główne okno aplikacji."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Analiza rynku pracy w Polsce")
        self.geometry("1200x760")

        self.analizator = AnalizatorRynkuPracy()
        self.canvas_plot: FigureCanvasTkAgg | None = None

        self._zbuduj_interfejs()

    def _zbuduj_interfejs(self) -> None:
        panel = ttk.Frame(self, padding=10)
        panel.pack(side="top", fill="x")

        ttk.Label(panel, text="Rok:").pack(side="left")
        self.rok_var = tk.IntVar(value=2023)
        ttk.Entry(panel, width=8, textvariable=self.rok_var).pack(side="left", padx=5)

        ttk.Label(panel, text="Rok od:").pack(side="left", padx=(20, 0))
        self.rok_od_var = tk.IntVar(value=2010)
        ttk.Entry(panel, width=8, textvariable=self.rok_od_var).pack(side="left", padx=5)

        ttk.Label(panel, text="Rok do:").pack(side="left")
        self.rok_do_var = tk.IntVar(value=2023)
        ttk.Entry(panel, width=8, textvariable=self.rok_do_var).pack(side="left", padx=5)

        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(side="top", fill="x")

        przyciski = [
            ("Analiza 1", self.uruchom_analize_1),
            ("Analiza 2", self.uruchom_analize_2),
            ("Analiza 3", self.uruchom_analize_3),
            ("Analiza 4", self.uruchom_analize_4),
            ("Analiza 5", self.uruchom_analize_5),
            ("Analiza 6", self.uruchom_analize_6),
            ("Analiza 7", self.uruchom_analize_7),
        ]
        for tekst, cmd in przyciski:
            ttk.Button(btn_frame, text=tekst, command=cmd).pack(side="left", padx=4, pady=4)

        self.status_var = tk.StringVar(value="Gotowe. Wybierz analizę.")
        ttk.Label(self, textvariable=self.status_var, padding=(10, 0)).pack(side="top", anchor="w")

        self.wykres_frame = ttk.Frame(self, padding=10)
        self.wykres_frame.pack(side="top", fill="both", expand=True)

    def _pokaz_figure(self, fig) -> None:
        if self.canvas_plot is not None:
            self.canvas_plot.get_tk_widget().destroy()
        self.canvas_plot = FigureCanvasTkAgg(fig, master=self.wykres_frame)
        self.canvas_plot.draw()
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True)

    def _bezpiecznie(self, nazwa: str, funkcja):
        try:
            self.status_var.set(f"Uruchamiam: {nazwa}...")
            self.update_idletasks()
            funkcja()
            self.status_var.set(f"Zakończono: {nazwa}")
        except Exception as exc:
            self.status_var.set("Błąd podczas analizy")
            messagebox.showerror("Błąd", str(exc))

    def uruchom_analize_1(self) -> None:
        def _run():
            rok = self.rok_var.get()
            df = self.analizator.analiza_1_bezrobocie_w_wojewodztwach(rok=rok)
            fig = wykres_analiza_1(df, rok=rok)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 1", _run)

    def uruchom_analize_2(self) -> None:
        def _run():
            rok_od = self.rok_od_var.get()
            rok_do = self.rok_do_var.get()
            df = self.analizator.analiza_2_trend_bezrobocia(rok_od=rok_od, rok_do=rok_do)
            fig = wykres_analiza_2(df)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 2", _run)

    def uruchom_analize_3(self) -> None:
        def _run():
            rok = self.rok_var.get()
            df = self.analizator.analiza_3_bezrobotni_wg_wyksztalcenia(rok=rok)
            fig = wykres_analiza_3(df, rok=rok)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 3", _run)

    def uruchom_analize_4(self) -> None:
        def _run():
            rok = self.rok_var.get()
            df = self.analizator.analiza_4_bezrobotni_wg_plci(rok=rok)
            fig = wykres_analiza_4(df, rok=rok)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 4", _run)

    def uruchom_analize_5(self) -> None:
        def _run():
            df = self.analizator.analiza_5_wplyw_covid()
            fig = wykres_analiza_5(df)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 5", _run)

    def uruchom_analize_6(self) -> None:
        def _run():
            rok = self.rok_var.get()
            df = self.analizator.analiza_6_mlodzi_vs_dlugo(rok=rok)
            fig = wykres_analiza_6(df, rok=rok)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 6", _run)

    def uruchom_analize_7(self) -> None:
        def _run():
            rok = self.rok_var.get()
            df = self.analizator.analiza_7_napiecie_rynku(rok=rok)
            fig = wykres_analiza_7(df, rok=rok)
            self._pokaz_figure(fig)

        self._bezpiecznie("Analiza 7", _run)


def uruchom_gui() -> None:
    app = AplikacjaRynkuPracy()
    app.mainloop()
