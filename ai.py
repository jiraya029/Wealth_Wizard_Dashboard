"""Gemini analyst: question -> guarded SELECT -> rows -> written answer.

Gemini never touches Snowflake. It proposes SQL, this module refuses anything
that is not a single read-only statement against WEALTH_WIZARD, the app runs it,
and the rows go back to Gemini to be summarised. The model name lives in
config.py and is deliberately never surfaced in the interface.
"""

import datetime
import json
import re
import urllib.error
import urllib.request

import streamlit as st

import config

DB = "WEALTH_WIZARD"
MART = "MART_WEALTH_WIZARD"
SCHEMAS = {
    "MART": MART,
    "STAGE": "STAGE_WEALTH_WIZARD",
    "RAW": "RAW_WEALTH_WIZARD",
    "ANALYTICS": "ANALYTICS_WEALTH_WIZARD",
    "AUDIT": "AUDIT_WEALTH_WIZARD",
}

SCHEMA = """
Database WEALTH_WIZARD, schema MART_WEALTH_WIZARD (a star schema). Fully qualify
every object as WEALTH_WIZARD.MART_WEALTH_WIZARD.<TABLE>. The database is spelled
WEALTH_WIZARD exactly once — never WEALTH_WEALTH_WIZARD.

DIM_USER(USER_KEY pk, USER_ID unique e.g. 'U001566', NAME, EMAIL, SIGNUP_DATE) 4,434 rows
DIM_CATEGORY(CATEGORY_KEY pk, CATEGORY_ID unique, NAME, ACTIVE_FLAG) 20 rows
DIM_DATE(DATE_KEY pk numeric YYYYMMDD, FULL_DATE, DAY, MONTH, MONTH_NAME, QUARTER, YEAR) 2,000 rows from 2022-01-01
FACT_TRANSACTION(TXN_KEY pk, USER_KEY fk, CATEGORY_KEY fk, DATE_KEY fk, AMOUNT number(12,2), TXN_TYPE, DESCRIPTION) 78,155 rows
FACT_BUDGET(BUDGET_KEY pk, USER_KEY fk, CATEGORY_KEY fk, PERIOD_DATE_KEY, LIMIT_AMOUNT, ACTUAL_SPEND, REMAINING_AMOUNT, STATUS) 6,170 rows
FACT_INSIGHT(INSIGHT_KEY pk, USER_KEY fk, TXN_KEY fk, DATE_KEY fk, INSIGHT_TYPE, SEVERITY, DESCRIPTION, GENERATED_AT) 23,956 rows
FACT_BUDGET_ALERT(ALERT_KEY, BUDGET_KEY, USER_KEY, CATEGORY_KEY, ALERT_TYPE, MESSAGE, LIMIT_AMOUNT, ACTUAL_SPEND, PERCENT_USED, GENERATED_AT, ACKNOWLEDGED) 5 rows

Facts carry surrogate keys only, so join through DIM_USER to filter by USER_ID.
For a calendar month, FLOOR(DATE_KEY/100) = YYYYMM is cheaper than joining DIM_DATE.

Known data conditions — respect these or the answer will be wrong:
- TXN_TYPE is 'expense' on all 78,155 rows. There is no income and no net-savings
  figure in this mart. Never present a savings, income or profit number.
- FACT_BUDGET.STATUS is 'ok' on 6,165 rows and 'over' on 5. ALERT_TYPE is always
  'over'; no warning-level alerts exist.
- FACT_BUDGET.ACTUAL_SPEND is 0 on 6,163 of 6,170 rows, so budget utilisation must
  be computed from FACT_TRANSACTION, not read from that column.
- FACT_BUDGET.PERIOD_DATE_KEY is unreliable: only 501 of 6,170 rows match DIM_DATE
  and bad periods fall back to 19700101. Derive the period arithmetically.
- FACT_INSIGHT.SEVERITY is NULL on the 10,102 rows loaded from staging and set (2-5)
  only on the 13,854 generated in the mart. DATE_KEY is NULL on those 13,854.
- Transactions run 2022-01 to 2026-08; August 2026 is partial.
"""


