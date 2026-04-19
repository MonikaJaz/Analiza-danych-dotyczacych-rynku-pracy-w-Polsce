"""Wizualizacje matplotlib dla analiz rynku pracy."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd


def _nowa_figura() -> Figure:
    fig, _ = plt.subplots(figsize=(10, 5))
    return fig


def wykres_analiza_1(df: pd.DataFrame, rok: int) -> Figure:
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(df["wojewodztwo"], df["wartosc"], color="#4E79A7")
    ax.set_title(f"Analiza 1: Bezrobotni w województwach ({rok})")
    ax.set_xlabel("Województwo")
    ax.set_ylabel("Liczba bezrobotnych")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def wykres_analiza_2(df: pd.DataFrame) -> Figure:
    fig = _nowa_figura()
    ax = fig.axes[0]
    ax.plot(df["rok"], df["wartosc"], marker="o", color="#E15759")
    ax.set_title("Analiza 2: Trend bezrobocia (2010-2023)")
    ax.set_xlabel("Rok")
    ax.set_ylabel("Liczba bezrobotnych")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def wykres_analiza_3(df: pd.DataFrame, rok: int) -> Figure:
    fig = _nowa_figura()
    ax = fig.axes[0]
    ax.barh(df["kategoria"], df["wartosc"], color="#76B7B2")
    ax.set_title(f"Analiza 3: Bezrobotni według wykształcenia ({rok})")
    ax.set_xlabel("Liczba bezrobotnych")
    ax.set_ylabel("Kategoria")
    fig.tight_layout()
    return fig


def wykres_analiza_4(df: pd.DataFrame, rok: int) -> Figure:
    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(df))
    szerokosc = 0.4
    ax.bar([i - szerokosc / 2 for i in x], df["wartosc_kobiety"], width=szerokosc, label="Kobiety")
    ax.bar([i + szerokosc / 2 for i in x], df["wartosc_mezczyzni"], width=szerokosc, label="Mężczyźni")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["wojewodztwo"], rotation=45, ha="right")
    ax.set_title(f"Analiza 4: Bezrobotni wg płci ({rok})")
    ax.set_xlabel("Województwo")
    ax.set_ylabel("Liczba bezrobotnych")
    ax.legend()
    fig.tight_layout()
    return fig


def wykres_analiza_5(df: pd.DataFrame) -> Figure:
    fig = _nowa_figura()
    ax = fig.axes[0]
    top = df.head(10)
    ax.bar(top["wojewodztwo"], top["zmiana_2019_2021"], color="#F28E2B")
    ax.set_title("Analiza 5: Największy wzrost bezrobocia po COVID (2019->2021)")
    ax.set_xlabel("Województwo")
    ax.set_ylabel("Zmiana liczby bezrobotnych")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def wykres_analiza_6(df: pd.DataFrame, rok: int) -> Figure:
    fig = _nowa_figura()
    ax = fig.axes[0]
    ax.bar(df["kategoria"], df["wartosc"], color=["#59A14F", "#EDC948"])
    ax.set_title(f"Analiza 6: Młodzi vs długotrwale bezrobotni ({rok})")
    ax.set_xlabel("Kategoria")
    ax.set_ylabel("Liczba osób")
    ax.tick_params(axis="x", rotation=12)
    fig.tight_layout()
    return fig


def wykres_analiza_7(df: pd.DataFrame, rok: int) -> Figure:
    fig = _nowa_figura()
    ax = fig.axes[0]
    top = df.dropna(subset=["bezrobotni_na_oferte"]).head(16)
    ax.barh(top["wojewodztwo"], top["bezrobotni_na_oferte"], color="#B07AA1")
    ax.set_title(f"Analiza 7: Bezrobotni na 1 ofertę pracy ({rok})")
    ax.set_xlabel("Bezrobotni / oferta")
    ax.set_ylabel("Województwo")
    fig.tight_layout()
    return fig
