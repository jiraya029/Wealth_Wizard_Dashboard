"""Read-only query layer for the Wealth Wizard mart.

Values are always passed as bound qmark parameters; table and column names are
fixed literals in this module. `ym` arguments are integers shaped YYYYMM.
"""

import streamlit as st

import config

MART = "WEALTH_WIZARD.MART_WEALTH_WIZARD"
TTL = config.CACHE_TTL


def prev_ym(ym: int) -> int:
    year, month = divmod(int(ym), 100)
    return (year - 1) * 100 + 12 if month == 1 else year * 100 + month - 1


# --- calendar ---------------------------------------------------------------
@st.cache_data(ttl=TTL, show_spinner=False)
def month_options(_conn):
    return _conn.query(
        f"""
        SELECT FLOOR(DATE_KEY / 100) AS YM, COUNT(*) AS TXNS, SUM(AMOUNT) AS SPEND
        FROM {MART}.FACT_TRANSACTION
        GROUP BY 1 ORDER BY 1 DESC
        """
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def member_months(_conn, user_id: str):
    """Only the months this member actually transacted in.

    Offering the whole mart's 56 months to someone who has records in nine of
    them invites empty screens, so the picker is built from their own history.
    """
    return _conn.query(
        f"""
        SELECT FLOOR(t.DATE_KEY / 100) AS YM, COUNT(*) AS TXNS,
               SUM(t.AMOUNT) AS SPEND
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        WHERE u.USER_ID = ?
        GROUP BY 1 ORDER BY 1 DESC
        """,
        params=(user_id,),
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def member_daily(_conn, user_id: str, ym: int):
    """Day-by-day spend for one member in one month."""
    return _conn.query(
        f"""
        SELECT MOD(t.DATE_KEY, 100) AS DAY, COUNT(*) AS TXNS, SUM(t.AMOUNT) AS SPEND
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        WHERE u.USER_ID = ? AND FLOOR(t.DATE_KEY / 100) = ?
        GROUP BY 1 ORDER BY 1
        """,
        params=(user_id, int(ym)),
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def member_month_mix(_conn, user_id: str, ym: int):
    """One member's category split inside one month — the pie on the overview."""
    return _conn.query(
        f"""
        SELECT COALESCE(c.NAME, '(unmapped)') AS CATEGORY, COUNT(*) AS TXNS,
               SUM(t.AMOUNT) AS SPEND, AVG(t.AMOUNT) AS AVG_TICKET
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = t.CATEGORY_KEY
        WHERE u.USER_ID = ? AND FLOOR(t.DATE_KEY / 100) = ?
        GROUP BY 1 ORDER BY SPEND DESC
        """,
        params=(user_id, int(ym)),
    )


# --- whole-book, month scoped -----------------------------------------------
@st.cache_data(ttl=TTL, show_spinner=False)
def month_kpis(_conn, ym: int):
    """Selected month and the month before it, one row each."""
    return _conn.query(
        f"""
        SELECT FLOOR(t.DATE_KEY / 100)   AS YM,
               COUNT(*)                   AS TXNS,
               COUNT(DISTINCT t.USER_KEY) AS MEMBERS,
               SUM(t.AMOUNT)              AS SPEND,
               AVG(t.AMOUNT)              AS AVG_TICKET,
               MAX(t.AMOUNT)              AS LARGEST,
               COUNT(DISTINCT t.CATEGORY_KEY) AS CATEGORIES
        FROM {MART}.FACT_TRANSACTION t
        WHERE FLOOR(t.DATE_KEY / 100) IN (?, ?)
        GROUP BY 1
        """,
        params=[int(ym), prev_ym(ym)],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def month_category_mix(_conn, ym: int):
    return _conn.query(
        f"""
        SELECT COALESCE(c.NAME, '(unmapped)') AS CATEGORY,
               COUNT(*) AS TXNS, SUM(t.AMOUNT) AS SPEND, AVG(t.AMOUNT) AS AVG_TICKET,
               COUNT(DISTINCT t.USER_KEY) AS MEMBERS
        FROM {MART}.FACT_TRANSACTION t
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = t.CATEGORY_KEY
        WHERE FLOOR(t.DATE_KEY / 100) = ?
        GROUP BY 1 ORDER BY SPEND DESC
        """,
        params=[int(ym)],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def month_top_members(_conn, ym: int, n: int = 12):
    return _conn.query(
        f"""
        SELECT u.USER_ID, u.NAME, u.EMAIL,
               COUNT(*) AS TXNS, SUM(t.AMOUNT) AS SPEND, MAX(t.AMOUNT) AS LARGEST
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        WHERE FLOOR(t.DATE_KEY / 100) = ?
        GROUP BY 1, 2, 3 ORDER BY SPEND DESC LIMIT ?
        """,
        params=[int(ym), n],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def month_daily(_conn, ym: int):
    return _conn.query(
        f"""
        SELECT MOD(DATE_KEY, 100) AS DAY, COUNT(*) AS TXNS, SUM(AMOUNT) AS SPEND
        FROM {MART}.FACT_TRANSACTION
        WHERE FLOOR(DATE_KEY / 100) = ?
        GROUP BY 1 ORDER BY 1
        """,
        params=[int(ym)],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def book_trend(_conn, n: int = 18):
    return _conn.query(
        f"""
        SELECT FLOOR(DATE_KEY / 100) AS YM, COUNT(*) AS TXNS, SUM(AMOUNT) AS SPEND
        FROM {MART}.FACT_TRANSACTION
        GROUP BY 1 ORDER BY 1 DESC LIMIT ?
        """,
        params=[n],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def estate(_conn):
    return _conn.query(
        f"""
        SELECT
          (SELECT COUNT(*) FROM {MART}.DIM_USER)            AS MEMBERS,
          (SELECT COUNT(*) FROM {MART}.FACT_TRANSACTION)    AS TXNS,
          (SELECT SUM(AMOUNT) FROM {MART}.FACT_TRANSACTION) AS SPEND,
          (SELECT COUNT(*) FROM {MART}.FACT_INSIGHT)        AS INSIGHTS,
          (SELECT COUNT(*) FROM {MART}.FACT_BUDGET)         AS BUDGETS,
          (SELECT COUNT(*) FROM {MART}.DIM_CATEGORY)        AS CATEGORIES
        """
    )


# --- members ----------------------------------------------------------------
@st.cache_data(ttl=TTL, show_spinner=False)
def member(_conn, user_id: str):
    return _conn.query(
        f"SELECT USER_KEY, USER_ID, NAME, EMAIL, SIGNUP_DATE FROM {MART}.DIM_USER "
        f"WHERE USER_ID = ?",
        params=[user_id],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def search_members(_conn, term: str, n: int = 25):
    """Match on id, name or email. The term is bound, never interpolated."""
    like = f"%{term.lower()}%"
    return _conn.query(
        f"""
        SELECT u.USER_ID, u.NAME, u.EMAIL, COUNT(t.TXN_KEY) AS TXNS,
               COALESCE(SUM(t.AMOUNT), 0) AS SPEND
        FROM {MART}.DIM_USER u
        LEFT JOIN {MART}.FACT_TRANSACTION t ON t.USER_KEY = u.USER_KEY
        WHERE LOWER(u.USER_ID) LIKE ? OR LOWER(u.NAME) LIKE ? OR LOWER(u.EMAIL) LIKE ?
        GROUP BY 1, 2, 3 ORDER BY TXNS DESC LIMIT ?
        """,
        params=[like, like, like, n],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def busiest_members(_conn, n: int = 10):
    return _conn.query(
        f"""
        SELECT u.USER_ID, u.NAME, COUNT(t.TXN_KEY) AS TXNS, SUM(t.AMOUNT) AS SPEND
        FROM {MART}.DIM_USER u
        JOIN {MART}.FACT_TRANSACTION t ON t.USER_KEY = u.USER_KEY
        GROUP BY 1, 2 ORDER BY TXNS DESC LIMIT ?
        """,
        params=[n],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def headline(_conn, user_id: str):
    return _conn.query(
        f"""
        SELECT COUNT(t.TXN_KEY) AS TXN_COUNT, COALESCE(SUM(t.AMOUNT), 0) AS TOTAL_SPEND,
               COALESCE(AVG(t.AMOUNT), 0) AS AVG_TICKET,
               COALESCE(MAX(t.AMOUNT), 0) AS LARGEST,
               COUNT(DISTINCT t.CATEGORY_KEY) AS CATEGORIES,
               MIN(t.DATE_KEY) AS FIRST_KEY, MAX(t.DATE_KEY) AS LAST_KEY
        FROM {MART}.DIM_USER u
        LEFT JOIN {MART}.FACT_TRANSACTION t ON t.USER_KEY = u.USER_KEY
        WHERE u.USER_ID = ?
        """,
        params=[user_id],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def member_month(_conn, user_id: str, ym: int):
    return _conn.query(
        f"""
        SELECT COUNT(*) AS TXNS, COALESCE(SUM(t.AMOUNT), 0) AS SPEND,
               COALESCE(AVG(t.AMOUNT), 0) AS AVG_TICKET,
               COUNT(DISTINCT t.CATEGORY_KEY) AS CATEGORIES
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        WHERE u.USER_ID = ? AND FLOOR(t.DATE_KEY / 100) = ?
        """,
        params=[user_id, int(ym)],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def monthly(_conn, user_id: str, months: int = 18):
    return _conn.query(
        f"""
        SELECT FLOOR(t.DATE_KEY / 100) AS YM, COUNT(*) AS TXNS, SUM(t.AMOUNT) AS SPEND
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        WHERE u.USER_ID = ?
        GROUP BY 1 ORDER BY 1 DESC LIMIT ?
        """,
        params=[user_id, months],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def category_mix(_conn, user_id: str):
    return _conn.query(
        f"""
        SELECT COALESCE(c.NAME, '(unmapped)') AS CATEGORY, COUNT(*) AS TXNS,
               SUM(t.AMOUNT) AS SPEND, AVG(t.AMOUNT) AS AVG_TICKET
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = t.CATEGORY_KEY
        WHERE u.USER_ID = ?
        GROUP BY 1 ORDER BY SPEND DESC
        """,
        params=[user_id],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def transactions(_conn, user_id: str, ym=None, limit: int = 300):
    """ym=None returns the whole history for the member."""
    if ym:
        clause, params = "AND FLOOR(t.DATE_KEY / 100) = ?", [user_id, int(ym), limit]
    else:
        clause, params = "", [user_id, limit]
    return _conn.query(
        f"""
        SELECT COALESCE(TO_VARCHAR(d.FULL_DATE), TO_VARCHAR(t.DATE_KEY)) AS TXN_DATE,
               COALESCE(c.NAME, '(unmapped)') AS CATEGORY, t.AMOUNT,
               COALESCE(t.DESCRIPTION, '') AS DESCRIPTION, t.TXN_KEY
        FROM {MART}.FACT_TRANSACTION t
        JOIN {MART}.DIM_USER u ON u.USER_KEY = t.USER_KEY
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = t.CATEGORY_KEY
        LEFT JOIN {MART}.DIM_DATE d ON d.DATE_KEY = t.DATE_KEY
        WHERE u.USER_ID = ? {clause}
        ORDER BY t.DATE_KEY DESC LIMIT ?
        """,
        params=params,
    )


# --- budgets ----------------------------------------------------------------
@st.cache_data(ttl=TTL, show_spinner=False)
def budgets(_conn, user_id: str):
    """Envelopes with utilisation recomputed from transactions.

    FACT_BUDGET.ACTUAL_SPEND is 0 on 6,163 of 6,170 rows, so the stored value is
    reported beside a live computation rather than trusted.
    """
    return _conn.query(
        f"""
        WITH me AS (SELECT USER_KEY FROM {MART}.DIM_USER WHERE USER_ID = ?),
        env AS (
          SELECT b.CATEGORY_KEY, b.LIMIT_AMOUNT, b.ACTUAL_SPEND AS STORED_SPEND,
                 b.STATUS,
                 FLOOR(b.PERIOD_DATE_KEY / 10000) AS P_YEAR,
                 MOD(FLOOR(b.PERIOD_DATE_KEY / 100), 100) AS P_MONTH
          FROM {MART}.FACT_BUDGET b JOIN me ON me.USER_KEY = b.USER_KEY
        )
        SELECT COALESCE(c.NAME, '(unmapped)') AS CATEGORY, e.P_YEAR, e.P_MONTH,
               e.LIMIT_AMOUNT, e.STORED_SPEND, e.STATUS,
               COALESCE(SUM(t.AMOUNT), 0) AS COMPUTED_SPEND,
               COUNT(t.TXN_KEY) AS MATCHED_TXNS
        FROM env e
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = e.CATEGORY_KEY
        LEFT JOIN {MART}.FACT_TRANSACTION t
               ON t.CATEGORY_KEY = e.CATEGORY_KEY
              AND t.USER_KEY IN (SELECT USER_KEY FROM me)
              AND FLOOR(t.DATE_KEY / 10000) = e.P_YEAR
              AND MOD(FLOOR(t.DATE_KEY / 100), 100) = e.P_MONTH
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY e.P_YEAR DESC, e.P_MONTH DESC
        """,
        params=[user_id],
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def budget_book(_conn):
    """Portfolio view: limits and status across all members."""
    return _conn.query(
        f"""
        SELECT COALESCE(c.NAME, '(unmapped)') AS CATEGORY, b.STATUS,
               COUNT(*) AS ENVELOPES, SUM(b.LIMIT_AMOUNT) AS TOTAL_LIMIT,
               AVG(b.LIMIT_AMOUNT) AS AVG_LIMIT,
               SUM(CASE WHEN FLOOR(b.PERIOD_DATE_KEY / 10000) < 2022
                        THEN 1 ELSE 0 END) AS UNPARSED_PERIODS
        FROM {MART}.FACT_BUDGET b
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = b.CATEGORY_KEY
        GROUP BY 1, 2 ORDER BY TOTAL_LIMIT DESC
        """
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def breaches(_conn):
    return _conn.query(
        f"""
        SELECT u.USER_ID, u.NAME, COALESCE(c.NAME, '(unmapped)') AS CATEGORY,
               b.LIMIT_AMOUNT, b.ACTUAL_SPEND, b.REMAINING_AMOUNT
        FROM {MART}.FACT_BUDGET b
        JOIN {MART}.DIM_USER u ON u.USER_KEY = b.USER_KEY
        LEFT JOIN {MART}.DIM_CATEGORY c ON c.CATEGORY_KEY = b.CATEGORY_KEY
        WHERE b.STATUS = 'over'
        ORDER BY b.ACTUAL_SPEND DESC
        """
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def alerts(_conn, user_id=None):
    if user_id:
        return _conn.query(
            f"""
            SELECT u.USER_ID, u.NAME, a.ALERT_TYPE, a.MESSAGE, a.LIMIT_AMOUNT,
                   a.ACTUAL_SPEND, a.PERCENT_USED, a.GENERATED_AT, a.ACKNOWLEDGED
            FROM {MART}.FACT_BUDGET_ALERT a
            JOIN {MART}.DIM_USER u ON u.USER_KEY = a.USER_KEY
            WHERE u.USER_ID = ? ORDER BY a.GENERATED_AT DESC
            """,
            params=[user_id],
        )
    return _conn.query(
        f"""
        SELECT u.USER_ID, u.NAME, a.ALERT_TYPE, a.MESSAGE, a.LIMIT_AMOUNT,
               a.ACTUAL_SPEND, a.PERCENT_USED, a.GENERATED_AT, a.ACKNOWLEDGED
        FROM {MART}.FACT_BUDGET_ALERT a
        LEFT JOIN {MART}.DIM_USER u ON u.USER_KEY = a.USER_KEY
        ORDER BY a.GENERATED_AT DESC
        """
    )


# --- insights ---------------------------------------------------------------
@st.cache_data(ttl=TTL, show_spinner=False)
def insight_mix(_conn):
    return _conn.query(
        f"""
        SELECT INSIGHT_TYPE, COUNT(*) AS N,
               SUM(CASE WHEN SEVERITY IS NULL THEN 1 ELSE 0 END) AS NO_SEVERITY,
               AVG(SEVERITY) AS AVG_SEVERITY
        FROM {MART}.FACT_INSIGHT GROUP BY 1 ORDER BY N DESC
        """
    )


@st.cache_data(ttl=TTL, show_spinner=False)
def insights(_conn, user_id=None, kind=None, limit: int = 120):
    where, params = [], []
    if user_id:
        where.append("u.USER_ID = ?")
        params.append(user_id)
    if kind and kind != "All types":
        where.append("i.INSIGHT_TYPE = ?")
        params.append(kind)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    return _conn.query(
        f"""
        SELECT u.USER_ID, u.NAME, i.INSIGHT_TYPE, i.SEVERITY, i.DESCRIPTION,
               i.GENERATED_AT, i.DATE_KEY
        FROM {MART}.FACT_INSIGHT i
        LEFT JOIN {MART}.DIM_USER u ON u.USER_KEY = i.USER_KEY
        {clause}
        ORDER BY i.SEVERITY DESC NULLS LAST, i.GENERATED_AT DESC
        LIMIT ?
        """,
        params=params,
    )


def clear_all():
    """Drop every cached loader so the next read hits Snowflake."""
    for fn in (month_options, member_months, member_daily, member_month_mix,
               month_kpis, month_category_mix, month_top_members,
               month_daily, book_trend, estate, member, search_members,
               busiest_members, headline, member_month, monthly, category_mix,
               transactions, budgets, budget_book, breaches, alerts,
               insight_mix, insights):
        fn.clear()
