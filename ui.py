"""Shared rendering helpers for the page modules."""

import html

import pandas as pd
import streamlit as st

import theme as T

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def ym_label(ym, short=False) -> str:
    """202607 -> 'Jul 2026' (or 'Jul 26')."""
    try:
        year, month = divmod(int(ym), 100)
        if not 1 <= month <= 12:
            return str(ym)
        return f"{MONTHS[month]} {str(year)[2:] if short else year}"
    except (TypeError, ValueError):
        return "—"


def key_to_date(key) -> str:
    if key is None or pd.isna(key):
        return "—"
    s = str(int(key))
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else "—"


def sev_chip(sev) -> str:
    if sev is None or pd.isna(sev):
        return '<span class="wb-chip mute">none</span>'
    tone = "over" if int(sev) >= 5 else "flag" if int(sev) >= 4 else "ok"
    return f'<span class="wb-chip {tone}">{int(sev)}</span>'


def bar_cell(pct, tone=None) -> str:
    """Inline share bar. pct is 0-100."""
    width = max(min(float(pct or 0), 100), 0)
    colour = f"background:{tone};" if tone else ""
    return (f'<div class="wb-bar"><i style="width:{width:.1f}%;{colour}"></i></div>')


def listing(headers, rows, ranked=False) -> str:
    """rows: list of lists of (html, css_class). Content must be escaped already."""
    head = "".join(f"<th>{h}</th>" for h in (["#"] + headers if ranked else headers))
    body = []
    for i, row in enumerate(rows):
        cells = [(f"{i + 1:02d}", "rank")] + list(row) if ranked else list(row)
        tds = "".join(f'<td class="{c}">{v}</td>' for v, c in cells)
        body.append(f'<tr style="animation-delay:{min(i, 24) * 0.022:.3f}s">{tds}</tr>')
    return (f'<div class="wb-list"><table class="wb-table"><thead><tr>{head}</tr>'
            f'</thead><tbody>{"".join(body)}</tbody></table></div>')


def board_header(title, where):
    """Masthead with the amber running lamp."""
    st.markdown(
        f'<div class="wb-head"><div><p class="name">{title}</p>'
        f'<p class="where"><span class="wb-lamp"></span>{where}</p></div></div>',
        unsafe_allow_html=True,
    )


def conn():
    return st.session_state["conn"]


# --- who is signed in --------------------------------------------------------
def signed_in() -> bool:
    return bool(st.session_state.get("member"))


def member() -> dict:
    """The signed-in member: user_id, name, email, signup, user_key."""
    return st.session_state.get("member") or {}


def sign_in(row):
    """Record the member and drop anything cached for the previous one."""
    st.session_state["member"] = {
        "user_id": str(row.USER_ID),
        "name": str(row.NAME),
        "email": str(row.EMAIL),
        "signup": str(row.SIGNUP_DATE),
        "user_key": str(row.USER_KEY),
    }
    for stale in ("ym", "chat"):
        st.session_state.pop(stale, None)


def sign_out():
    for stale in ("member", "ym", "chat"):
        st.session_state.pop(stale, None)


def mine() -> str:
    return member().get("user_id", "")


def selected_ym():
    return st.session_state.get("ym")


def filter_mode():
    return st.session_state.get("filter_mode", "Month")


def selected_year():
    return st.session_state.get("year_filter")


def selected_date_range():
    return st.session_state.get("date_range")


def empty(message):
    st.markdown(f'<div class="wb-empty">{message}</div>', unsafe_allow_html=True)


def note(message):
    st.markdown(f'<p class="wb-note">{message}</p>', unsafe_allow_html=True)


def hair():
    st.markdown('<div class="wb-hair"></div>', unsafe_allow_html=True)


def eyebrow(text, sub=""):
    st.markdown(T.eyebrow(text, sub), unsafe_allow_html=True)


def cards(specs):
    """specs: list of (caption, figure, footnote)."""
    cols = st.columns(len(specs))
    for col, (cap, fig, foot) in zip(cols, specs):
        col.markdown(T.card(cap, fig, foot), unsafe_allow_html=True)


def hero(lede, amount, under="", aside=()):
    """The page's single flipping total."""
    st.markdown(T.hero(lede, amount, under, aside), unsafe_allow_html=True)


def mode_switch(box=None, key="mode_pick", label="Appearance"):
    """Light/dark switch.

    Writes to session_state["mode"], which streamlit_app reads before it emits the
    stylesheet — so the change lands on the rerun the click causes. The widget
    keeps its own key: sharing one with the value it sets is not allowed.
    """
    box = box or st
    labels = {"light": "Light", "dark": "Dark"}
    current = st.session_state.get("mode", "dark")
    picked = box.segmented_control(
        label, list(labels.values()), default=labels[current], key=key,
        help="Switch between the paper and the ink.",
    )
    if picked:
        chosen = "light" if picked == "Light" else "dark"
        if chosen != current:
            st.session_state["mode"] = chosen
            st.rerun()
