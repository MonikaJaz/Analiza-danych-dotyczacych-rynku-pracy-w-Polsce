# Analiza danych dotyczących rynku pracy w Polsce

Projekt studencki w Pythonie: dynamiczne pobieranie danych z API GUS BDL, analiza w `pandas`, wizualizacje w `matplotlib` oraz interfejs graficzny w `tkinter`.

## Wymagane biblioteki

- `pandas`
- `requests`
- `python-dotenv`
- `matplotlib`
- `tkinter` (zwykle wbudowany w Pythona)

## Konfiguracja klucza API

1. Utwórz plik `.env` w katalogu głównym.
2. Dodaj:

```env
GUS_API_KEY=twoj_klucz_api
```

Klucz nie jest wymagany dla wszystkich endpointów, ale jest zalecany.

## Uruchomienie aplikacji

```bash
python main.py
```

## Struktura projektu

- `src/api.py` - komunikacja z API GUS
- `src/analysis.py` - logika 7 analiz danych
- `src/visualization.py` - wykresy `matplotlib`
- `src/gui.py` - interfejs `tkinter`
- `main.py` - punkt startowy aplikacji

## Zakres analiz

### 4 podstawowe

1. Bezrobocie w województwach (wykres słupkowy)
2. Trend bezrobocia w czasie 2010-2023 (wykres liniowy)
3. Bezrobotni według wykształcenia
4. Bezrobotni według płci w województwach

### 3 nieoczywiste

5. Wpływ COVID-19 na rynek pracy (porównanie 2019/2020/2021)
6. Młodzi/krótkotrwale bezrobotni vs długotrwale bezrobotni
7. Oferty pracy vs liczba bezrobotnych (bezrobotni na 1 ofertę pracy)

## Uwagi

- Aplikacja pobiera dane dynamicznie z internetu.
- Część wskaźników jest dobierana automatycznie po słowach kluczowych z metadanych API, aby utrzymać prostą i czytelną implementację.