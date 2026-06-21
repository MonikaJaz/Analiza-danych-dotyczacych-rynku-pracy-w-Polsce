"""Funkcje pomocnicze: rysowanie wykresów, GeoJSON, formatowanie liczb i nazw."""

import json
import unicodedata

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

from .config import KOLORY, SCIEZKA_GEOJSON


def styl_matplotlib() -> None:
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


def wyczysc(frame: tk.Frame) -> None:
    for w in frame.winfo_children():
        w.destroy()


def osadz_figure(fig: plt.Figure, rodzic: tk.Widget) -> None:
    canvas = FigureCanvasTkAgg(fig, master=rodzic)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


def normalizuj_nazwe(nazwa: str) -> str:
    bez_znakow = unicodedata.normalize("NFKD", nazwa)
    bez_znakow = "".join(z for z in bez_znakow if not unicodedata.combining(z))
    return bez_znakow.upper().strip()


def wczytaj_geojson() -> dict:
    with open(SCIEZKA_GEOJSON, encoding="utf-8") as f:
        return json.load(f)


def pole_pierscienia(pierscien: list) -> float:
    pole = 0.0
    for i in range(len(pierscien) - 1):
        x1, y1 = pierscien[i]
        x2, y2 = pierscien[i + 1]
        pole += x1 * y2 - x2 * y1
    return abs(pole) / 2


def srodek_pierscienia(pierscien: list) -> tuple:
    xs = [p[0] for p in pierscien]
    ys = [p[1] for p in pierscien]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def formatuj_liczbe(v) -> str:
    if isinstance(v, str):
        return v
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} mln"
    if v >= 1_000:
        return f"{v / 1_000:.1f} tys."
    return f"{v:.1f}"
