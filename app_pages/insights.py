"""Insights — what the mart flagged about this member's spending."""

import streamlit as st

import data
import theme as T
import ui

conn = ui.conn()
me = ui.member()
user_id = me["user_id"]

ui.board_header("Your <em>insights</em>", f"{ui.esc(user_id)} · flagged on your record")

ins = data.insights(conn, user_id=user_id, limit=200)

if ins.empty:
    ui.empty("Nothing has been flagged on your record.")
    st.stop()

graded = ins[ins.SEVERITY.notna()]
severe = graded[graded.SEVERITY >= 4]
kinds = ins.INSIGHT_TYPE.value_counts()

ui.cards([
    ("Insights", T.count(len(ins)), "on your record"),
    ("Graded", T.count(len(graded)), f"{len(ins) - len(graded)} carry no severity"),
    ("Severity 4+", T.count(len(severe)), "worth a look"),
    ("Kinds", T.count(len(kinds)), ", ".join(kinds.index[:2]) if len(kinds) else "—"),
])

ui.hair()

# --- what kind, and how severe -----------------------------------------------
left, right = st.columns([1, 1.5], gap="large")

with left:
    ui.eyebrow("By kind", "Every insight type on your record.")
    rows = [(str(k), int(v)) for k, v in kinds.items()]
    st.markdown(
        T.donut(rows, size=228, centre_top=T.count(len(ins)), centre_bottom="FLAGGED"),
        unsafe_allow_html=True,
    )
    st.markdown(T.key(rows, fmt=lambda v: f"{int(v)}"), unsafe_allow_html=True)

with right:
    ui.eyebrow("By severity", "Higher is more pressing; ungraded rows are excluded.")
    if graded.empty:
        ui.empty("None of your insights carry a severity grade.")
    else:
        counts = graded.SEVERITY.astype(int).value_counts().sort_index()
        st.markdown(
            T.bars([(f"sev {int(k)}", int(v)) for k, v in counts.items()],
                   width=700, height=190),
            unsafe_allow_html=True,
        )
    ui.note("Severity is only set on insights generated inside the mart. The rows "
            "loaded from staging carry none, which is why some show as ungraded.")

ui.hair()

# --- the list -----------------------------------------------------------------
pick = st.multiselect("Kinds", kinds.index.tolist(), default=[],
                      placeholder="All kinds")
only_severe = st.toggle("Only severity 4 and above", value=False)

view = ins
if pick:
    view = view[view.INSIGHT_TYPE.isin(pick)]
if only_severe:
    view = view[view.SEVERITY.notna() & (view.SEVERITY >= 4)]

if view.empty:
    ui.empty("Nothing matches those filters.")
else:
    ui.eyebrow(f"{T.count(len(view))} insights", "Most severe first.")
    st.markdown(
        ui.listing(["Kind", "Severity", "What it says", "Raised"],
                   [[(ui.esc(r.INSIGHT_TYPE), ""), (ui.sev_chip(r.SEVERITY), ""),
                     (ui.esc(r.DESCRIPTION), "wrap"),
                     (ui.esc(r.GENERATED_AT), "dim")] for r in view.itertuples()]),
        unsafe_allow_html=True,
    )
    st.download_button("Download these insights", view.to_csv(index=False).encode(),
                       file_name=f"{user_id}_insights.csv", mime="text/csv")
