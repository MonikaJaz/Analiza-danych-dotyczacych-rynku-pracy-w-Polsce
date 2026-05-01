"""Podstawowy interfejs tkinter do sprawdzania danych z API GUS BDL."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd

from .api import GusApiError, pobierz_tematy, pobierz_zmienne


class AplikacjaRynkuPracy(tk.Tk):
    """Glowne okno aplikacji na aktualnym etapie projektu."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Rynek pracy w Polsce - dane z API GUS BDL")
        self.geometry("1000x650")

        self.status_var = tk.StringVar(value="Gotowe. Pobierz glowne kategorie albo podtematy.")
        self.id_nadrzedne_var = tk.StringVar(value="")
        self.id_tematu_var = tk.StringVar(value="P1364")

        self._zbuduj_interfejs()

    def _zbuduj_interfejs(self) -> None:
        pasek = ttk.Frame(self, padding=10)
        pasek.pack(side="top", fill="x")

        ttk.Button(pasek, text="Glowne kategorie", command=self.pokaz_glowne_kategorie).pack(
            side="left", padx=(0, 8)
        )

        ttk.Label(pasek, text="ID kategorii/tematu nadrzednego:").pack(side="left")
        ttk.Entry(pasek, width=12, textvariable=self.id_nadrzedne_var).pack(
            side="left", padx=6
        )
        ttk.Button(pasek, text="Pobierz podtematy", command=self.pokaz_podtematy).pack(
            side="left", padx=(0, 16)
        )

        ttk.Label(pasek, text="ID tematu podrzędnego:").pack(side="left")
        ttk.Entry(pasek, width=12, textvariable=self.id_tematu_var).pack(side="left", padx=6)
        ttk.Button(pasek, text="Pobierz zmienne", command=self.pokaz_zmienne).pack(
            side="left", padx=8
        )

        ttk.Label(self, textvariable=self.status_var, padding=(10, 0)).pack(
            side="top", anchor="w"
        )

        tabela_frame = ttk.Frame(self, padding=10)
        tabela_frame.pack(side="top", fill="both", expand=True)

        self.tabela = ttk.Treeview(tabela_frame, show="headings")
        self.tabela.pack(side="left", fill="both", expand=True)

        pasek_y = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        pasek_y.pack(side="right", fill="y")
        self.tabela.configure(yscrollcommand=pasek_y.set)

    def _bezpiecznie(self, opis: str, funkcja) -> None:
        try:
            self.status_var.set(f"Pobieram: {opis}...")
            self.update_idletasks()
            df = funkcja()
            self._pokaz_dataframe(df)
            self.status_var.set(f"Pobrano {len(df)} rekordow: {opis}.")
        except (GusApiError, ValueError) as exc:
            self.status_var.set("Blad pobierania danych.")
            messagebox.showerror("Blad", str(exc))

    def _pokaz_dataframe(self, df: pd.DataFrame) -> None:
        self.tabela.delete(*self.tabela.get_children())

        kolumny = list(df.columns[:8])
        self.tabela["columns"] = kolumny

        for kolumna in kolumny:
            self.tabela.heading(kolumna, text=kolumna)
            self.tabela.column(kolumna, width=140, anchor="w")

        for _, rekord in df.head(200).iterrows():
            wartosci = [rekord.get(kolumna, "") for kolumna in kolumny]
            self.tabela.insert("", "end", values=wartosci)

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
