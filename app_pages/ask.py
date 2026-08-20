"""Ask — questions about your own record, and general ones too."""

import streamlit as st

import ai
import theme as T
import ui

conn = ui.conn()
me = ui.member()
user_id = me["user_id"]
ym = ui.selected_ym()

ui.board_header("Ask <em>Wealth Wizard</em>", f"{ui.esc(user_id)} · your record, and general questions")

api_key = ai.find_key()

if not api_key:
    ui.eyebrow("Not connected yet")
    ui.empty(
        "Open <b>config.py</b> and paste your API key on line 9, or set the secret "
        "named there in your app secrets, then reload.<br><br>"
        "<b>Running inside a Snowflake trial account, this page cannot work.</b> "
        "Outbound calls need an external access integration, and trial accounts "
        "cannot create one. Every other page works without it."
    )
    st.stop()

ui.note("Questions about amounts are answered by querying your own records — each "
        "reply shows the SQL it ran. Anything general is answered directly. Only "
        "your rows are ever read.")

if "chat" not in st.session_state:
    st.session_state.chat = []

for turn in st.session_state.chat:
    with st.chat_message(turn["role"]):
        st.write(turn["content"])
        if turn.get("sql"):
            with st.expander("The query behind this answer"):
                st.code(turn["sql"], language="sql")
        if turn.get("table") is not None:
            st.dataframe(turn["table"], use_container_width=True, height=250)

if not st.session_state.chat:
    ui.eyebrow("Openers", "Pick one, or type your own below.")
    starters = [
        f"How much did I spend in {ui.ym_label(ym)}?" if ym else "How much have I spent in total?",
        "Which category do I spend the most on?",
        "What was my largest single transaction?",
        "What is a budget envelope?",
        "How can I bring my biggest category down?",
    ]
    chosen = st.pills("Openers", starters, label_visibility="collapsed")
    if chosen:
        st.session_state.chat.append({"role": "user", "content": chosen})
        st.rerun()

question = st.chat_input("Ask about your spending, or anything else")

pending = None
if question:
    pending = question
elif st.session_state.chat and st.session_state.chat[-1]["role"] == "user":
    pending = st.session_state.chat[-1]["content"]

if pending:
    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

    asked = pending
    if ym:
        asked += f"\n\n(The month on screen is {ui.ym_label(ym)}.)"

    with st.chat_message("assistant"):
        with st.spinner("Working…"):
            try:
                prose, sql, df, note = ai.answer(
                    conn, asked, api_key,
                    [t for t in st.session_state.chat[:-1]
                     if t["role"] in ("user", "assistant")],
                    user_id=user_id,
                    name=me.get("name"),
                )
            except ai.AiError as err:
                st.error(str(err))
                st.session_state.chat.append(
                    {"role": "assistant", "content": f"Could not answer: {err}"})
            except Exception as err:
                st.error(f"That did not work: {err}")
                st.session_state.chat.append(
                    {"role": "assistant", "content": f"That did not work: {err}"})
            else:
                st.write(prose)
                if note:
                    st.caption(note)
                if sql:
                    with st.expander("The query behind this answer"):
                        st.code(sql, language="sql")
                if df is not None:
                    st.dataframe(df, use_container_width=True, height=250)
                st.session_state.chat.append({
                    "role": "assistant", "content": prose, "sql": sql, "table": df})

if st.session_state.chat:
    st.button("Clear this conversation",
              on_click=lambda: st.session_state.pop("chat", None))
