"""Overview — the signed-in member's money, one month at a time."""

import streamlit as st

import data
import theme as T
import ui

conn = ui.conn()
me = ui.member()
user_id = me["user_id"]
ym = ui.selected_ym()

ui.board_header("Wealth <em>Wizard</em>",
                f"{ui.esc(me['name'])} · {ui.esc(user_id)}"
                f"{' · ' + ui.ym_label(ym) if ym else ''}")

life = data.headline(conn, user_id).iloc[0]

if not int(life.TXN_COUNT or 0):
    st.write("")
    ui.empty("Your record has no transactions yet, so there is nothing to total. "
             "Everything else on these pages will fill in once spending is recorded.")
    st.stop()

# --- the total ---------------------------------------------------------------
st.write("")
ui.hero(
    "Total money on your record",
    life.TOTAL_SPEND,
    under=f"{T.count(life.TXN_COUNT)} transactions across "
          f"{int(life.CATEGORIES)} categories, "
          f"{ui.key_to_date(life.FIRST_KEY)} to {ui.key_to_date(life.LAST_KEY)}.",
    aside=[
        ("exact", T.money(life.TOTAL_SPEND)),
        ("average", T.money(life.AVG_TICKET, 0)),
        ("largest", T.money(life.LARGEST, 0)),
    ],
)

if not ym:
    st.stop()

# --- the selected month ------------------------------------------------------
this = data.member_month(conn, user_id, ym).iloc[0]
prev = data.member_month(conn, user_id, data.prev_ym(ym)).iloc[0]
share = (float(this.SPEND or 0) / float(life.TOTAL_SPEND or 1)) * 100

ui.cards([
    (f"{ui.ym_label(ym)} spend", T.compact(this.SPEND),
     T.delta_foot(this.SPEND, prev.SPEND)),
    ("Transactions", T.count(this.TXNS), f"in {ui.ym_label(ym)}"),
    ("Average ticket", T.money(this.AVG_TICKET, 0), "this month"),
    ("Categories used", T.count(this.CATEGORIES), f"of {int(life.CATEGORIES)} lifetime"),
    ("Share of your total", f"{share:,.1f}%", f"{ui.ym_label(ym)} against all time"),
])

ui.hair()

# --- where it went, and when -------------------------------------------------
left, right = st.columns([1, 1.3], gap="large")

with left:
    ui.eyebrow("Where it went", f"Your categories in {ui.ym_label(ym)}.")
    mix = data.member_month_mix(conn, user_id, ym)
    if mix.empty:
        ui.empty(f"No categorised spend in {ui.ym_label(ym)}.")
    else:
        rows = [(r.CATEGORY, float(r.SPEND or 0)) for r in mix.itertuples()]
        st.markdown(
            T.donut(rows, size=232,
                    centre_top=T.compact(mix.SPEND.sum()),
                    centre_bottom=ui.ym_label(ym, short=True).upper()),
            unsafe_allow_html=True,
        )
        st.markdown(T.key(rows, fmt=T.compact), unsafe_allow_html=True)
        top = mix.iloc[0]
        top_share = float(top.SPEND or 0) / float(mix.SPEND.sum() or 1) * 100
        ui.note(f"{ui.esc(top.CATEGORY)} took the largest share this month at "
                f"{T.money(top.SPEND, 0)} — {top_share:,.1f}% of "
                f"{ui.ym_label(ym)}.")

with right:
    ui.eyebrow("Your months", "Newest at the right; the selected month is lit.")
    trend = data.monthly(conn, user_id, 18)
    if trend.empty:
        ui.empty("No monthly history to plot.")
    else:
        ordered = trend.iloc[::-1]
        st.markdown(
            T.bars([(ui.ym_label(r.YM, short=True), float(r.SPEND or 0))
                    for r in ordered.itertuples()], width=780, height=196,
                   highlight=ui.ym_label(ym, short=True)),
            unsafe_allow_html=True,
        )
        ui.note("Months with no spending are absent rather than shown as zero.")

    daily = data.member_daily(conn, user_id, ym)
    if not daily.empty:
        ui.eyebrow("Day by day", f"Days in {ui.ym_label(ym)} with activity.")
        st.markdown(
            T.bars([(f"{int(r.DAY):02d}", float(r.SPEND or 0))
                    for r in daily.itertuples()], width=780, height=158),
            unsafe_allow_html=True,
        )

ui.hair()

# --- this month's biggest, as a listing --------------------------------------
ui.eyebrow("Your largest this month", f"The ten biggest amounts in {ui.ym_label(ym)}.")
# Pull the month, then take the top ten by amount. Reading ten rows straight from
# the query would have ranked the ten most recent, which is a different question.
month_txns = data.transactions(conn, user_id, ym, 300)
if month_txns.empty:
    ui.empty(f"No transactions in {ui.ym_label(ym)}.")
else:
    biggest = month_txns.nlargest(10, "AMOUNT")
    cap = float(biggest.AMOUNT.max() or 1)
    st.markdown(
        ui.listing(["Date", "Category", "Amount", "Against your largest", "Description"],
                   [[(ui.esc(r.TXN_DATE), ""), (ui.esc(r.CATEGORY), ""),
                     (T.money(r.AMOUNT), "num"),
                     (ui.bar_cell(float(r.AMOUNT or 0) / cap * 100), ""),
                     (ui.esc(r.DESCRIPTION), "wrap")]
                    for r in biggest.itertuples()], ranked=True),
        unsafe_allow_html=True,
    )
    if len(month_txns) > 10:
        ui.note(f"{len(month_txns)} transactions in {ui.ym_label(ym)}; the ten "
                "largest are listed. The full ledger is on the Transactions page.")
