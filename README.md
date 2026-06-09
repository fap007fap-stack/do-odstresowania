# Saperka vs Kurierzy+ — Streamlit

## Dodane w tej wersji

- Automatyczne przypisywanie nicku po IP.
- Formularz nicku pokazuje się tylko przy pierwszym wejściu z danego IP.
- Combo i mnożnik punktów.
- Power-upy:
  - BIG — większa saperka,
  - x3 — potrójny rzut,
  - SLOW — wolniejsze auta,
  - BOOM — czyści ekran,
  - +❤ — dodatkowe życie.
- Boss „MEGA KURIER”.
- Poczta Polska ma 2 HP.
- InPost lekko robi uniki.
- Ranking:
  - dzisiejszy,
  - tygodniowy,
  - all-time.
- Zapisywane statystyki:
  - wynik,
  - max combo,
  - pokonane bossy,
  - trafienia DPD.

## Jak wrzucić na Streamlit

1. Wrzuć do repozytorium:
   - `app.py`
   - `requirements.txt`
2. Zrób commit i push.
3. W Streamlit Cloud ustaw start file jako `app.py`.
4. Kliknij Deploy/Reboot.

`app.py` sam tworzy folder `frontend`, więc nie musisz go wrzucać osobno.

## Sekret do hashowania IP

W Streamlit Cloud → Settings → Secrets możesz dodać:

```toml
IP_HASH_SALT = "tu-wpisz-dlugi-losowy-sekret"
```

## Uwaga o trwałości rankingu

Ta wersja używa SQLite. Na darmowym Streamlit Cloud ranking może zniknąć po restarcie/redeployu. Do rankingu „na serio” najlepiej podłączyć Supabase, Neon albo inny Postgres.
