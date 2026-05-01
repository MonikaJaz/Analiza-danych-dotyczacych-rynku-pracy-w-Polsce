# Analiza danych dotyczacych rynku pracy w Polsce

Projekt studencki w Pythonie. Aktualny etap projektu zawiera czysta strukture aplikacji, warstwe API do dynamicznego pobierania danych z Banku Danych Lokalnych GUS oraz prosty interfejs `tkinter` do sprawdzenia danych.

Analizy i wizualizacje zostana dodane dopiero po wyborze konkretnych pytan badawczych.

## Wymagane biblioteki

- `pandas`
- `requests`
- `python-dotenv`
- `tkinter` (zwykle wbudowany w Pythona)

## Konfiguracja klucza API

1. Utworz plik `.env` w katalogu glownym.
2. Dodaj:

```env
GUS_API_KEY=twoj_klucz_api
```

Klucz nie jest wymagany dla wszystkich endpointow, ale jest zalecany.

## Uruchomienie aplikacji

```powershell
python main.py
```

## Struktura projektu

- `src/api.py` - komunikacja z API GUS BDL i zamiana odpowiedzi na `DataFrame`
- `src/gui.py` - podstawowy interfejs `tkinter` do pobierania tematow i zmiennych
- `scripts/debug_api.py` - skrypt pomocniczy do szybkiego sprawdzenia API
- `main.py` - punkt startowy aplikacji

## Warstwa API

Modul `src/api.py` udostepnia funkcje:

- `pobierz_tematy()` - pobiera tematy/kategorie danych BDL
- `pobierz_zmienne(id_tematu)` - pobiera wskazniki dla wybranego tematu
- `pobierz_dane_wskaznika(id_zmiennej, rok_od, rok_do, poziom_jednostki)` - pobiera wartosci wskaznika
- `pobierz_jednostki(poziom)` - pobiera jednostki terytorialne

## Uwagi

- Aplikacja pobiera dane dynamicznie z internetu.
- Na tym etapie nie ma jeszcze docelowych analiz ani wykresow.
- Kolejny krok to wybor 2-4 konkretnych pytan analitycznych i dopiero potem dodanie modulow `analysis.py` oraz `visualization.py`.
