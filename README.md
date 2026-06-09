# Saperka vs Kurierzy — poprawiona wersja Streamlit

Ta wersja naprawia błąd:

`No such component directory: '/mount/src/.../frontend'`

Nie musisz już osobno pilnować folderu `frontend`, bo `app.py` sam tworzy folder i plik `frontend/index.html` przy starcie aplikacji.

## Jak wdrożyć

1. W repozytorium zostaw/wrzuć te pliki:
   - `app.py`
   - `requirements.txt`
2. Zrób commit i push.
3. W Streamlit Cloud kliknij `Reboot app` albo redeploy.
4. Plik startowy ma być: `app.py`.

## Opcjonalnie: sekret do hashowania IP

W Streamlit Cloud → App settings → Secrets dodaj:

```toml
IP_HASH_SALT = "tu-wpisz-dlugi-losowy-sekret"
```
