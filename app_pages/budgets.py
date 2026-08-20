"""Budgets — the member's limits, with utilisation recomputed from their ledger."""

import streamlit as st

import data
import theme as T
import ui

conn = ui.conn()
me = ui.member()
user_id = me["user_id"]

ui.board_header("Your <em>budgets</em>", f"{ui.esc(user_id)} · limits and what you used")

buds = data.budgets(conn, user_id)

if buds.empty:
    ui.empty("You have no budget rows. Not every member does — 3,278 of 4,434 "
             "accounts carry budgets, and yours is not one of them. Your ledger, "
             "categories and insights all still work.")
    st.stop()

limits = float(buds.LIMIT_AMOUNT.sum() or 0)
used = float(buds.COMPUTED_SPEND.sum() or 0)
over = [r for r in buds.itertuples()
        if float(r.LIMIT_AMOUNT or 0) and float(r.COMPUTED_SPEND or 0) > float(r.LIMIT_AMOUNT)]

ui.hero(
    "Budgeted across every envelope",
    limits,
    under=f"You used {T.money(used)} against these limits — "
          f"{used / (limits or 1) * 100:,.1f}% of what was set aside.",
    aside=[("envelopes", T.count(len(buds))),
           ("used", T.money(used, 0)),
           ("over limit", T.count(len(over)))],
)

ui.cards([
    ("Envelopes", T.count(len(buds)), "budget rows on your record"),
    ("Total limit", T.compact(limits), T.money(limits)),
    ("Total used", T.compact(used), f"{used / (limits or 1) * 100:,.1f}% of limit"),
    ("Within limit", T.count(len(buds) - len(over)), "envelopes under their cap"),
    ("Over limit", T.count(len(over)),
     "nothing exceeded" if not over else "needs attention"),
])

ui.hair()

ui.eyebrow("Envelope by envelope", "Largest limit first.")
ui.note("Utilisation is recomputed from your own transactions. The stored "
        "ACTUAL_SPEND column is 0 on 6,163 of 6,170 rows in this mart, so it is "
        "shown for reference rather than relied on.")

for r in buds.itertuples():
    limit = float(r.LIMIT_AMOUNT or 0)
    spend = float(r.COMPUTED_SPEND or 0)
    pct = (spend / limit * 100) if limit else 0
    breached = pct > 100
    unparsed = not (2022 <= int(r.P_YEAR or 0) <= 2027)
    flag = '<span class="wb-chip flag">period unreadable</span>' if unparsed else ""
    period = ("—" if unparsed
              else ui.ym_label(int(r.P_YEAR) * 100 + int(r.P_MONTH)))
    st.markdown(
        f'<div class="wb-env"><div class="top">'
        f'<span class="cat">{ui.esc(r.CATEGORY)}</span>'
        f'<span class="amt">{T.money(spend)} of {T.money(limit)}</span></div>'
        f'<div class="track"><i class="{"over" if breached else ""}" '
        f'style="width:{min(pct, 100):.1f}%"></i></div>'
        f'<div class="meta">{period} · {pct:,.1f}% used · '
        f'{int(r.MATCHED_TXNS or 0)} matching transactions · '
        f'stored {T.money(r.STORED_SPEND)} · marked {ui.esc(r.STATUS)} {flag}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

# --- alerts -------------------------------------------------------------------
al = data.alerts(conn, user_id)
if not al.empty:
    ui.hair()
    ui.eyebrow(f"Alerts on your account · {len(al)}", "Raised when an envelope was exceeded.")
    st.markdown(
        ui.listing(["Type", "Message", "Limit", "Recorded", "% used", "Raised"],
                   [[(f'<span class="wb-chip over">{ui.esc(r.ALERT_TYPE)}</span>', ""),
                     (ui.esc(r.MESSAGE), "wrap"),
                     (T.money(r.LIMIT_AMOUNT, 0), "num"),
                     (T.money(r.ACTUAL_SPEND, 0), "num"),
                     (f"{float(r.PERCENT_USED or 0):,.1f}%", "num"),
                     (ui.esc(r.GENERATED_AT), "dim")] for r in al.itertuples()]),
        unsafe_allow_html=True,
    )
