# Analiza rynku pracy w Polsce

Interaktywny dashboard do eksploracji danych o rynku pracy w Polsce. Dane pobierane są na bieżąco z API Banku Danych Lokalnych GUS.

## Wymagania

```
pip install -r requirements.txt
```

`tkinter` jest zazwyczaj wbudowany w Pythona – nie wymaga osobnej instalacji.

## Konfiguracja klucza API

Utwórz plik `.env` w katalogu głównym:

```
GUS_API_KEY=twoj_klucz_api
```

Klucz można wygenerować na stronie: https://bdl.stat.gov.pl/api/v1

## Uruchomienie

```
python main.py
```

## Opis dashboardu

Dashboard ma 5 zakładek:

- **Trendy** – wykresy liniowe bezrobocia (ogółem i wg płci), stopy bezrobocia i wynagrodzeń (z linią trendu) oraz ofert pracy w wybranym zakresie lat
- **Mapa** – kartogram województw: stopa bezrobocia, wynagrodzenia lub napięcie rynku pracy
- **Struktura bezrobocia** – wykresy kołowe i słupkowe pokazujące podział wg płci, wykształcenia, wieku i stażu pracy
- **Statystyki** – tabela statystyk opisowych (średnia, mediana, kwartyle, odchylenie std. itp.) dla wybranych wskaźników
- **Dane** – surowe dane w tabeli z możliwością wyboru źródła

Wszystkie filtry (zakres lat, województwo, rodzaj mapy, wybór wskaźników/źródeł) znajdują się w panelu bocznym po lewej stronie. Panel pokazuje tylko filtry odpowiadające aktualnie wybranej zakładce. Po ustawieniu filtrów dane wczytuje się przyciskiem „Pobierz dane”.

## Struktura projektu

```
src/
  api.py           – pobieranie danych z API GUS BDL
  gui.py           – okno główne, nagłówek, pasek KPI, sidebar, notebook
  config.py        – kolory i stałe
  utils.py         – funkcje pomocnicze (wykresy, formatowanie)
  tab_trendy.py    – logika zakładki Trendy
  tab_mapa.py      – logika zakładki Mapa
  tab_struktura.py – logika zakładki Struktura
  tab_statystyki.py – logika zakładki Statystyki
  tab_dane.py      – logika zakładki Dane

assets/
  wojewodztwa.geojson – dane geograficzne do mapy

main.py            – punkt startowy
```

## Źródło danych

Bank Danych Lokalnych GUS – https://bdl.stat.gov.pl/api/v1
