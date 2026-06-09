from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "scores.sqlite3"
FRONTEND_DIR = APP_DIR / "frontend"

# W produkcji ustaw w Streamlit Secrets:
# IP_HASH_SALT = "dlugi-losowy-sekret"
DEFAULT_SALT = "zmien-ten-sekret-w-streamlit-secrets"


st.set_page_config(
    page_title="Saperka vs Kurierzy",
    page_icon="🪖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_game_component = components.declare_component(
    "saperka_game",
    path=str(FRONTEND_DIR),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_secret_salt() -> str:
    try:
        return str(st.secrets.get("IP_HASH_SALT", DEFAULT_SALT))
    except Exception:
        return DEFAULT_SALT


def get_client_ip() -> str | None:
    """Zwraca IP połączenia, jeśli Streamlit je udostępnia.

    Streamlit ostrzega, że IP nie powinno być używane do zabezpieczeń, bo da się je podszyć.
    Tutaj używamy go tylko do przypisania nicku i rankingu.
    """
    try:
        ip = getattr(st.context, "ip_address", None)
        if ip:
            return str(ip)
    except Exception:
        pass

    try:
        headers = st.context.headers
        for key in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for", "x-client-ip"):
            value = headers.get(key)
            if value:
                return str(value).split(",")[0].strip()
    except Exception:
        pass

    return None


def get_visitor_key() -> tuple[str, bool]:
    ip = get_client_ip()
    salt = get_secret_salt()

    if ip:
        digest = hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()
        return digest, True

    # Fallback dla localhost albo hostingu, który nie przekazuje IP.
    # To nie jest stałe między przeglądarkami, ale pozwala testować lokalnie.
    if "fallback_visitor_key" not in st.session_state:
        st.session_state.fallback_visitor_key = "session_" + secrets.token_hex(16)
    return st.session_state.fallback_visitor_key, False


def clean_nick(raw: str) -> str:
    nick = raw.strip()
    nick = re.sub(r"\s+", " ", nick)
    # Zostawiamy polskie znaki, litery, cyfry, spację, _ i -
    nick = re.sub(r"[^0-9A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż _-]", "", nick)
    return nick[:24]


def init_db() -> None:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                visitor_key TEXT PRIMARY KEY,
                nick TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_key TEXT NOT NULL,
                nick TEXT NOT NULL,
                score INTEGER NOT NULL,
                round_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_visitor ON scores(visitor_key)")


def get_player_nick(visitor_key: str) -> str | None:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        row = conn.execute(
            "SELECT nick FROM players WHERE visitor_key = ?",
            (visitor_key,),
        ).fetchone()
    return row[0] if row else None


def save_player_nick(visitor_key: str, nick: str) -> None:
    stamp = now_iso()
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute(
            """
            INSERT INTO players(visitor_key, nick, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(visitor_key) DO UPDATE SET
                nick = excluded.nick,
                updated_at = excluded.updated_at
            """,
            (visitor_key, nick, stamp, stamp),
        )


def save_score(visitor_key: str, nick: str, score: int, round_id: str) -> bool:
    if not isinstance(score, int):
        return False
    if score < 0 or score > 999_999:
        return False
    if not round_id or len(round_id) > 80:
        return False

    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        try:
            conn.execute(
                """
                INSERT INTO scores(visitor_key, nick, score, round_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (visitor_key, nick, score, round_id, now_iso()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        rows = conn.execute(
            """
            SELECT
                nick,
                MAX(score) AS best_score,
                COUNT(*) AS games_played,
                MAX(created_at) AS last_played
            FROM scores
            GROUP BY visitor_key, nick
            ORDER BY best_score DESC, last_played ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "place": idx + 1,
            "nick": row[0],
            "score": int(row[1]),
            "games": int(row[2]),
            "last_played": row[3],
        }
        for idx, row in enumerate(rows)
    ]


def get_my_best(visitor_key: str) -> int:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        row = conn.execute(
            "SELECT MAX(score) FROM scores WHERE visitor_key = ?",
            (visitor_key,),
        ).fetchone()
    return int(row[0] or 0)


def render_css() -> None:
    st.markdown(
        """
        <style>
          .block-container {
            padding-top: 0.6rem;
            padding-bottom: 1rem;
            max-width: 1500px;
          }
          header, footer {
            visibility: hidden;
          }
          [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 12px;
            border-radius: 14px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    render_css()
    init_db()

    visitor_key, has_ip = get_visitor_key()
    nick = get_player_nick(visitor_key)

    st.title("🪖 Saperka vs Kurierzy")

    if nick is None:
        st.info("Pierwsze wejście z tego IP. Podaj nick — potem wyniki będą zapisywane w rankingu.")
        if not has_ip:
            st.warning(
                "Nie udało się odczytać IP w tym środowisku, więc aplikacja użyje tymczasowego ID sesji. "
                "Na Streamlit Cloud zwykle działa to lepiej niż lokalnie."
            )

        with st.form("nick_form", clear_on_submit=False):
            raw_nick = st.text_input("Nick", max_chars=24, placeholder="np. Michał")
            accepted = st.checkbox(
                "Rozumiem, że aplikacja zapisze nick, wynik, datę i hash mojego IP.",
                value=False,
            )
            submit = st.form_submit_button("Wejdź do gry")

        if submit:
            cleaned = clean_nick(raw_nick)
            if len(cleaned) < 3:
                st.error("Nick musi mieć minimum 3 znaki.")
            elif not accepted:
                st.error("Zaznacz zgodę na zapis wyniku w rankingu.")
            else:
                save_player_nick(visitor_key, cleaned)
                st.rerun()

        st.stop()

    top = leaderboard(10)
    my_best = get_my_best(visitor_key)

    col1, col2, col3 = st.columns(3)
    col1.metric("Twój nick", nick)
    col2.metric("Twój rekord", my_best)
    col3.metric("Graczy w topce", len(top))

    with st.expander("Zmień nick przypisany do tego IP"):
        with st.form("change_nick_form", clear_on_submit=False):
            new_raw = st.text_input("Nowy nick", value=nick, max_chars=24)
            change = st.form_submit_button("Zapisz nowy nick")
        if change:
            new_nick = clean_nick(new_raw)
            if len(new_nick) < 3:
                st.error("Nick musi mieć minimum 3 znaki.")
            else:
                save_player_nick(visitor_key, new_nick)
                st.success("Nick zmieniony.")
                st.rerun()

    result = _game_component(
        nick=nick,
        leaderboard=top,
        my_best=my_best,
        default=None,
        key="saperka_canvas_game",
    )

    if isinstance(result, dict) and result.get("event") == "score":
        try:
            score = int(result.get("score", 0))
        except Exception:
            score = 0

        round_id = str(result.get("round_id", ""))[:80]
        saved = save_score(visitor_key, nick, score, round_id)

        if saved:
            st.toast(f"Zapisano wynik: {score} pkt")
            st.rerun()

    st.caption(
        "Ranking zapisuje nick, wynik, datę i hash IP, nie surowy adres IP. "
        "Uwaga: lokalna baza SQLite jest dobra do testów i prostego hostingu; na darmowym Streamlit Cloud "
        "dane mogą zniknąć po restarcie lub redeployu. Do produkcji najlepiej podłączyć Supabase, Neon, "
        "Postgres albo Google Sheets."
    )


if __name__ == "__main__":
    main()
