import threading
from tkinter import messagebox

import matplotlib.pyplot as plt

from .config import KOLORY, PALETA_WYKRESY
from .utils import wyczysc, osadz_figure
from .api import (
    GusApiError,
    pobierz_strukture_plci,
    pobierz_strukture_wyksztalcenia,
    pobierz_strukture_wieku,
    pobierz_strukture_stazu,
)


def uruchom(app) -> None:
    rok = app.rok_str_var.get()
    wojew_nazwa = app.wojew_var.get()
    wojew = None if wojew_nazwa == "Wszystkie" else wojew_nazwa
    app.status_var.set(f"Struktura bezrobocia ({rok})…")
    app.update_idletasks()
    wyczysc(app.tab_struktura)

    def zadanie() -> None:
        try:
            df_plec = pobierz_strukture_plci(rok, wojew)
            df_wyk  = pobierz_strukture_wyksztalcenia(rok, wojew)
            df_wiek = pobierz_strukture_wieku(rok, wojew)
            df_staz = pobierz_strukture_stazu(rok, wojew)
            app.after(0, lambda: rysuj(app, df_plec, df_wyk, df_wiek, df_staz, rok, wojew_nazwa))
            app.after(0, lambda: app.status_var.set("Gotowe."))
        except GusApiError as e:
            app.after(0, lambda: messagebox.showerror("Błąd API", str(e)))
            app.after(0, lambda: app.status_var.set(f"Błąd: {e}"))

    threading.Thread(target=zadanie, daemon=True).start()


def rysuj(app, df_plec, df_wyk, df_wiek, df_staz, rok, wojew_nazwa) -> None:
    wyczysc(app.tab_struktura)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    fig.suptitle(f"Struktura bezrobocia – {wojew_nazwa} – {rok}", fontsize=13)

    if not df_plec.empty and df_plec["liczba"].sum() > 0:
        ax1.pie(
            df_plec["liczba"], labels=df_plec["plec"],
            autopct="%1.1f%%", startangle=90,
            colors=[KOLORY["akcent2"], KOLORY["panel_ciemny"]],
            pctdistance=0.75,
            wedgeprops=dict(linewidth=1.5, edgecolor=KOLORY["bialy"]),
        )
    ax1.set_title("Bezrobotni wg płci", pad=10)

    if not df_wyk.empty and df_wyk["liczba"].sum() > 0:
        df_s = df_wyk.sort_values("liczba")
        bars = ax2.barh(df_s["wyksztalcenie"], df_s["liczba"] / 1000,
                        color=PALETA_WYKRESY[:len(df_s)], height=0.6, edgecolor=KOLORY["linia"])
        for bar, val in zip(bars, df_s["liczba"] / 1000):
            ax2.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                     f"{val:.1f} tys.", va="center", fontsize=7, color=KOLORY["tekst"])
        ax2.grid(True, axis="x", alpha=0.3)
        ax2.tick_params(axis="y", labelsize=8)
    ax2.set_title("Bezrobotni wg wykształcenia", pad=10)

    if not df_wiek.empty and df_wiek["liczba"].sum() > 0:
        ax3.bar(df_wiek["wiek"], df_wiek["liczba"] / 1000,
                color=PALETA_WYKRESY[:len(df_wiek)], edgecolor=KOLORY["linia"], width=0.65)
        ax3.set_ylabel("Liczba [tys.]")
        ax3.tick_params(axis="x", rotation=25, labelsize=8)
        ax3.grid(True, axis="y", alpha=0.3)
    ax3.set_title("Bezrobotni wg grup wiekowych", pad=10)

    if not df_staz.empty and df_staz["liczba"].sum() > 0:
        df_s2 = df_staz.sort_values("liczba")
        bars2 = ax4.barh(df_s2["staz"], df_s2["liczba"] / 1000,
                         color=PALETA_WYKRESY[:len(df_s2)], height=0.6, edgecolor=KOLORY["linia"])
        for bar, val in zip(bars2, df_s2["liczba"] / 1000):
            ax4.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                     f"{val:.1f} tys.", va="center", fontsize=7, color=KOLORY["tekst"])
        ax4.set_xlabel("Liczba [tys.]")
        ax4.grid(True, axis="x", alpha=0.3)
        ax4.tick_params(axis="y", labelsize=8)
    ax4.set_title("Bezrobotni wg stażu pracy", pad=10)

    osadz_figure(fig, app.tab_struktura)
