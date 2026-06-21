"""Zakładka Mapa – kartogram województw (stopa bezrobocia / wynagrodzenia / napięcie rynku pracy)."""

import threading
import tkinter as tk
from tkinter import messagebox

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon
import pandas as pd

from .config import KOLORY
from .utils import wyczysc, osadz_figure, normalizuj_nazwe, wczytaj_geojson, pole_pierscienia, srodek_pierscienia
from .api import GusApiError, WOJEWODZTWA, pobierz_mape_stopy_bezrobocia, pobierz_mape_wynagrodzen, pobierz_napiecie_rynku


def uruchom(app) -> None:
    rok = app.rok_mapy_var.get()
    typ = app.typ_mapy_var.get()
    app.status_var.set(f"Mapa: {typ} ({rok})…")
    app.update_idletasks()
    wyczysc(app.tab_mapa)

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
            app.after(0, lambda: rysuj(app, df, tytul, kolor))
            app.after(0, lambda: app.status_var.set("Gotowe."))
        except GusApiError as e:
            app.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
            app.after(0, lambda: app.status_var.set(f"Błąd: {e}"))

    threading.Thread(target=zadanie, daemon=True).start()


def rysuj(app, df: pd.DataFrame, tytul: str, kolor_bazy: str) -> None:
    wyczysc(app.tab_mapa)

    df = df.dropna(subset=["wartosc"]).copy()
    df = df[df["jednostka"].isin(WOJEWODZTWA.values())].copy()
    df = df.sort_values("wartosc", ascending=True).reset_index(drop=True)

    if df.empty:
        tk.Label(app.tab_mapa, text="Brak danych dla wybranych parametrów.",
                 bg=KOLORY["obszar"], fg=KOLORY["tekst2"],
                 font=("Segoe UI", 12)).pack(pady=40)
        return

    geojson = wczytaj_geojson()
    df["klucz_wojew"] = df["jednostka"].map(normalizuj_nazwe)
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
        klucz = normalizuj_nazwe(nazwa)
        wartosc = wartosci.get(klucz)
        geometria = cecha["geometry"]
        wielokaty = (geometria["coordinates"] if geometria["type"] == "MultiPolygon"
                     else [geometria["coordinates"]])
        najwiekszy_pierscien = None
        najwieksze_pole = -1.0

        for wielokat in wielokaty:
            pierscien = wielokat[0]
            xs = [p[0] for p in pierscien]
            ys = [p[1] for p in pierscien]
            min_x, max_x = min(min_x, min(xs)), max(max_x, max(xs))
            min_y, max_y = min(min_y, min(ys)), max(max_y, max(ys))

            p = pole_pierscienia(pierscien)
            if p > najwieksze_pole:
                najwieksze_pole = p
                najwiekszy_pierscien = pierscien

            kolor = cmap(norma(wartosc)) if wartosc is not None else KOLORY["panel2"]
            ax.add_patch(Polygon(pierscien, closed=True, facecolor=kolor,
                                 edgecolor=KOLORY["bialy"], linewidth=1.2, joinstyle="round"))

        if najwiekszy_pierscien is not None:
            x, y = srodek_pierscienia(najwiekszy_pierscien)
            if wartosc is None:
                tekst = f"{nazwa.title()}\nbrak"
            elif jednostka == "PLN":
                tekst = f"{nazwa.title()}\n{wartosc:,.0f}".replace(",", " ")
            elif jednostka == "%":
                tekst = f"{nazwa.title()}\n{wartosc:.1f}%"
            else:
                tekst = f"{nazwa.title()}\n{wartosc:.1f}"
            ax.text(x, y, tekst, ha="center", va="center",
                    fontsize=6.5, color=KOLORY["tekst"], fontweight="semibold")

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
    osadz_figure(fig, app.tab_mapa)
