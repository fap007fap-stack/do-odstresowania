# Saperka vs Kurierzy+ — wersja bez IP

## Zmiany

- Nie używa IP.
- Użytkownik musi wpisać nick na wejściu.
- Ranking zapisuje wynik pod nickiem.
- Zostają dodatki:
  - combo,
  - power-upy,
  - boss,
  - rankingi dzienny/tygodniowy/all-time.
- Dodana ukryta edycja wyniku:
  - przytrzymaj `P` przez 3 sekundy,
  - wpisz nowy wynik,
  - wynik zapisze się po końcu rundy.

## Jak wrzucić na Streamlit

Wrzuć do GitHuba:
- `app.py`
- `requirements.txt`

Potem w Streamlit Cloud zrób Reboot/Redeploy.

Nie musisz wrzucać folderu `frontend`, bo `app.py` tworzy go automatycznie.
