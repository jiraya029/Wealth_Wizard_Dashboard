"""Wealth Wizard's look: tokens, and the components drawn from them.

Colour lives in CSS custom properties, set once per run by css(mode). Components
never name a colour directly, they reference a variable, so the light and dark
palettes are the only place a hue is decided. That is also why SVG fills are set
through style="fill:var(--x)" rather than the fill attribute: var() resolves in
CSS declarations, not in presentation attributes.

The palette is drawn from Indian banknote printing — ₹200 saffron, ₹100 lavender,
₹50 fluorescent blue, ₹20 greenish-yellow, ₹2000 magenta. The app counts in
rupees, so the notes are where its colours come from, and they supply enough
distinct hues for a twenty-slice ring without inventing any.
"""

import math

# --- tokens -----------------------------------------------------------------
PALETTES = {
    "dark": {
        "bg": "#14142B",        # deep intaglio indigo, not near-black
        "surf": "#1E1D3F",
        "raise": "#2A2851",
        "line": "rgba(234,231,245,.13)",
        "keyline": "rgba(242,160,61,.30)",
        "text": "#EAE7F5",
        "mute": "#9A93B8",
        "accent": "#F2A03D",    # ₹200
        "lav": "#A78BD0",       # ₹100
        "cyan": "#35A7C2",      # ₹50
        "ok": "#46B08D",
        "over": "#E8637F",      # ₹2000 magenta, pushed warm
        "flapA": "#E9E5F4",
        "flapB": "#CFC9E2",
        "flapText": "#16132E",
        "shadow": "rgba(0,0,0,.34)",
        "engrave": "rgba(242,160,61,.055)",
        "inputBg": "#191833",
        "slices": ["#F2A03D", "#35A7C2", "#A78BD0", "#E8637F", "#C9CE58",
                   "#46B08D", "#B57A52", "#8A9BE0", "#F0BE7A", "#7ED0B4",
                   "#C79ADD", "#9AA5C4"],
    },
    "light": {
        "bg": "#F1EFF7",        # lavender-tinted note paper, not cream
        "surf": "#FFFFFF",
        "raise": "#E7E3F2",
        "line": "rgba(34,29,60,.14)",
        "keyline": "rgba(180,105,14,.34)",
        "text": "#221D3C",
        "mute": "#635C7D",
        "accent": "#B4690E",    # saffron, darkened to hold contrast on paper
        "lav": "#6E52A8",
        "cyan": "#16748C",
        "ok": "#1B7A5E",
        "over": "#BE3350",
        "flapA": "#2B2550",     # inverted: ink tiles read on pale paper
        "flapB": "#1E1940",
        "flapText": "#F4F2FA",
        "shadow": "rgba(34,29,60,.16)",
        "engrave": "rgba(34,29,60,.05)",
        "inputBg": "#FFFFFF",
        "slices": ["#B4690E", "#16748C", "#6E52A8", "#BE3350", "#7A7E1C",
                   "#1B7A5E", "#8A5733", "#4A5CA8", "#A97317", "#2C8A6C",
                   "#8B4E9E", "#5A6480"],
    },
}

MODES = ("light", "dark")

DISPLAY = ("'Arial Narrow', 'Liberation Sans Narrow', 'Helvetica Neue', "
           "Helvetica, Arial, 'Nirmala UI', 'Noto Sans', sans-serif")
BODY = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, "
        "'Nirmala UI', 'Noto Sans', sans-serif")
# Consolas, Menlo and Nirmala UI all carry the rupee sign; the Noto and DejaVu
# fallbacks cover the older mono faces that would draw it as a missing-glyph box.
DATA = ("ui-monospace, SFMono-Regular, Menlo, Consolas, 'Nirmala UI', "
        "'Noto Sans Mono', 'DejaVu Sans Mono', 'Courier New', monospace")

RUPEE = "\u20b9"
SLICE_COUNT = len(PALETTES["dark"]["slices"])


# --- money ------------------------------------------------------------------
def _indian(digits: str) -> str:
    """Group an integer string the way rupees are read: 24,11,225 not 2,411,225.

    The last three digits stand alone, then pairs, which is what lakh and crore
    describe. Western grouping would misrepresent the figure to this audience.
    """
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    pairs = []
    while len(head) > 2:
        pairs.insert(0, head[-2:])
        head = head[:-2]
    if head:
        pairs.insert(0, head)
    return ",".join(pairs + [tail])


