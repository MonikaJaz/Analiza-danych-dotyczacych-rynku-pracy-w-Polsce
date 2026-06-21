"""Kolory i stałe współdzielone przez wszystkie moduły aplikacji."""

from pathlib import Path

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
SCIEZKA_GEOJSON = Path(__file__).resolve().parents[1] / "assets" / "wojewodztwa.geojson"