def context():
    """Schema notes plus today's date, so relative months resolve correctly."""
    today = datetime.date.today()
    return SCHEMA + f"""
Today is {today:%Y-%m-%d}. Resolve relative periods against it:
- "this month" / "current month" = {today:%Y%m} -> FLOOR(DATE_KEY/100) = {today:%Y%m}
- "last month" = {(today.replace(day=1) - datetime.timedelta(days=1)):%Y%m}
- "this year" = YEAR {today:%Y} -> FLOOR(DATE_KEY/10000) = {today:%Y}
The newest month holding data is 202608 and it is incomplete, so a current-month
total is a partial month. Say so when you report one.
"""


SQL_RULES = """You are the Wealth Wizard assistant. Decide first whether the
question needs the member's own records, or whether it is a general question you
can simply answer.

Return ONLY a JSON object, no prose, no code fence. One of these two shapes:

Needs data from the mart:
{"sql": "<one SELECT, no trailing semicolon>", "reads": "<what it returns, one sentence>"}

Does not need data — general knowledge, a definition, advice, or small talk:
{"sql": "", "answer": "<your complete answer, 2-4 sentences, plain text>"}

Choose the general shape for questions like "what is a good savings rate",
"explain what a budget envelope is", "how should I cut my food spending",
"what does severity 5 mean", "who are you". Choose SQL whenever the question
refers to actual amounts, counts, dates, categories, budgets or insights.

SQL rules:
- SELECT or WITH only. Never INSERT, UPDATE, DELETE, MERGE, CREATE, DROP, ALTER,
  TRUNCATE, GRANT, CALL, COPY or USE.
- One statement, no semicolons. Fully qualify every table.
- Aggregate rather than dumping rows for "how many", "how much" and "which" questions.
- Amounts are Indian rupees. Never call them dollars.
- If the tables genuinely cannot answer a data question, use the general shape
  and explain in "answer" what is missing.
"""

GENERAL_RULES = """You are the Wealth Wizard assistant, helping one member
understand their own spending record.

- Answer in 2-4 sentences of plain prose. No bullet lists, no headings.
- Amounts are Indian rupees; write them with the rupee sign, e.g. ₹24,11,225.96.
- This record holds expenses only. There is no income, savings or profit figure,
  so never imply one exists or offer a savings rate calculated from it.
- If a question needs figures you were not given, say plainly that you would need
  to look it up rather than estimating.
- Never mention how you are built, what model runs you, or the SQL you did not run.
"""

BANNED = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|CREATE|DROP|ALTER|TRUNCATE|GRANT|"
    r"REVOKE|CALL|EXECUTE|COPY|PUT|UNLOAD|USE|SET|UNSET|BEGIN|COMMIT|ROLLBACK|"
    r"SYSTEM\$)\b",
    re.IGNORECASE,
)


class AiError(Exception):
    """Anything that stops the analyst from answering."""


# --- key handling -----------------------------------------------------------
def find_key():
    """Snowflake secret first, then the key pasted into config.py."""
    try:
        import _snowflake

        secret = _snowflake.get_generic_secret_string(config.SECRET_NAME)
        if secret:
            return secret
    except Exception:
        pass
    try:
        if config.SECRET_NAME in st.secrets:
            return st.secrets[config.SECRET_NAME]
    except Exception:
        pass
    return (config.GEMINI_API_KEY or "").strip() or None