def money(value, dp=2, symbol=True):
    """Exact figure with the rupee sign and Indian grouping."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    whole, _, frac = f"{abs(v):.{dp}f}".partition(".")
    out = _indian(whole) + (f".{frac}" if frac else "")
    return f"{'-' if v < 0 else ''}{RUPEE if symbol else ''}{out}"


def compact(value, symbol=True):
    """Headline figure in the units rupees are spoken in: 37307016 -> ₹3.73 Cr."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    head = f"{sign}{RUPEE if symbol else ''}"
    for cut, suf in ((1e7, " Cr"), (1e5, " L")):
        if abs(v) >= cut:
            return f"{head}{abs(v) / cut:,.2f}{suf}"
    return f"{head}{_indian(f'{abs(v):.0f}')}"


def count(value):
    """Plain tally — never carries a currency sign."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


# --- stylesheet --------------------------------------------------------------
def css(mode="dark") -> str:
    p = PALETTES.get(mode, PALETTES["dark"])
    slices = "".join(f"--wb-s{i}:{c};" for i, c in enumerate(p["slices"]))
    return f"""
<style>
  :root {{
    --wb-bg: {p["bg"]}; --wb-surf: {p["surf"]}; --wb-raise: {p["raise"]};
    --wb-line: {p["line"]}; --wb-key: {p["keyline"]};
    --wb-text: {p["text"]}; --wb-mute: {p["mute"]};
    --wb-accent: {p["accent"]}; --wb-lav: {p["lav"]}; --wb-cyan: {p["cyan"]};
    --wb-ok: {p["ok"]}; --wb-over: {p["over"]};
    --wb-flap-a: {p["flapA"]}; --wb-flap-b: {p["flapB"]};
    --wb-flap-text: {p["flapText"]};
    --wb-shadow: {p["shadow"]}; --wb-engrave: {p["engrave"]};
    --wb-input: {p["inputBg"]};
    {slices}
  }}

  /* ---- ground ---- */
  /* Colour is set on the root and inherited. A blanket rule on p/span would
     out-specify the component classes below (.stApp span beats .wb-flap), which
     silently washes out the flap faces and the notes, so Streamlit's own text is
     named narrowly: classless paragraphs, labels, headings, list items. */
  .stApp, .stAppViewContainer {{ background: var(--wb-bg); color: var(--wb-text); }}
  .stApp p:not([class]), .stApp label, .stApp li,
  .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: var(--wb-text); }}

  /* Streamlit's floating toolbar sits over the first element, so the page needs
     real clearance beneath it rather than the default 1rem. */
  .block-container {{ padding-top: 3.6rem; max-width: 1500px; }}
  header[data-testid="stHeader"] {{ background: transparent; }}
  header[data-testid="stHeader"]::before {{ content: ""; position: absolute;
     inset: 0; background: linear-gradient(180deg, var(--wb-bg) 35%,
     transparent); }}
  @media (max-width: 760px) {{ .block-container {{ padding-top: 3rem; }} }}

  section[data-testid="stSidebar"] {{ background: var(--wb-surf);
     border-right: 1px solid var(--wb-key); }}
  /* Same reasoning as above — a universal selector here would flatten the
     eyebrow and the member id back to body colour. */
  section[data-testid="stSidebar"] p:not([class]),
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] li,
  section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {{ color: var(--wb-text); }}
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
  .stApp small {{ color: var(--wb-mute) !important; }}

  /* ---- masthead ---- */
  .wb-head {{ display: flex; align-items: flex-end; justify-content: space-between;
     gap: 1rem; flex-wrap: wrap; padding-bottom: .7rem;
     border-bottom: 1px solid var(--wb-line); }}
  .wb-head .name {{ font-family: {DISPLAY}; font-size: 2rem; line-height: 1;
     text-transform: uppercase; letter-spacing: .09em; color: var(--wb-text);
     margin: 0; font-weight: 700; }}
  .wb-head .name em {{ font-style: normal; color: var(--wb-accent); }}
  .wb-head .where {{ font-family: {DATA}; font-size: .68rem; letter-spacing: .2em;
     text-transform: uppercase; color: var(--wb-mute); margin-top: .3rem; }}
  .wb-lamp {{ display: inline-block; width: 6px; height: 6px; border-radius: 50%;
     background: var(--wb-accent); margin-right: .5rem; vertical-align: middle;
     animation: wb-pulse 2.6s ease-in-out infinite; }}
  @keyframes wb-pulse {{ 0%,100% {{ opacity: .35; }} 50% {{ opacity: 1; }} }}

  .wb-eyebrow {{ font-family: {DISPLAY}; font-size: .78rem; letter-spacing: .22em;
     text-transform: uppercase; color: var(--wb-accent); margin: 0 0 .35rem 0;
     font-weight: 700; }}
  .wb-rule {{ height: 1px; background: linear-gradient(90deg, var(--wb-key),
     transparent); margin-bottom: .5rem; }}
  .wb-sub {{ font-family: {BODY}; font-size: .8rem; color: var(--wb-mute);
     margin: 0 0 .6rem 0; }}
  .wb-hair {{ height: 1px; background: var(--wb-line); margin: 1.6rem 0 1.2rem; }}

  /* ---- split-flap tiles: the signature ---- */
  .wb-flaps {{ display: inline-flex; gap: 2px; font-family: {DATA};
     font-weight: 700; letter-spacing: .02em; }}
  .wb-flap {{ display: inline-block; min-width: .72em; text-align: center;
     padding: .12em .1em; border-radius: 2px; position: relative;
     background: linear-gradient(180deg, var(--wb-flap-a) 0 49.5%,
        var(--wb-flap-b) 50.5% 100%);
     color: var(--wb-flap-text); box-shadow: 0 1px 2px var(--wb-shadow);
     transform-origin: 50% 0; animation: wb-flip .34s ease-out both; }}
  .wb-flap::after {{ content: ""; position: absolute; left: 0; right: 0; top: 50%;
     height: 1px; background: var(--wb-shadow); }}
  .wb-flap.sep {{ background: none; box-shadow: none; color: var(--wb-mute);
     min-width: .3em; padding: .1em 0; }}
  .wb-flap.sep::after {{ display: none; }}
  @keyframes wb-flip {{
     0%   {{ transform: rotateX(-92deg); opacity: 0; }}
     60%  {{ transform: rotateX(8deg);   opacity: 1; }}
     100% {{ transform: rotateX(0);      opacity: 1; }} }}

  /* ---- the hero total ---- */
  .wb-hero {{ position: relative; overflow: hidden;
     background: var(--wb-surf); border: 1px solid var(--wb-key);
     border-radius: 5px; padding: 1.15rem 1.3rem 1.2rem; margin-bottom: 1rem;
     display: flex; align-items: flex-end; justify-content: space-between;
     gap: 1.4rem; flex-wrap: wrap; animation: wb-rise .42s ease-out both; }}
  /* Guilloché: the fine engraved line-work of security printing, kept faint
     enough to be texture rather than pattern. */
  .wb-hero::before {{ content: ""; position: absolute; inset: 0; pointer-events: none;
     background:
       repeating-linear-gradient(58deg, var(--wb-engrave) 0 1px, transparent 1px 7px),
       repeating-linear-gradient(-58deg, var(--wb-engrave) 0 1px, transparent 1px 7px); }}
  .wb-hero > * {{ position: relative; }}
  .wb-hero .lede {{ font-family: {DISPLAY}; font-size: .74rem; letter-spacing: .24em;
     text-transform: uppercase; color: var(--wb-accent); margin: 0 0 .55rem 0;
     font-weight: 700; }}
  .wb-hero .total {{ display: flex; align-items: center; gap: .5rem;
     font-size: 2.5rem; line-height: 1; }}
  .wb-hero .cur {{ font-family: {DATA}; font-size: 1.6rem; color: var(--wb-accent);
     font-weight: 600; }}
  .wb-hero .under {{ font-family: {BODY}; font-size: .8rem; color: var(--wb-mute);
     margin: .7rem 0 0 0; }}
  .wb-hero .aside {{ text-align: right; font-family: {DATA}; font-size: .72rem;
     color: var(--wb-mute); line-height: 1.9; }}
  .wb-hero .aside b {{ color: var(--wb-text); font-weight: 600; }}
  @media (max-width: 760px) {{
    .wb-hero .total {{ font-size: 1.7rem; }}
    .wb-hero .aside {{ text-align: left; }}
  }}

  /* ---- readout cards ---- */
  .wb-card {{ background: var(--wb-surf); border: 1px solid var(--wb-line);
     border-radius: 4px; padding: .85rem .95rem .9rem; height: 100%;
     display: flex; flex-direction: column;
     transition: transform .18s ease, border-color .18s ease;
     animation: wb-rise .4s ease-out both; }}
  .wb-card:hover {{ transform: translateY(-2px); border-color: var(--wb-key); }}
  .wb-card .cap {{ font-family: {DISPLAY}; font-size: .7rem; letter-spacing: .2em;
     text-transform: uppercase; color: var(--wb-mute); margin-bottom: .55rem; }}
  /* Quiet tabular figures. The flaps belong to the hero alone, otherwise the
     whole page flickers on every rerun and reads as a novelty. */
  .wb-card .fig {{ font-family: {DATA}; font-size: 1.32rem; color: var(--wb-text);
     font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.15;
     letter-spacing: -.01em; }}
  .wb-card .foot {{ font-family: {BODY}; font-size: .72rem; color: var(--wb-mute);
     margin-top: auto; padding-top: .55rem; }}
  .wb-card .foot b.up {{ color: var(--wb-over); }}
  .wb-card .foot b.down {{ color: var(--wb-ok); }}
  @keyframes wb-rise {{ from {{ opacity: 0; transform: translateY(7px); }}
                        to {{ opacity: 1; transform: none; }} }}

  /* ---- listings ---- */
  .wb-list {{ background: var(--wb-surf); border: 1px solid var(--wb-line);
     border-radius: 4px; overflow: hidden; }}
  table.wb-table {{ width: 100%; border-collapse: collapse; font-family: {DATA};
     font-size: .78rem; color: var(--wb-text); }}
  table.wb-table thead th {{ font-family: {DISPLAY}; font-size: .7rem;
     letter-spacing: .18em; text-transform: uppercase; color: var(--wb-accent);
     text-align: left; padding: .6rem .8rem; white-space: nowrap;
     border-bottom: 1px solid var(--wb-key); font-weight: 700; }}
  table.wb-table tbody td {{ padding: .48rem .8rem;
     border-bottom: 1px solid var(--wb-line); vertical-align: middle; }}
  table.wb-table tbody tr {{ animation: wb-rowin .34s ease-out both; }}
  table.wb-table tbody tr:hover {{ background: var(--wb-raise); }}
  table.wb-table td.num {{ text-align: right; font-variant-numeric: tabular-nums;
     white-space: nowrap; }}
  table.wb-table td.rank {{ color: var(--wb-mute); width: 2.2rem; }}
  table.wb-table td.dim {{ color: var(--wb-mute); }}
  table.wb-table td.wrap {{ white-space: normal; font-family: {BODY};
     font-size: .76rem; color: var(--wb-mute); max-width: 26rem; }}
  @keyframes wb-rowin {{ from {{ opacity: 0; transform: translateY(4px); }}
                         to {{ opacity: 1; transform: none; }} }}

  .wb-bar {{ height: 6px; background: var(--wb-raise); border-radius: 3px;
     overflow: hidden; min-width: 60px; }}
  .wb-bar i {{ display: block; height: 100%; background: var(--wb-accent);
     border-radius: 3px; animation: wb-grow .6s ease-out both; }}
  @keyframes wb-grow {{ from {{ transform: scaleX(0); transform-origin: left; }}
                        to {{ transform: scaleX(1); }} }}

  /* ---- budget envelopes ---- */
  .wb-env {{ background: var(--wb-surf); border: 1px solid var(--wb-line);
     border-radius: 4px; padding: .7rem .85rem; margin-bottom: .55rem;
     animation: wb-rise .4s ease-out both; }}
  .wb-env .top {{ display: flex; justify-content: space-between; gap: 1rem;
     align-items: baseline; margin-bottom: .45rem; }}
  .wb-env .cat {{ font-family: {DISPLAY}; font-size: .92rem; font-weight: 700;
     letter-spacing: .06em; text-transform: uppercase; color: var(--wb-text); }}
  .wb-env .amt {{ font-family: {DATA}; font-size: .78rem; color: var(--wb-text);
     font-variant-numeric: tabular-nums; }}
  .wb-env .track {{ height: 8px; background: var(--wb-raise); border-radius: 4px;
     overflow: hidden; }}
  .wb-env .track i {{ display: block; height: 100%; background: var(--wb-ok);
     border-radius: 4px; animation: wb-grow .65s ease-out both; }}
  .wb-env .track i.over {{ background: var(--wb-over); }}
  .wb-env .meta {{ font-family: {BODY}; font-size: .72rem; color: var(--wb-mute);
     margin-top: .4rem; }}

  .wb-chip {{ display: inline-block; font-family: {DATA}; font-size: .64rem;
     letter-spacing: .08em; text-transform: uppercase; padding: .1rem .4rem;
     border-radius: 2px; border: 1px solid currentColor; white-space: nowrap;
     font-weight: 700; }}
  .wb-chip.ok {{ color: var(--wb-ok); }}
  .wb-chip.over {{ color: var(--wb-over); }}
  .wb-chip.flag {{ color: var(--wb-accent); }}
  .wb-chip.mute {{ color: var(--wb-mute); }}

  .wb-empty {{ font-family: {BODY}; font-size: .86rem; color: var(--wb-mute);
     background: var(--wb-surf); border: 1px dashed var(--wb-line);
     border-radius: 4px; padding: 1.1rem; }}
  .wb-note {{ font-family: {BODY}; font-size: .78rem; color: var(--wb-mute);
     border-left: 2px solid var(--wb-accent); padding: .15rem 0 .15rem .65rem;
     margin: .6rem 0; }}

  /* ---- sign in ---- */
  .wb-gate {{ text-align: center; padding: 1rem 0 .4rem; }}
  .wb-gate .mark {{ font-size: 2.1rem; line-height: 1; }}
  .wb-gate .tag {{ font-family: {DISPLAY}; font-size: .78rem; letter-spacing: .3em;
     text-transform: uppercase; color: var(--wb-accent); margin: 1rem 0 .2rem;
     font-weight: 700; }}
  .wb-gate .say {{ font-family: {BODY}; font-size: .92rem; color: var(--wb-text);
     max-width: 34rem; margin: .5rem auto 0; line-height: 1.6; }}
  .wb-gate .say span {{ color: var(--wb-mute); }}

  .wb-who {{ display: flex; align-items: center; gap: .55rem;
     background: var(--wb-raise); border: 1px solid var(--wb-key);
     border-radius: 3px; padding: .5rem .6rem; margin: 0 0 .8rem 0; }}
  .wb-who .initial {{ width: 26px; height: 26px; border-radius: 3px; flex: none;
     background: var(--wb-accent); color: var(--wb-surf); font-family: {DISPLAY};
     font-weight: 700; font-size: .9rem; display: flex; align-items: center;
     justify-content: center; }}
  .wb-who .who {{ min-width: 0; }}
  .wb-who .nm {{ font-family: {BODY}; font-size: .8rem; color: var(--wb-text);
     white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .wb-who .id {{ font-family: {DATA}; font-size: .66rem; color: var(--wb-accent);
     letter-spacing: .1em; }}

  .wb-ring {{ transform-origin: 50% 50%;
     animation: wb-ring .62s cubic-bezier(.2,.75,.3,1) both; }}
  @keyframes wb-ring {{ from {{ opacity: 0; transform: rotate(-20deg) scale(.93); }}
                        to {{ opacity: 1; transform: none; }} }}
  .wb-dial {{ margin: 0 auto .6rem; }}

  .wb-key {{ display: flex; flex-direction: column; gap: .3rem; }}
  .wb-key div {{ display: flex; align-items: center; gap: .5rem;
     font-family: {DATA}; font-size: .74rem; color: var(--wb-text); }}
  .wb-key i {{ width: 10px; height: 10px; border-radius: 2px; flex: none; }}
  .wb-key span.v {{ margin-left: auto; color: var(--wb-mute);
     font-variant-numeric: tabular-nums; }}

  /* ---- streamlit's own controls, tuned to whichever mode is on ---- */
  .stTabs [data-baseweb="tab-list"] {{ gap: 1.5rem; background: transparent;
     border-bottom: 1px solid var(--wb-line); }}
  .stTabs [data-baseweb="tab"] {{ font-family: {DISPLAY}; font-size: .78rem;
     letter-spacing: .18em; text-transform: uppercase; color: var(--wb-mute);
     padding: .35rem 0; font-weight: 700; background: transparent; }}
  .stTabs [aria-selected="true"] {{ color: var(--wb-accent) !important; }}
  .stTabs [data-baseweb="tab-highlight"] {{ background: var(--wb-accent); }}

  .stButton button, .stDownloadButton button, .stFormSubmitButton button {{
     font-family: {DISPLAY}; letter-spacing: .16em; text-transform: uppercase;
     font-size: .74rem; font-weight: 700; border-radius: 2px;
     background: var(--wb-raise); color: var(--wb-text);
     border: 1px solid var(--wb-key); transition: background .16s ease; }}
  .stButton button:hover, .stDownloadButton button:hover,
  .stFormSubmitButton button:hover {{ background: var(--wb-accent);
     color: var(--wb-surf); border-color: var(--wb-accent); }}
  .stFormSubmitButton button[kind="primaryFormSubmit"],
  button[data-testid="stBaseButton-primaryFormSubmit"],
  button[data-testid="stBaseButton-primary"] {{ background: var(--wb-accent);
     color: var(--wb-surf); border-color: var(--wb-accent); }}

  /* Segmented controls and pills. Streamlit compiles the unselected face from
     config.toml, so in light mode it arrives dark-on-dark; both states are named
     here. This covers the appearance switch and the question openers alike. */
  [data-testid="stButtonGroup"] button {{ background: var(--wb-surf) !important;
     color: var(--wb-mute) !important; border: 1px solid var(--wb-line) !important;
     font-family: {BODY}; }}
  [data-testid="stButtonGroup"] button:hover {{ color: var(--wb-text) !important;
     border-color: var(--wb-key) !important; }}
  [data-testid="stButtonGroup"] button[aria-checked="true"],
  [data-testid="stButtonGroup"] button[aria-selected="true"] {{
     background: var(--wb-accent) !important; color: var(--wb-surf) !important;
     border-color: var(--wb-accent) !important; }}

  /* text fields, selects and their popovers */
  .stTextInput input, .stTextArea textarea, .stNumberInput input,
  [data-baseweb="input"], [data-baseweb="base-input"],
  [data-baseweb="select"] > div, [data-baseweb="textarea"] {{
     background: var(--wb-input) !important; color: var(--wb-text) !important;
     border-color: var(--wb-line) !important; }}
  /* Selects and multiselects paint their face on an emotion-generated div with no
     stable attribute of its own, so the inner fills are cleared and the wrapper
     carries the colour instead. The tag exception outranks the reset. */
  [data-testid="stSelectbox"] div, [data-testid="stMultiSelect"] div {{
     background-color: transparent !important; color: var(--wb-text) !important; }}
  [data-testid="stSelectbox"] > div, [data-testid="stMultiSelect"] > div {{
     background-color: var(--wb-input) !important; border-radius: 2px; }}
  [data-testid="stMultiSelect"] [data-baseweb="tag"],
  [data-testid="stMultiSelect"] [data-baseweb="tag"] span {{
     background-color: var(--wb-accent) !important;
     color: var(--wb-surf) !important; }}
  .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
     color: var(--wb-mute) !important; }}
  [data-baseweb="popover"] div, [data-baseweb="menu"], [role="listbox"],
  [data-baseweb="menu"] li {{ background: var(--wb-surf) !important;
     color: var(--wb-text) !important; }}
  [data-baseweb="menu"] li:hover, [role="option"]:hover {{
     background: var(--wb-raise) !important; }}
  [data-baseweb="tag"] {{ background: var(--wb-accent) !important;
     color: var(--wb-surf) !important; }}

  [data-testid="stExpander"] {{ background: var(--wb-surf);
     border: 1px solid var(--wb-line); border-radius: 4px; }}
  [data-testid="stExpander"] summary {{ color: var(--wb-text); }}
  [data-testid="stChatInput"], [data-testid="stChatInput"] textarea {{
     background: var(--wb-input) !important; color: var(--wb-text) !important; }}
  [data-testid="stChatMessage"] {{ background: var(--wb-surf);
     border: 1px solid var(--wb-line); border-radius: 4px; }}
  [data-testid="stDataFrame"] {{ border: 1px solid var(--wb-line);
     border-radius: 4px; }}
  [data-testid="stForm"] {{ border: 1px solid var(--wb-line);
     border-radius: 4px; background: var(--wb-surf); }}
  hr {{ border-color: var(--wb-line); }}
  *:focus-visible {{ outline: 2px solid var(--wb-accent) !important;
     outline-offset: 2px; }}

  @media (prefers-reduced-motion: reduce) {{
    .wb-flap, .wb-card, .wb-env, .wb-bar i, .wb-env .track i,
    table.wb-table tbody tr, .wb-lamp, .wb-ring, .wb-hero {{
      animation: none !important; }}
  }}
  @media (max-width: 760px) {{
    .wb-head .name {{ font-size: 1.5rem; }}
    .wb-card .fig {{ font-size: 1.15rem; }}
  }}
