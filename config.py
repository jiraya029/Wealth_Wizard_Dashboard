"""Settings for the Wealth Wizard console.

============================================================================
For Streamlit Cloud: set gemini_api_key in your app's Secrets (Settings > Secrets)
For local: set it in .streamlit/secrets.toml
============================================================================
"""

import streamlit as st

GEMINI_API_KEY = st.secrets.get("gemini_api_key", "")

# ---------------------------------------------------------------------------
# Everything below is wiring. You should not need to touch it.
# ---------------------------------------------------------------------------

# Model is fixed here on purpose so it never appears in the interface.
# If the API ever rejects it, change this one string.
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_ENDPOINT = (
    f"https://{GEMINI_HOST}/v1beta/models/{GEMINI_MODEL}:generateContent"
)

# Name of the Snowflake secret to use instead of the key above. If the secret
# exists and is attached to the app, it wins and the key above stays empty.
SECRET_NAME = "gemini_api_key"

# Hard cap on rows returned to the assistant from any generated query.
ROW_CAP = 200

# Cache lifetime for mart reads, in seconds.
CACHE_TTL = 600
