"""Categories — how the member's spending divides up."""

import streamlit as st

import data
import theme as T
import ui

conn = ui.conn()
me = ui.member()
user_id = me["user_id"]
ym = ui.selected_ym()

ui.board_header("Your <em>categories</em>", f"{ui.esc(user_id)} · lifetime and by month")

mix = data.category_mix(conn, user_id)
if mix.empty:
    ui.empty("No categorised spending on your record yet.")
    st.stop()

total = float(mix.SPEND.sum() or 0)
top = mix.iloc[0]

ui.hero(
    "Across every category",
    total,
    under=f"{len(mix)} categories used, led by {ui.esc(top.CATEGORY)} at "
          f"{float(top.SPEND or 0) / (total or 1) * 100:,.1f}%.",
    aside=[("exact", T.money(total)),
           ("categories", T.count(len(mix))),
           ("largest", T.money(top.SPEND, 0))],
)

lifetime, month = st.tabs(["Lifetime", f"{ui.ym_label(ym)}" if ym else "Selected month"])

# --- lifetime -----------------------------------------------------------------
with lifetime:
    rows = [(r.CATEGORY, float(r.SPEND or 0)) for r in mix.itertuples()]
    chart, table = st.columns([1, 1.7], gap="large")
    with chart:
        st.markdown(
            T.donut(rows, size=250, centre_top=T.compact(total),
                    centre_bottom="ALL TIME"),
            unsafe_allow_html=True,
        )
        st.markdown(T.key(rows, fmt=T.compact), unsafe_allow_html=True)
    with table:
        st.markdown(
            ui.listing(["Category", "Txns", "Spend", "Average", "Share"],
                       [[(ui.esc(r.CATEGORY), ""), (T.count(r.TXNS), "num"),
                         (T.money(r.SPEND, 0), "num"),
                         (T.money(r.AVG_TICKET, 0), "num"),
                         (ui.bar_cell(float(r.SPEND or 0) / (total or 1) * 100), "")]
                        for r in mix.itertuples()], ranked=True),
            unsafe_allow_html=True,
        )
        st.download_button("Download this breakdown",
                           mix.to_csv(index=False).encode(),
                           file_name=f"{user_id}_categories.csv", mime="text/csv")

# --- the selected month -------------------------------------------------------
with month:
    if not ym:
        ui.empty("Pick a month in the sidebar to compare it against your lifetime split.")
    else:
        m = data.member_month_mix(conn, user_id, ym)
        if m.empty:
            ui.empty(f"You recorded no spending in {ui.ym_label(ym)}.")
        else:
            m_total = float(m.SPEND.sum() or 0)
            rows = [(r.CATEGORY, float(r.SPEND or 0)) for r in m.itertuples()]
            chart, table = st.columns([1, 1.7], gap="large")
            with chart:
                st.markdown(
                    T.donut(rows, size=250, centre_top=T.compact(m_total),
                            centre_bottom=ui.ym_label(ym, short=True).upper()),
                    unsafe_allow_html=True,
                )
                st.markdown(T.key(rows, fmt=T.compact), unsafe_allow_html=True)
            with table:
                # Lifetime share sits beside the month's so a spike is visible as a
                # spike rather than as a number the reader has to hold in their head.
                life_share = {r.CATEGORY: float(r.SPEND or 0) / (total or 1) * 100
                              for r in mix.itertuples()}
                st.markdown(
                    ui.listing(["Category", "Txns", "Spend", "Month share", "Lifetime"],
                               [[(ui.esc(r.CATEGORY), ""), (T.count(r.TXNS), "num"),
                                 (T.money(r.SPEND, 0), "num"),
                                 (f"{float(r.SPEND or 0) / (m_total or 1) * 100:,.1f}%", "num"),
                                 (f"{life_share.get(r.CATEGORY, 0):,.1f}%", "num dim")]
                                for r in m.itertuples()], ranked=True),
                    unsafe_allow_html=True,
                )
                ui.note(f"{ui.ym_label(ym)} came to {T.money(m_total)}, which is "
                        f"{m_total / (total or 1) * 100:,.1f}% of everything you have "
                        "on record.")