</style>
"""


# --- components --------------------------------------------------------------
def flaps(text, delay_step=0.035, cls="") -> str:
    tiles, i = [], 0
    for ch in str(text):
        sep = ch in " ,.:%/-+"
        style = f"animation-delay:{i * delay_step:.3f}s"
        tiles.append(f'<span class="wb-flap{" sep" if sep else ""}" style="{style}">'
                     f'{"&nbsp;" if ch == " " else ch}</span>')
        if not sep:
            i += 1
    return f'<span class="wb-flaps {cls}">{"".join(tiles)}</span>'


def card(cap, figure, foot="") -> str:
    """A readout. Figures are set plainly — the flaps are the hero's alone."""
    return (f'<div class="wb-card"><div class="cap">{cap}</div>'
            f'<div class="fig">{figure}</div>'
            f'<div class="foot">{foot}</div></div>')


def hero(lede, amount, under="", aside_rows=()) -> str:
    """The one flipping figure on the page: a total, in rupees.

    The currency sign is set beside the flaps rather than on one, because a board
    flap carries a digit — the denomination is printed on the housing.
    """
    digits = compact(amount, symbol=False)
    aside = "".join(f"<div>{label} <b>{value}</b></div>" for label, value in aside_rows)
    under_html = f'<p class="under">{under}</p>' if under else ""
    return (f'<div class="wb-hero"><div>'
            f'<p class="lede">{lede}</p>'
            f'<div class="total"><span class="cur">{RUPEE}</span>{flaps(digits)}</div>'
            f'{under_html}'
            f'</div><div class="aside">{aside}</div></div>')


