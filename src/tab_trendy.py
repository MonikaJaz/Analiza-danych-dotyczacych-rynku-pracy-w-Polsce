"""Zakładka Trendy – wykresy liniowe bezrobocia, stopy bezrobocia, wynagrodzeń i ofert pracy w czasie."""

import threading
from tkinter import messagebox

import numpy as np
import matplotlib.pyplot as plt

from .config import KOLORY
from .utils import wyczysc, osadz_figure
from .api import (
    GusApiError,
    pobierz_trend_bezrobocia_plec,
    pobierz_trend_stopy_bezrobocia,
    pobierz_trend_wynagrodzen,
    pobierz_trend_ofert_pracy,
)


def uruchom(app) -> None:
    rok_od = app.rok_od_var.get()
    rok_do = app.rok_do_var.get()
    if rok_od > rok_do:
        messagebox.showwarning("Filtry", "'Rok od' nie może być większy niż 'Rok do'.")
        return
    app.status_var.set(f"Trendy {rok_od}–{rok_do}…")
    app.update_idletasks()
    wyczysc(app.tab_trendy)
    widok = app.plec_trend_var.get()

    def zadanie() -> None:
        try:
            df_plec   = pobierz_trend_bezrobocia_plec(rok_od, rok_do)
            df_stopa  = pobierz_trend_stopy_bezrobocia(rok_od, rok_do)
            df_wyn    = pobierz_trend_wynagrodzen(rok_od, rok_do)
            df_oferty = pobierz_trend_ofert_pracy(rok_od, rok_do)
            app.after(0, lambda: rysuj(app, df_plec, df_stopa, df_wyn, df_oferty, widok))
            app.after(0, lambda: app.status_var.set("Gotowe."))
        except GusApiError as e:
            app.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
            app.after(0, lambda: app.status_var.set(f"Błąd: {e}"))

    threading.Thread(target=zadanie, daemon=True).start()


def linia_trendu(lata, wartosci):
    """Liczy linię regresji liniowej (numpy.polyfit) dla wskazanych lat i wartości."""
    a, b = np.polyfit(lata, wartosci, 1)
    return a * lata + b


def rysuj(app, df_plec, df_stopa, df_wyn, df_oferty, widok) -> None:
    wyczysc(app.tab_trendy)
    fig, axs = plt.subplots(2, 2, figsize=(13, 8))
    fig.tight_layout(pad=3.5, h_pad=5.0, w_pad=3.0)

    ax = axs[0, 0]
    ax.set_title("Liczba bezrobotnych wg płci")
    kolumny_mapa = {
        "Ogółem + płcie": ["Ogółem", "Kobiety", "Mężczyźni"],
        "Tylko kobiety":  ["Kobiety"],
        "Tylko mężczyźni": ["Mężczyźni"],
        "Ogółem":         ["Ogółem"],
    }
    kolumny = [k for k in kolumny_mapa.get(widok, ["Ogółem"]) if k in df_plec.columns]
    kolory = [KOLORY["panel_ciemny"], KOLORY["akcent2"], KOLORY["akcent3"]]
    for i, kol in enumerate(kolumny):
        ax.plot(df_plec["rok"], df_plec[kol] / 1000, marker="o", markersize=4,
                color=kolory[i % len(kolory)], linewidth=2, label=kol)
    ax.set_ylabel("Liczba bezrobotnych [tys.]")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.4)

    ax = axs[0, 1]
    ax.set_title("Stopa bezrobocia rejestrowanego [%]")
    if not df_stopa.empty:
        ax.fill_between(df_stopa["rok"], df_stopa["wartosc"], alpha=0.2, color=KOLORY["akcent2"])
        ax.plot(df_stopa["rok"], df_stopa["wartosc"], color=KOLORY["akcent2"],
                linewidth=2.5, marker="o", markersize=4)
        if len(df_stopa) >= 2:
            trend = linia_trendu(df_stopa["rok"].to_numpy(), df_stopa["wartosc"].to_numpy())
            ax.plot(df_stopa["rok"], trend, "--", color=KOLORY["tekst2"],
                    linewidth=1.3, label="Trend (regresja liniowa)")
            ax.legend(fontsize=7)
        if 2020 in df_stopa["rok"].values:
            val = df_stopa.loc[df_stopa["rok"] == 2020, "wartosc"].values[0]
            ax.annotate("COVID-19", xy=(2020, val), xytext=(2020 - 1.5, val + 1.5),
                        arrowprops=dict(arrowstyle="->", color=KOLORY["akcent3"]),
                        color=KOLORY["akcent3"], fontsize=8)
    ax.set_ylabel("Stopa [%]")
    ax.grid(True, alpha=0.4)

    ax = axs[1, 0]
    ax.set_title("Przeciętne miesięczne wynagrodzenie brutto [PLN]")
    if not df_wyn.empty:
        ax.fill_between(df_wyn["rok"], df_wyn["wartosc"], alpha=0.2, color=KOLORY["akcent4"])
        ax.plot(df_wyn["rok"], df_wyn["wartosc"], color=KOLORY["akcent4"],
                linewidth=2.5, marker="s", markersize=4)
        if len(df_wyn) >= 2:
            trend = linia_trendu(df_wyn["rok"].to_numpy(), df_wyn["wartosc"].to_numpy())
            ax.plot(df_wyn["rok"], trend, "--", color=KOLORY["tekst2"],
                    linewidth=1.3, label="Trend (regresja liniowa)")
            ax.legend(fontsize=7)
    ax.set_xlabel("Rok")
    ax.set_ylabel("PLN")
    ax.grid(True, alpha=0.4)

    ax = axs[1, 1]
    ax.set_title("Liczba ofert pracy")
    if not df_oferty.empty:
        ax.bar(df_oferty["rok"], df_oferty["wartosc"] / 1000,
               color=KOLORY["akcent5"], alpha=0.85, width=0.7)
        ax.set_xticks(df_oferty["rok"])
        ax.tick_params(axis="x", rotation=45)
    ax.set_xlabel("Rok")
    ax.set_ylabel("Oferty [tys.]")
    ax.grid(True, alpha=0.4, axis="y")

    osadz_figure(fig, app.tab_trendy)