# --- transport --------------------------------------------------------------
def _call(api_key, system, turns, max_tokens=1400, timeout=90):
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": turns,
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
    }).encode()
    req = urllib.request.Request(
        config.GEMINI_ENDPOINT,
        data=body,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        if e.code in (400, 403):
            raise AiError(
                "The API rejected the key. Check the value pasted into config.py "
                f"or the Snowflake secret named {config.SECRET_NAME}. "
                f"Response: {detail}"
            ) from e
        if e.code == 404:
            raise AiError(
                "The API does not recognise the configured model. Change "
                f"GEMINI_MODEL in config.py. Response: {detail}"
            ) from e
        if e.code == 429:
            raise AiError("Rate limit reached on the Gemini API. Try again shortly.") from e
        raise AiError(f"The Gemini API returned {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise AiError(
            f"Could not reach {config.GEMINI_HOST}. Snowflake blocks outbound calls "
            "unless an external access integration for that host is attached to this "
            "app. Trial accounts cannot create one, in which case this page cannot "
            f"work on this account at all. Underlying error: {e.reason}"
        ) from e

    candidates = payload.get("candidates") or []
    if not candidates:
        blocked = (payload.get("promptFeedback") or {}).get("blockReason")
        raise AiError(f"No answer came back{f' (blocked: {blocked})' if blocked else ''}.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise AiError("The model returned an empty response.")
    return text


# --- sql guard --------------------------------------------------------------
# Three-part names, and two-part names whose first part is one of our schemas.
_THREE_PART = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b")
_SCHEMA_FIRST = re.compile(r"(?<![\w.])(" + "|".join(SCHEMAS.values()) + r")\.(\w+)\b", re.I)


def _canon_schema(name: str) -> str:
    """Map a mangled schema name back onto the real one by its layer prefix."""
    upper = name.upper()
    for prefix, real in SCHEMAS.items():
        if upper.startswith(prefix):
            return real
    return MART


def repair(sql: str) -> str:
    """Correct duplicated-name mangles such as WEALTH_WEALTH_WIZARD.

    The model reliably picks the right tables but sometimes doubles a word in the
    database or schema name. That is a spelling slip, not a different intent, so
    it is cheaper to fix it here than to spend a round trip asking again.
    """
    def three(m):
        db, schema, table = m.groups()
        if "WEALTH_WIZARD" in db.upper() or "WEALTH" in db.upper():
            db = DB
        if "WEALTH" in schema.upper():
            schema = _canon_schema(schema)
        return f"{db}.{schema}.{table}"

    fixed = _THREE_PART.sub(three, sql)
    # Bare SCHEMA.TABLE with the database omitted.
    fixed = _SCHEMA_FIRST.sub(lambda m: f"{DB}.{_canon_schema(m.group(1))}.{m.group(2)}", fixed)
    return fixed


def guard(sql: str, scope_user: str = None) -> str:
    """Accept one read-only SELECT against WEALTH_WIZARD, or raise.

    scope_user, when given, must appear in the statement. A signed-in member may
    only ever read their own rows, so a query that forgets the filter is refused
    rather than quietly returning the whole book.
    """
    if not sql or not sql.strip():
        raise AiError("No SQL was produced for that question.")
    clean = repair(sql.strip().rstrip(";").strip())
    if ";" in clean:
        raise AiError("Refused: more than one statement.")
    if not re.match(r"^\s*(SELECT|WITH)\b", clean, re.IGNORECASE):
        raise AiError("Refused: only SELECT or WITH statements run here.")
    if BANNED.search(clean):
        raise AiError("Refused: the statement contains a write or session keyword.")

    refs = _THREE_PART.findall(clean)
    if not refs:
        raise AiError("Refused: no fully qualified WEALTH_WIZARD table was referenced.")
    valid = set(SCHEMAS.values())
    for db, schema, table in refs:
        # Substring matching is not enough here: WEALTH_WIZARD is a substring of
        # WEALTH_WEALTH_WIZARD, which is how an invalid database slipped past.
        if db.upper() != DB:
            raise AiError(f"Refused: unexpected database '{db}' in {db}.{schema}.{table}.")
        if schema.upper() not in valid:
            raise AiError(f"Refused: unexpected schema '{schema}' in {db}.{schema}.{table}.")

    if scope_user and scope_user.upper() not in clean.upper():
        raise AiError("Refused: that query was not limited to your own records. "
                      "Ask about your own spending, budgets or insights.")
    return f"SELECT * FROM (\n{clean}\n) LIMIT {config.ROW_CAP}"


def extract_json(text: str) -> dict:
    body = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", body, re.DOTALL)
        if not match:
            raise AiError(f"Could not read the model's plan: {text[:200]}")
        return json.loads(match.group(0))


# --- the two-step answer ----------------------------------------------------
def _run(conn, sql, scope_user=None):
    """Execute guarded SQL, returning (dataframe, guarded_sql)."""
    guarded = guard(sql, scope_user)
    return conn.query(guarded), guarded


def _scope_note(user_id, name=None):
    if not user_id:
        return ""
    return f"""
You are answering for one signed-in member: USER_ID '{user_id}'{f" ({name})" if name else ""}.
Every SELECT must restrict to that member, by joining DIM_USER and filtering
USER_ID = '{user_id}'. Never return another member's rows, totals across all
members, or rankings of members. Say "your" rather than "the member's".
"""


def answer(conn, question: str, api_key: str, history=None, user_id=None, name=None):
    """Return (prose, executed_sql, dataframe, note).

    Data questions run SQL; general questions are answered directly. Which path a
    question takes is the model's call, made in the first exchange.
    """
    notes = context() + _scope_note(user_id, name)
    turns = []
    for msg in (history or [])[-6:]:
        role = "model" if msg["role"] == "assistant" else "user"
        turns.append({"role": role, "parts": [{"text": msg["content"]}]})
    turns.append({"role": "user", "parts": [{"text": question}]})

    plan = extract_json(_call(api_key, notes + SQL_RULES, turns, 1400))
    proposed = (plan.get("sql") or "").strip()

    # --- general question: no data needed ---
    if not proposed:
        direct = (plan.get("answer") or plan.get("reads") or "").strip()
        if direct:
            return direct, None, None, None
        prose = _call(api_key, notes + GENERAL_RULES, turns, 700)
        return prose, None, None, None

    # --- data question ---
    try:
        df, _ = _run(conn, proposed, user_id)
    except AiError:
        raise
    except Exception as first_error:
        # One correction round. A rejected statement is usually a wrong column or
        # a bad join, and the model fixes it when it can see the actual message.
        retry = turns + [{"role": "user", "parts": [{"text": (
            f"That SQL failed:\n{proposed}\n\nSnowflake said: {first_error}\n\n"
            "Return the corrected JSON object. Use only the columns listed in the "
            "schema notes and spell the database WEALTH_WIZARD."
        )}]}]
        plan = extract_json(_call(api_key, notes + SQL_RULES, retry, 1400))
        proposed = (plan.get("sql") or "").strip()
        if not proposed:
            raise AiError(f"That query could not be run: {first_error}") from first_error
        try:
            df, _ = _run(conn, proposed, user_id)
        except AiError:
            raise
        except Exception as second_error:
            raise AiError(f"That query could not be run: {second_error}") from second_error

    truncated = len(df) >= config.ROW_CAP
    preview = df.head(60).to_csv(index=False)
    followup = [{"role": "user", "parts": [{"text": (
        f"Question: {question}\n\nSQL run:\n{proposed}\n\n"
        f"Result ({len(df)} rows{' — capped' if truncated else ''}):\n{preview}\n\n"
        "Answer the question directly from these rows. Lead with the figure or name "
        "that answers it. Two or three sentences, no bullet lists. Amounts are Indian "
        "rupees: write them with the rupee sign and Indian grouping, e.g. "
        "₹24,11,225.96. Quote the numbers exactly as returned. Do not invent context "
        "that is not in the rows, and never mention income, savings or profit."
    )}]}]
    prose = _call(api_key, notes + GENERAL_RULES, followup, 700)
    note = f"Showing the first {config.ROW_CAP} rows." if truncated else None
    return prose, proposed, df, note