def who(name, user_id) -> str:
    """Identity strip: who the figures on screen belong to."""
    initial = (str(name).strip()[:1] or "?").upper()
    return (f'<div class="wb-who"><div class="initial">{initial}</div>'
            f'<div class="who"><div class="nm">{name}</div>'
            f'<div class="id">{user_id}</div></div></div>')


def eyebrow(text, sub="") -> str:
    tail = f'<p class="wb-sub">{sub}</p>' if sub else ""
    return f'<p class="wb-eyebrow">{text}</p><div class="wb-rule"></div>{tail}'


def delta_foot(current, previous, label="vs previous month") -> str:
    """Spend going up is bad news here, so up reads as the warning colour."""
    try:
        cur, prev = float(current or 0), float(previous or 0)
    except (TypeError, ValueError):
        return label
    if not prev:
        return f"no {label.split()[-2]} {label.split()[-1]} to compare"
    pct = (cur - prev) / prev * 100
    arrow, cls = ("▲", "up") if pct > 0 else ("▼", "down")
    return f'<b class="{cls}">{arrow} {abs(pct):,.1f}%</b> {label}'


def donut(rows, size=240, thickness=26, centre_top="", centre_bottom="") -> str:
    """Ring of shares. rows: [(label, value)] already ordered."""
    total = sum(float(v or 0) for _, v in rows) or 1
    r = (size - thickness) / 2
    circ = 2 * math.pi * r
    cx = cy = size / 2
    segs, offset = [], 0.0
    for i, (_, value) in enumerate(rows):
        share = float(value or 0) / total
        length = share * circ
        if length <= 0:
            continue
        segs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" fill="none" '
            f'style="stroke:var(--wb-s{i % SLICE_COUNT})" '
            f'stroke-width="{thickness}" '
            f'stroke-dasharray="{length:.2f} {circ - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += length
    mid = ""
    if centre_top or centre_bottom:
        mid = (f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" '
               f'style="fill:var(--wb-text)" font-family="{DATA}" font-size="17" '
               f'font-weight="600">{centre_top}</text>'
               f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" '
               f'style="fill:var(--wb-mute)" font-family="{DISPLAY}" '
               f'font-size="10" letter-spacing="2">{centre_bottom}</text>')
    # One reveal on the whole ring rather than per slice: keyframes that read a
    # custom property are not resolved reliably, which left the ring incomplete.
    # The wrapper caps the width — a 100% SVG in a wide column grows to fill it,
    # which turned a 232px dial into a half-metre one.
    return (f'<div class="wb-dial" style="max-width:{size}px">'
            f'<svg width="100%" viewBox="0 0 {size} {size}" role="img" '
            f'aria-label="Share by category">'
            f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" fill="none" '
            f'style="stroke:var(--wb-raise)" stroke-width="{thickness}"/>'
            f'<g class="wb-ring">{"".join(segs)}</g>{mid}</svg></div>')


