"""Sign in — the member id decides whose money the app shows.

This identifies a member; it does not authenticate one. There is no password in
DIM_USER, so anyone who knows an id can open that record. Treat it as a way of
choosing whose figures to display, not as a security boundary.
"""

import streamlit as st

import data
import theme as T
import ui

conn = ui.conn()

left, mid, right = st.columns([1, 1.5, 1])

with right:
    # Available before sign-in too, so nobody has to squint at the wrong mode
    # just to reach their account.
    ui.mode_switch(label="Appearance", key="mode_pick_gate")

with mid:
    st.markdown(
        f'<div class="wb-gate">'
        f'<div class="mark">{T.flaps("WEALTH WIZARD", delay_step=0.055)}</div>'
        f'<p class="tag">Your spending, on the record</p>'
        f'<p class="say">Enter your member id to open your own account. '
        f'<span>Ids look like U000862.</span></p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.form("signin", clear_on_submit=False):
        entered = st.text_input("Member id", placeholder="U000862",
                                max_chars=12, label_visibility="collapsed")
        go = st.form_submit_button("Open my account", use_container_width=True,
                                   type="primary")

    if go:
        user_id = (entered or "").strip().upper()
        if not user_id:
            ui.empty("Enter your member id to continue.")
        else:
            found = data.member(conn, user_id)
            if found.empty:
                ui.empty(f"No account with id <b>{ui.esc(user_id)}</b>. "
                         "Check the id, or search for your name below.")
            else:
                ui.sign_in(found.iloc[0])
                st.rerun()

    ui.hair()

    # Not everyone will remember an id, so give them a way to find it.
    with st.expander("I don't know my member id"):
        term = st.text_input("Search by name or email", placeholder="Tiffany  ·  @example.net")
        if term and len(term) >= 2:
            hits = data.search_members(conn, term, 12)
            if hits.empty:
                ui.empty(f"Nothing matches “{ui.esc(term)}”.")
            else:
                st.markdown(
                    ui.listing(["Member id", "Name", "Email", "Txns", "Spend"],
                               [[(ui.esc(r.USER_ID), ""), (ui.esc(r.NAME), ""),
                                 (ui.esc(r.EMAIL), "dim"), (T.count(r.TXNS), "num"),
                                 (T.compact(r.SPEND), "num")]
                                for r in hits.itertuples()]),
                    unsafe_allow_html=True,
                )
                ui.note("Type the id from this list into the box above.")
        else:
            st.caption("Type at least two characters of your name or email.")

    st.markdown(
        '<p class="wb-note" style="margin-top:1.2rem">Signing in here only chooses '
        'whose records to show — it does not check a password. Anyone with a valid '
        'member id can open that account.</p>',
        unsafe_allow_html=True,
    )
