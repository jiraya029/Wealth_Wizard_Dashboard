"""Transactions — the member's own ledger."""

import streamlit as st

import data
import theme as T
import ui

conn = ui.conn()
me = ui.member()
user_id = me["user_id"]
ym = ui.selected_ym()
mode = ui.filter_mode()

ui.board_header("Your <em>ledger</em>", f"{ui.esc(user_id)} · every amount recorded")

# Adapt scope options based on filter mode
if mode == "Date Range":
    scope_label = "Date range"
    txns = data.transactions(conn, user_id, None, 300)
    dr = ui.selected_date_range()
    if dr and len(dr) == 2:
        import pandas as pd
        txns = txns[txns.TXN_DATE.apply(
            lambda d: dr[0].isoformat() <= str(d)[:10] <= dr[1].isoformat()
            if d and str(d) != "—" else False
        )]
    month_only = False
elif mode == "Year":
    year = ui.selected_year()
    scope_label = f"Year {year}" if year else "All time"
    txns = data.transactions(conn, user_id, None, 300)
    if year:
        txns = txns[txns.TXN_DATE.apply(
            lambda d: str(d)[:4] == str(year) if d and str(d) != "—" else False
        )]
    month_only = False
else:
    scope = st.radio(
        "Show",
        ["Whole record", f"{ui.ym_label(ym)} only" if ym else "This month"],
        horizontal=True, label_visibility="collapsed",
    )
    month_only = ym is not None and scope.startswith(ui.ym_label(ym))
    txns = data.transactions(conn, user_id, ym if month_only else None, 300)

if txns.empty:
    ui.empty(f"No transactions{' in ' + ui.ym_label(ym) if month_only else ' on your record'}.")
    st.stop()

total = float(txns.AMOUNT.sum() or 0)
ui.hero(
    f"{ui.ym_label(ym)} total" if month_only else "Total on the rows below",
    total,
    under=f"{T.count(len(txns))} transactions"
          f"{' in ' + ui.ym_label(ym) if month_only else ', newest first, capped at 300'}.",
    aside=[
        ("exact", T.money(total)),
        ("largest", T.money(txns.AMOUNT.max(), 0)),
        ("smallest", T.money(txns.AMOUNT.min(), 0)),
    ],
)

# --- filters ------------------------------------------------------------------
cats = sorted(txns.CATEGORY.dropna().unique().tolist())
pick, search = st.columns([1.4, 1], gap="medium")
with pick:
    chosen = st.multiselect("Categories", cats, default=[],
                            placeholder="All categories")
with search:
    term = st.text_input("Find in description", placeholder="rent · fuel · fee")

view = txns
if chosen:
    view = view[view.CATEGORY.isin(chosen)]
if term:
    view = view[view.DESCRIPTION.str.contains(term, case=False, na=False)]

ui.hair()

if view.empty:
    ui.empty("No rows match those filters. Clear them to see your ledger again.")
    st.stop()

shown = float(view.AMOUNT.sum() or 0)
ui.eyebrow(f"{T.count(len(view))} rows · {T.money(shown)}",
           "Filtered from your record." if len(view) != len(txns) else "Newest first.")

cap = float(view.AMOUNT.max() or 1)
st.markdown(
    ui.listing(["Date", "Category", "Amount", "Size", "Description"],
               [[(ui.esc(r.TXN_DATE), ""), (ui.esc(r.CATEGORY), ""),
                 (T.money(r.AMOUNT), "num"),
                 (ui.bar_cell(float(r.AMOUNT or 0) / cap * 100), ""),
                 (ui.esc(r.DESCRIPTION), "wrap")]
                for r in view.itertuples()]),
    unsafe_allow_html=True,
)

st.download_button("Download these rows", view.to_csv(index=False).encode(),
                   file_name=f"{user_id}_transactions.csv", mime="text/csv")
