# Saperka vs Kurierzy — Streamlit z nickiem, IP i rankingiem

## Co jest dodane

- Przy pierwszym wejściu z danego IP użytkownik musi podać nick.
- Aplikacja zapisuje:
  - nick,
  - wynik,
  - datę,
  - hash IP, a nie surowe IP.
- Po zakończeniu gry wynik sam zapisuje się do rankingu.
- DPD daje 20 pkt, reszta daje 10 pkt.

## Pliki

- `app.py` — backend Streamlit, formularz nicku, SQLite, ranking.
- `frontend/index.html` — gra jako własny komponent Streamlit.
- `requirements.txt` — zależności.
- `scores.sqlite3` — utworzy się automatycznie po pierwszym uruchomieniu.

## Uruchomienie lokalnie

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publikacja na Streamlit Community Cloud

1. Załóż repozytorium na GitHubie.
2. Wrzuć do niego:
   - `app.py`
   - folder `frontend`
   - `requirements.txt`
3. Wejdź na Streamlit Community Cloud.
4. Wybierz repozytorium, branch `main`, plik startowy `app.py`.
5. Kliknij Deploy.

## Ważne o trwałości rankingu

Ta wersja używa lokalnego SQLite. To jest OK do testów i prostych wdrożeń, ale na darmowym Streamlit Community Cloud pliki tworzone przez aplikację mogą nie przetrwać restartu/redeployu kontenera.

Jeśli ranking ma być naprawdę trwały, podłącz zewnętrzną bazę:
- Supabase/Postgres,
- Neon,
- Google Sheets,
- Firebase,
- S3/R2.

## Sekret do hashowania IP

W Streamlit Secrets ustaw:

```toml
IP_HASH_SALT = "tu-wpisz-dlugi-losowy-sekret"
```

Bez tego aplikacja też działa, ale lepiej zmienić sekret przed publicznym udostępnieniem.
