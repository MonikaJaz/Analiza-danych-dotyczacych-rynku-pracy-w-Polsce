"""Moduł analiz danych rynku pracy oparty na API GUS BDL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .api import pobierz_dane_wskaznika, pobierz_jednostki, pobierz_zmienne


SUBJECT_BEZROBOCIE = "P1364"
SUBJECT_WYKSZTALCENIE = "P1947"
SUBJECT_CZAS_BEZ_PRACY = "P1948"
SUBJECT_OFERTY_PRACY = "P1365"


@dataclass
class VariableMeta:
    """Podstawowe informacje o wskaźniku z API."""

    id: str
    nazwa: str


class AnalizatorRynkuPracy:
    """Prosty serwis do pobierania i przetwarzania danych."""

    def __init__(self) -> None:
        self._cache_zmiennych: dict[str, pd.DataFrame] = {}
        self._cache_wojewodztw: pd.DataFrame | None = None

    def _zmienne(self, subject_id: str) -> pd.DataFrame:
        if subject_id not in self._cache_zmiennych:
            df = pobierz_zmienne(subject_id)
            if df.empty:
                raise ValueError(f"Brak zmiennych dla kategorii {subject_id}.")
            self._cache_zmiennych[subject_id] = df
        return self._cache_zmiennych[subject_id]

    def _wojewodztwa(self) -> pd.DataFrame:
        if self._cache_wojewodztw is None:
            woj = pobierz_jednostki(poziom=2)
            if woj.empty:
                raise ValueError("Nie udało się pobrać listy województw.")
            self._cache_wojewodztw = woj[["id", "name"]].rename(
                columns={"id": "id_jednostki", "name": "wojewodztwo"}
            )
        return self._cache_wojewodztw

    @staticmethod
    def _kolumna_nazwy_zmiennej(df: pd.DataFrame) -> pd.Series:
        czesci = []
        for kol in ("name", "n1", "n2", "n3"):
            if kol in df.columns:
                czesci.append(df[kol].fillna("").astype(str))
        if not czesci:
            return pd.Series([""] * len(df), index=df.index)
        wynik = czesci[0]
        for kol in czesci[1:]:
            wynik = wynik + " " + kol
        return wynik.str.strip().str.lower()

    def znajdz_wskaznik(
        self,
        subject_id: str,
        wymagane_slowa: Iterable[str],
        preferowane_slowa: Iterable[str] | None = None,
    ) -> VariableMeta:
        """Znajduje wskaźnik po słowach kluczowych w opisie."""
        df = self._zmienne(subject_id).copy()
        df["full_name"] = self._kolumna_nazwy_zmiennej(df)

        wymagane = [s.lower() for s in wymagane_slowa]
        for slowo in wymagane:
            df = df[df["full_name"].str.contains(slowo, na=False)]

        if df.empty:
            raise ValueError(
                f"Nie znaleziono wskaźnika dla {subject_id} i słów: {list(wymagane_slowa)}"
            )

        if preferowane_slowa:
            pref = [s.lower() for s in preferowane_slowa]
            ranking = pd.Series(0, index=df.index, dtype="int64")
            for slowo in pref:
                ranking += df["full_name"].str.contains(slowo, na=False).astype(int)
            df = df.assign(rank=ranking).sort_values(["rank", "id"], ascending=[False, True])
        else:
            df = df.sort_values("id")

        rekord = df.iloc[0]
        return VariableMeta(id=str(rekord["id"]), nazwa=str(rekord.get("full_name", "")))

    @staticmethod
    def _ostatni_rok(df: pd.DataFrame) -> int:
        if df.empty:
            raise ValueError("Brak danych do wyznaczenia ostatniego roku.")
        return int(df["rok"].max())

    def analiza_1_bezrobocie_w_wojewodztwach(self, rok: int) -> pd.DataFrame:
        """Porównanie bezrobotnych w 16 województwach (rok)."""
        wsk = self.znajdz_wskaznik(
            SUBJECT_BEZROBOCIE,
            wymagane_slowa=["bezrobot"],
            preferowane_slowa=["ogółem", "ogolem", "ogol"],
        )
        df = pobierz_dane_wskaznika(wsk.id, rok, rok, poziom_jednostki=2)
        if df.empty:
            raise ValueError("Brak danych dla analizy 1.")

        woj = self._wojewodztwa()
        wynik = df.merge(woj, on="id_jednostki", how="left")
        wynik = wynik.groupby("wojewodztwo", as_index=False)["wartosc"].sum()
        return wynik.sort_values("wartosc", ascending=False)

    def analiza_2_trend_bezrobocia(self, rok_od: int = 2010, rok_do: int = 2023) -> pd.DataFrame:
        """Trend bezrobocia w czasie, suma województw jako Polska."""
        wsk = self.znajdz_wskaznik(
            SUBJECT_BEZROBOCIE,
            wymagane_slowa=["bezrobot"],
            preferowane_slowa=["ogółem", "ogolem", "ogol"],
        )
        df = pobierz_dane_wskaznika(wsk.id, rok_od, rok_do, poziom_jednostki=2)
        if df.empty:
            raise ValueError("Brak danych dla analizy 2.")
        wynik = df.groupby("rok", as_index=False)["wartosc"].sum()
        return wynik.sort_values("rok")

    def analiza_3_bezrobotni_wg_wyksztalcenia(
        self, rok: int | None = None, rok_od: int = 2010, rok_do: int = 2023
    ) -> pd.DataFrame:
        """Bezrobotni według poziomu wykształcenia (Polska)."""
        zmienne = self._zmienne(SUBJECT_WYKSZTALCENIE).copy()
        zmienne["full_name"] = self._kolumna_nazwy_zmiennej(zmienne)

        if rok is None:
            probe = pobierz_dane_wskaznika(str(zmienne.iloc[0]["id"]), rok_od, rok_do, poziom_jednostki=2)
            rok = self._ostatni_rok(probe)

        wyniki = []
        for _, row in zmienne.iterrows():
            var_id = str(row["id"])
            nazwa = str(row["full_name"])
            df = pobierz_dane_wskaznika(var_id, rok, rok, poziom_jednostki=2)
            if df.empty:
                continue
            wartosc = df["wartosc"].sum()
            wyniki.append({"kategoria": nazwa, "wartosc": wartosc})

        if not wyniki:
            raise ValueError("Brak danych dla analizy 3.")
        wynik = pd.DataFrame(wyniki).sort_values("wartosc", ascending=False)
        return wynik

    def analiza_4_bezrobotni_wg_plci(self, rok: int) -> pd.DataFrame:
        """Porównanie kobiet i mężczyzn w każdym województwie."""
        wsk_k = self.znajdz_wskaznik(
            SUBJECT_BEZROBOCIE, wymagane_slowa=["kobiet"], preferowane_slowa=["bezrobot"]
        )
        wsk_m = self.znajdz_wskaznik(
            SUBJECT_BEZROBOCIE, wymagane_slowa=["mężczyzn"], preferowane_slowa=["bezrobot"]
        )

        df_k = pobierz_dane_wskaznika(wsk_k.id, rok, rok, poziom_jednostki=2)
        df_m = pobierz_dane_wskaznika(wsk_m.id, rok, rok, poziom_jednostki=2)
        if df_k.empty or df_m.empty:
            raise ValueError("Brak danych dla analizy 4.")

        woj = self._wojewodztwa()
        k = df_k.merge(woj, on="id_jednostki", how="left").groupby("wojewodztwo", as_index=False)["wartosc"].sum()
        m = df_m.merge(woj, on="id_jednostki", how="left").groupby("wojewodztwo", as_index=False)["wartosc"].sum()
        wynik = k.merge(m, on="wojewodztwo", suffixes=("_kobiety", "_mezczyzni"))
        return wynik.sort_values("wojewodztwo")

    def analiza_5_wplyw_covid(self) -> pd.DataFrame:
        """Zmiana bezrobocia 2019->2021 oraz porównanie 2019/2020/2021."""
        wsk = self.znajdz_wskaznik(
            SUBJECT_BEZROBOCIE,
            wymagane_slowa=["bezrobot"],
            preferowane_slowa=["ogółem", "ogolem", "ogol"],
        )
        df = pobierz_dane_wskaznika(wsk.id, 2019, 2021, poziom_jednostki=2)
        if df.empty:
            raise ValueError("Brak danych dla analizy 5.")

        woj = self._wojewodztwa()
        base = df.merge(woj, on="id_jednostki", how="left")
        pivot = base.pivot_table(index="wojewodztwo", columns="rok", values="wartosc", aggfunc="sum").fillna(0)
        for kol in (2019, 2020, 2021):
            if kol not in pivot.columns:
                pivot[kol] = 0.0
        pivot["zmiana_2019_2021"] = pivot[2021] - pivot[2019]
        pivot["zmiana_proc_2019_2021"] = ((pivot[2021] - pivot[2019]) / pivot[2019].replace(0, pd.NA)) * 100
        wynik = pivot.reset_index()
        return wynik.sort_values("zmiana_2019_2021", ascending=False)

    def analiza_6_mlodzi_vs_dlugo(self, rok: int = 2023) -> pd.DataFrame:
        """Młodzi/absolwenci vs długotrwale bezrobotni."""
        wsk_mlodzi = self.znajdz_wskaznik(
            SUBJECT_CZAS_BEZ_PRACY,
            wymagane_slowa=["do 1"],
            preferowane_slowa=["miesią", "miesiac", "krótk", "krotk"],
        )
        wsk_dlugo = self.znajdz_wskaznik(
            SUBJECT_CZAS_BEZ_PRACY,
            wymagane_slowa=["24", "więcej"],
            preferowane_slowa=["miesią", "miesiac", "i więcej", "i wiecej"],
        )

        df_mlodzi = pobierz_dane_wskaznika(wsk_mlodzi.id, rok, rok, poziom_jednostki=2)
        df_dlugo = pobierz_dane_wskaznika(wsk_dlugo.id, rok, rok, poziom_jednostki=2)
        if df_mlodzi.empty or df_dlugo.empty:
            raise ValueError("Brak danych dla analizy 6.")

        mlodzi = df_mlodzi["wartosc"].sum()
        dlugo = df_dlugo["wartosc"].sum()
        wynik = pd.DataFrame(
            [
                {"kategoria": "Krótko bez pracy (do 1 mies.)", "wartosc": mlodzi},
                {"kategoria": "Długotrwale bezrobotni (24+ mies.)", "wartosc": dlugo},
            ]
        )
        return wynik

    def analiza_7_napiecie_rynku(self, rok: int) -> pd.DataFrame:
        """Wskaźnik napięcia rynku: bezrobotni na 1 ofertę pracy."""
        wsk_bezrobocie = self.znajdz_wskaznik(
            SUBJECT_BEZROBOCIE,
            wymagane_slowa=["bezrobot"],
            preferowane_slowa=["ogółem", "ogolem", "ogol"],
        )
        wsk_oferty = self.znajdz_wskaznik(
            SUBJECT_OFERTY_PRACY,
            wymagane_slowa=["ofert"],
            preferowane_slowa=["pracy", "ogółem", "ogolem", "ogol"],
        )

        df_b = pobierz_dane_wskaznika(wsk_bezrobocie.id, rok, rok, poziom_jednostki=2)
        df_o = pobierz_dane_wskaznika(wsk_oferty.id, rok, rok, poziom_jednostki=2)
        if df_b.empty or df_o.empty:
            raise ValueError("Brak danych dla analizy 7.")

        woj = self._wojewodztwa()
        b = df_b.merge(woj, on="id_jednostki", how="left").groupby("wojewodztwo", as_index=False)["wartosc"].sum()
        o = df_o.merge(woj, on="id_jednostki", how="left").groupby("wojewodztwo", as_index=False)["wartosc"].sum()
        wynik = b.merge(o, on="wojewodztwo", suffixes=("_bezrobotni", "_oferty"))
        wynik["bezrobotni_na_oferte"] = wynik["wartosc_bezrobotni"] / wynik["wartosc_oferty"].replace(0, pd.NA)
        return wynik.sort_values("bezrobotni_na_oferte", ascending=False)
