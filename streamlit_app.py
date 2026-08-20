"""Wealth Wizard — entry point.

Holds the Snowflake connection, gates the app behind a member id, and gives every
page the two things it needs: who is signed in, and which of their months is on
screen. Before sign-in the only reachable page is the sign-in screen.
"""

import streamlit as st

import data
import theme as T
import ui

st.set_page_config(page_title="Wealth Wizard", page_icon=":material/savings:",
                   layout="wide", initial_sidebar_state="expanded")

# The mode is read before the stylesheet is written, so the switch below takes
# effect on the same rerun that flips it.
if "mode" not in st.session_state:
    st.session_state["mode"] = "dark"
st.markdown(T.css(st.session_state["mode"]), unsafe_allow_html=True)

if "conn" not in st.session_state:
    st.session_state["conn"] = st.connection("snowflake")
conn = st.session_state["conn"]

# --- gate --------------------------------------------------------------------
if not ui.signed_in():
    st.navigation([st.Page("app_pages/login.py", title="Sign in")],
                  position="hidden").run()
    st.stop()

me = ui.member()

# --- shared controls, only once there is somebody to show them for ------------
with st.sidebar:
    st.markdown(
        f'<p class="wb-eyebrow" style="margin-top:.4rem">Wealth Wizard</p>'
        f'<div class="wb-rule"></div>'
        f'{T.who(ui.esc(me["name"]), ui.esc(me["user_id"]))}',
        unsafe_allow_html=True,
    )

    months = data.member_months(conn, me["user_id"])
    if months.empty:
        st.warning("No transactions on your record yet.")
        st.session_state["ym"] = None
    else:
        choices = [int(v) for v in months.YM.tolist()]
        volumes = {int(r.YM): int(r.TXNS) for r in months.itertuples()}

        # --- Date filter mode ---
        st.markdown('<p class="wb-eyebrow" style="margin-top:.6rem;margin-bottom:.2rem">'
                    'Date Filter</p>', unsafe_allow_html=True)
        filter_mode = st.segmented_control(
            "Filter by",
            ["Month", "Year", "Date Range"],
            default=st.session_state.get("filter_mode", "Month"),
            key="filter_mode_pick",
            help="Choose how to filter your data.",
        )
        if filter_mode and filter_mode != st.session_state.get("filter_mode"):
            st.session_state["filter_mode"] = filter_mode

        active_mode = st.session_state.get("filter_mode", "Month")

        if active_mode == "Month":
            if st.session_state.get("ym") not in choices:
                st.session_state["ym"] = choices[0]
            st.selectbox(
                "Month",
                choices,
                key="ym",
                format_func=lambda v: f"{ui.ym_label(v)}  ·  {volumes.get(v, 0)} txns",
                help="Every figure marked with a month follows this choice.",
            )
            st.caption(f"{len(choices)} months on your record · "
                       f"{ui.ym_label(choices[-1])} to {ui.ym_label(choices[0])}")

        elif active_mode == "Year":
            years = sorted(set(int(c) // 100 for c in choices), reverse=True)
            selected_year = st.selectbox(
                "Year", years, key="year_pick",
                format_func=lambda y: str(y),
                help="View data for a specific year.",
            )
            # Set ym to the most recent month of that year
            year_months = [c for c in choices if int(c) // 100 == selected_year]
            if year_months:
                st.session_state["ym"] = year_months[0]
                st.session_state["year_filter"] = selected_year
                total_txns = sum(volumes.get(m, 0) for m in year_months)
                st.caption(f"{len(year_months)} months · {total_txns} transactions in {selected_year}")
            else:
                st.session_state["ym"] = choices[0]

        elif active_mode == "Date Range":
            import datetime
            # Derive date bounds from available months
            first_ym = min(choices)
            last_ym = max(choices)
            first_date = datetime.date(first_ym // 100, first_ym % 100, 1)
            last_month = last_ym % 100
            last_year = last_ym // 100
            import calendar
            last_day = calendar.monthrange(last_year, last_month)[1]
            last_date = datetime.date(last_year, last_month, last_day)

            date_range = st.date_input(
                "Select date range",
                value=(first_date, last_date),
                min_value=first_date,
                max_value=last_date,
                key="date_range_pick",
                help="Filter transactions within a specific date range.",
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                st.session_state["date_range"] = date_range
                st.caption(f"{date_range[0].strftime('%b %d, %Y')} to "
                           f"{date_range[1].strftime('%b %d, %Y')}")
            # Keep ym set to most recent for other pages
            if st.session_state.get("ym") not in choices:
                st.session_state["ym"] = choices[0]

    ui.hair()
    st.button("Refresh figures", use_container_width=True, on_click=data.clear_all,
              help="Read the latest rows from Snowflake.", type="secondary")
    st.button("Sign out", use_container_width=True, on_click=ui.sign_out)

    ui.hair()
    ui.mode_switch(st.sidebar)

# --- navigation --------------------------------------------------------------
page = st.navigation({
    "Wealth Wizard": [
        st.Page("app_pages/overview.py", title="Overview",
                icon=":material/dashboard:", default=True),
        st.Page("app_pages/transactions.py", title="Transactions",
                icon=":material/receipt_long:"),
        st.Page("app_pages/categories.py", title="Categories",
                icon=":material/donut_small:"),
        st.Page("app_pages/budgets.py", title="Budgets",
                icon=":material/account_balance_wallet:"),
        st.Page("app_pages/insights.py", title="Insights",
                icon=":material/lightbulb:"),
    ],
    "Assistant": [
        st.Page("app_pages/ask.py", title="Ask", icon=":material/forum:"),
    ],
}, position="sidebar")

page.run()