def key(rows, fmt=lambda v: f"{v:,.0f}", limit=8) -> str:
    """Legend beside the donut: name the leaders, summarise the tail."""
    total = sum(float(v or 0) for _, v in rows) or 1
    out = []
    for i, (label, value) in enumerate(rows[:limit]):
        share = float(value or 0) / total * 100
        out.append(f'<div><i style="background:var(--wb-s{i % SLICE_COUNT})"></i>'
                   f'{label}<span class="v">{fmt(float(value or 0))} '
                   f'· {share:,.1f}%</span></div>')
    rest = rows[limit:]
    if rest:
        spare = sum(float(v or 0) for _, v in rest)
        out.append(f'<div><i style="background:var(--wb-mute)"></i>'
                   f'{len(rest)} more<span class="v">{fmt(spare)} '
                   f'· {spare / total * 100:,.1f}%</span></div>')
    return f'<div class="wb-key">{"".join(out)}</div>'


def bars(rows, width=760, height=190, highlight=None) -> str:
    """Column chart. rows: [(label, value)], left to right."""
    if not rows:
        return ""
    top = max(float(v or 0) for _, v in rows) or 1
    pad_l, pad_r, pad_t, pad_b = 6, 6, 22, 26
    plot = height - pad_t - pad_b
    step = (width - pad_l - pad_r) / len(rows)
    bw = min(step * 0.62, 42)
    out = []
    for i, (label, value) in enumerate(rows):
        v = float(value or 0)
        h = max(v / top * plot, 1.5)
        x = pad_l + i * step + (step - bw) / 2
        y = pad_t + plot - h
        lit = highlight is not None and str(label) == str(highlight)
        tone = "var(--wb-accent)" if lit else "var(--wb-cyan)"
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
            f'rx="1" style="fill:{tone}" opacity="{1 if lit else .85}">'
            f'<animate attributeName="height" from="0" to="{h:.1f}" dur="0.55s" '
            f'begin="{i * 0.03:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="{pad_t + plot}" to="{y:.1f}" '
            f'dur="0.55s" begin="{i * 0.03:.2f}s" fill="freeze"/></rect>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{height - 10}" '
                   f'style="fill:{"var(--wb-accent)" if lit else "var(--wb-mute)"}" '
                   f'font-family="{DATA}" font-size="9.5" text-anchor="middle">'
                   f'{label}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{y - 5:.1f}" '
                   f'style="fill:var(--wb-text)" font-family="{DATA}" '
                   f'font-size="8.5" text-anchor="middle">'
                   f'{compact(v, symbol=False)}</text>')
    return (f'<svg width="100%" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="Column chart">{"".join(out)}</svg>')
