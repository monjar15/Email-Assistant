COLORS = {
    # Main display: light slate-blue canvas that the reader/content panels blend into.
    "bg_primary": "#EEF1F4",
    "bg_primary_deep": "#DCE1E6",  # subtle darker stop for the page gradient
    "bg_secondary": "#2C3E50",     # sidebar — deep navy slate
    "bg_card": "#EEF1F4",          # reader/email-content surface, matches bg_primary
    "bg_input": "#F7F9FB",
    "border": "#C9D2DA",
    "border_soft": "#DDE3E8",
    "text_primary": "#1F2937",
    "text_secondary": "#4B5563",
    "text_muted": "#7C8797",
    "accent": "#3B6EA5",
    "accent_soft": "rgba(59, 110, 165, 0.08)",
    "accent_strong": "#2C5680",
    # Sidebar-specific tokens, since its background is a dark navy slate.
    "sidebar_text": "#EDEFF2",
    "sidebar_text_muted": "#A9B4C0",
    "sidebar_border": "#45596E",
    "sidebar_btn_hover": "#3A4E62",
}

FONT_DISPLAY = "'Playfair Display', Georgia, serif"
FONT_BODY = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"


# Return the application CSS.
def get_css() -> str:
    c = COLORS
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600;700&display=swap');

/* Base */
html, body, [class*="css"] {{
    font-family: {FONT_BODY};
}}

.stApp {{
    background: {c['bg_card']};
    color: {c['text_primary']};
}}

h1, h2, h3, h4 {{
    font-family: {FONT_DISPLAY};
    font-weight: 600;
    color: {c['text_primary']};
    letter-spacing: 0.2px;
}}

p, span, div, label {{
    color: {c['text_primary']};
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: {c['bg_secondary']};
    border-right: 1px solid {c['sidebar_border']};
    min-width: 250px !important;
    width: 250px !important;
    max-width: 250px !important;
    transform: translateX(0) !important;
    visibility: visible !important;
    position: relative !important;
    left: auto !important;
    top: auto !important;
    bottom: auto !important;
    z-index: 999 !important;
    overflow-x: hidden !important;
    flex: 0 0 250px !important;
    cursor: default !important;
}}

/* The sidebar contrast. */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] label {{
    color: {c['sidebar_text']};
}}

section[data-testid="stSidebar"] .brand-tagline,
section[data-testid="stSidebar"] .section-label {{
    color: {c['sidebar_text_muted']};
}}

section[data-testid="stSidebar"] .block-container {{
    padding-top: 2rem;
}}

section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    min-width: 250px !important;
    width: 250px !important;
    max-width: 250px !important;
}}

section[data-testid="stSidebar"]::after {{
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 12px !important;
    background: transparent !important;
    cursor: default !important;
    pointer-events: auto !important;
    z-index: 2147483647 !important;
}}

[data-testid="stSidebarResizeHandle"],
[data-testid="stSidebarResizeHandle"] *,
[data-testid="stSidebarResizer"],
[data-testid="stSidebarResizer"] *,
[data-testid="stSidebarSplitter"],
[data-testid="stSidebarSplitter"] *,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarHeader"] button,
div[role="separator"],
div[role="separator"] *,
section[data-testid="stSidebar"] button[aria-label="Close sidebar"],
section[data-testid="stSidebar"] button[aria-label="Collapse sidebar"],
button[aria-label="Open sidebar"],
button[aria-label="Expand sidebar"],
button[title="Close sidebar"],
button[title="Collapse sidebar"],
button[title="Open sidebar"],
button[title="Expand sidebar"] {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}}

[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewContainer"] [data-testid="stMain"] {{
    margin-left: 0 !important;
    width: auto !important;
    max-width: none !important;
    min-width: 0 !important;
}}

/* Header */
.brand-header {{
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    margin-bottom: 0.15rem;
}}

.brand-mark {{
    font-family: {FONT_DISPLAY};
    font-size: 2.1rem;
    font-weight: 700;
    color: {c['text_primary']};
    letter-spacing: 0.3px;
}}

.brand-tagline {{
    font-family: {FONT_BODY};
    font-size: 0.82rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: {c['text_muted']};
    margin-top: -0.3rem;
    margin-bottom: 1.4rem;
}}

.brand-rule {{
    height: 1px;
    border: none;
    background: linear-gradient(
        90deg,
        {c['accent']} 0%,
        {c['border']} 45%,
        transparent 100%
    );
    margin: 0 0 1.8rem 0;
}}

.section-label {{
    font-family: {FONT_BODY};
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: {c['accent']};
    margin-bottom: 0.4rem;
    white-space: nowrap;
}}

/* Buttons */
.stButton > button {{
    background: {c['bg_primary']};
    color: {c['text_primary']};
    border: 1px solid {c['border_soft']};
    border-radius: 2px;
    font-family: {FONT_BODY};
    font-weight: 500;
    font-size: 0.85rem;
    letter-spacing: 0.6px;
    padding: 0.4rem 1.1rem;
    text-align: left !important;
    white-space: pre-line;
    line-height: 1.35;
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    justify-content: center !important;
    transition: all 0.18s ease;
}}

.stButton > button div,
.stButton > button p {{
    text-align: left !important;
    justify-content: flex-start !important;
    align-items: flex-start !important;
    width: 100%;
    margin: 0;
    line-height: 1.35;
}}

.stButton > button:hover {{
    border-color: {c['accent']};
    color: {c['accent_strong']};
    background: {c['accent_soft']};
}}

.stButton {{
    margin-bottom: 0.2rem;
}}

.stButton > button[kind="primary"] {{
    background: {c['accent']};
    border: 1px solid {c['accent']};
    color: #FFFFFF;
    font-weight: 600;
}}

.stButton > button[kind="primary"]:hover {{
    background: {c['accent_strong']};
    border-color: {c['accent_strong']};
    color: #FFFFFF;
}}

/* Sidebar buttons (e.g. the login button) blend with the sidebar's darker
   surface instead of the main canvas or the navy accent used elsewhere. */
section[data-testid="stSidebar"] .stButton > button {{
    background: {c['bg_secondary']};
    color: {c['sidebar_text']};
    border: 1px solid {c['sidebar_border']};
}}

section[data-testid="stSidebar"] .stButton > button:hover {{
    background: {c['sidebar_btn_hover']};
    border-color: {c['sidebar_border']};
    color: {c['sidebar_text']};
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: {c['bg_secondary']};
    border: 1px solid {c['sidebar_text']};
    color: {c['sidebar_text']};
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
    background: {c['sidebar_btn_hover']};
    border-color: {c['sidebar_text']};
    color: {c['sidebar_text']};
}}

/* Select / dropdown controls blend with the same surface they sit on. */
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    background: {c['accent_soft']};
    border: 1px solid {c['accent']};
    color: {c['text_primary']};
}}

.stSelectbox > div > div:hover,
.stMultiSelect > div > div:hover {{
    border-color: {c['accent_strong']};
}}

section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stMultiSelect > div > div {{
    background: {c['bg_secondary']};
    border: 1px solid {c['accent']};
    color: {c['sidebar_text']};
}}

section[data-testid="stSidebar"] .stSelectbox > div > div:hover,
section[data-testid="stSidebar"] .stMultiSelect > div > div:hover {{
    border-color: {c['sidebar_text']};
}}

/* The inbox row's "Select" checkbox (bulk-select) blends with the row
   background instead of Streamlit's default white checkbox face. */
html body [data-testid="stCheckbox"] label[data-rac] > span + div {{
    background-color: {c['bg_primary']} !important;
    border: 1px solid {c['accent']} !important;
    box-shadow: none !important;
}}

html body [data-testid="stCheckbox"] label[data-baseweb="checkbox"] > span {{
    background-color: {c['bg_primary']} !important;
    border: 1px solid {c['accent']} !important;
    box-shadow: none !important;
}}

html body [data-testid="stCheckbox"] label[data-rac][data-selected="true"] > span + div {{
    background-color: {c['accent']} !important;
    border-color: {c['accent']} !important;
}}

html body [data-testid="stCheckbox"] label[data-rac] > span + div svg {{
    fill: #FFFFFF !important;
}}

/* Inputs */
.stTextInput > div > div > input {{
    background: {c['bg_primary']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 2px;
    font-family: {FONT_BODY};
}}

.stTextInput > div > div > input::placeholder {{
    color: {c['text_primary']};
    opacity: 1;
}}

.stTextInput > div > div:focus-within {{
    border-color: {c['accent']} !important;
    box-shadow: 0 0 0 1px {c['accent']} !important;
}}

.st-key-inbox_toolbar
div[data-baseweb="input"][data-testid="stTextInputRootElement"]:focus-within,
.st-key-inbox_toolbar
div[data-baseweb="input"][data-testid="stTextInputRootElement"]:has(input[aria-label="Search"]:focus),
.st-key-inbox_toolbar
div[data-baseweb="input"][data-testid="stTextInputRootElement"]
div[data-baseweb="base-input"]:focus-within {{
    border-color: {c['accent']} !important;
    box-shadow: 0 0 0 1px {c['accent']} !important;
    outline: 0 !important;
}}

.st-key-inbox_toolbar
div[data-baseweb="input"][data-testid="stTextInputRootElement"]
div[data-baseweb="base-input"] > input:focus {{
    border-color: transparent !important;
    box-shadow: none !important;
    outline: 0 !important;
}}

section[data-testid="stSidebar"] .stNumberInput input {{
    background: {c['bg_secondary']};
    color: {c['sidebar_text']};
    border: 1px solid {c['sidebar_border']};
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 1.8rem;
    border-bottom: 1px solid {c['border']};
    background: transparent;
}}

.stTabs [data-baseweb="tab"] {{
    background: transparent;
    color: {c['text_secondary']};
    font-family: {FONT_BODY};
    font-weight: 500;
    font-size: 0.9rem;
    letter-spacing: 0.4px;
    padding: 0.6rem 0.1rem;
}}

.stTabs [aria-selected="true"] {{
    color: {c['accent']} !important;
    border-bottom: 2px solid {c['accent']} !important;
}}

hr {{
    border: none;
    border-top: 1px solid {c['border_soft']};
    margin: 0.9rem 0;
}}

.stAlert {{
    background: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: 3px;
}}

/* The login form's warning/caption text sits on the sidebar's darker
   surface, so it needs the sidebar text tokens rather than the main ones. */
section[data-testid="stSidebar"] .stAlert {{
    background: {c['bg_secondary']};
    border: 1px solid {c['sidebar_border']};
    color: {c['sidebar_text']};
}}

section[data-testid="stSidebar"] .stAlert p {{
    color: {c['sidebar_text']} !important;
}}

section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] .stCaption {{
    color: {c['sidebar_text_muted']} !important;
}}

.item-meta {{
    font-family: {FONT_BODY};
    font-size: 0.78rem;
    color: {c['text_muted']};
}}

/* Reader */
.reader-header {{
    background: {c['bg_card']};
    border: none;
    border-radius: 0;
    padding: 18px 20px 14px 20px;
    margin-bottom: 0;
}}

.reader-subject {{
    font-family: {FONT_DISPLAY};
    font-size: 1.15rem;
    font-weight: 600;
    color: {c['text_primary']};
    margin-bottom: 0.5rem;
}}

.reader-meta-row {{
    display: flex;
    align-items: center;
    gap: 10px;
}}

.reader-avatar {{
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    color: #fff;
    font-family: {FONT_BODY};
    font-size: 0.72rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.reader-meta {{
    font-family: {FONT_BODY};
    font-size: 0.78rem;
    color: {c['text_secondary']};
}}

.reader-body {{
    font-family: {FONT_BODY};
    font-size: 0.95rem;
    line-height: 1.7;
    color: {c['text_primary']};
    background: {c['bg_card']};
    white-space: pre-wrap;
}}

/* Attachments */
.attach-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 0.6rem;
}}

.attach-card {{
    display: block;
    width: 104px;
    text-decoration: none;
    cursor: pointer;
}}

.attach-thumb {{
    position: relative;
    width: 104px;
    height: 72px;
    background: {c['bg_input']};
    border: 1px solid {c['border_soft']};
    border-radius: 6px;
    overflow: hidden;
    transition: border-color 0.15s ease;
}}

.attach-card:hover .attach-thumb {{
    border-color: {c['accent']};
}}

.attach-badge {{
    position: absolute;
    left: 6px;
    bottom: 6px;
    color: #fff;
    font-family: {FONT_BODY};
    font-size: 0.56rem;
    font-weight: 700;
    letter-spacing: 0.2px;
    padding: 2px 5px;
    border-radius: 3px;
}}

.attach-corner {{
    position: absolute;
    bottom: 0;
    right: 0;
    width: 0;
    height: 0;
    border-style: solid;
    border-width: 0 0 16px 16px;
    border-color: transparent transparent transparent transparent;
}}

.attach-name {{
    margin-top: 4px;
    font-family: {FONT_BODY};
    font-size: 0.7rem;
    color: {c['text_secondary']};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.attach-card:hover .attach-name {{
    color: {c['accent_strong']};
}}

.empty-state {{
    font-family: {FONT_BODY};
    color: {c['text_muted']};
    font-size: 0.9rem;
    font-style: italic;
    padding: 1.5rem 0;
    text-align: center;
    border: 1px dashed {c['border']};
    border-radius: 3px;
    min-height: 55vh;
    display: flex;
    align-items: center;
    justify-content: center;
}}

/* ---------------------------------------------------------------------- */
/* Sticky inbox toolbar                                                    */
/* ---------------------------------------------------------------------- */
.st-key-inbox_toolbar {{
    position: sticky !important;
    top: 0.45rem !important;
    z-index: 100 !important;
    padding: 0.45rem 0 0.30rem 0 !important;
    margin-bottom: 0.20rem !important;
    background:
        linear-gradient(
            180deg,
            rgba(238, 241, 244, 0.99) 0%,
            rgba(238, 241, 244, 0.96) 78%,
            rgba(238, 241, 244, 0.90) 100%
        ) !important;
    border-bottom: none !important;
    box-shadow: none !important;
    backdrop-filter: blur(8px);
}}

.st-key-inbox_toolbar .section-label {{
    margin-bottom: 0.25rem !important;
}}

.inbox-range-label {{
    padding-top: 0.35rem;
    white-space: nowrap;
}}

/* Search and clear icon alignment */
.st-key-inbox_clear_search_icon,
.st-key-inbox_search_btn,
.st-key-refresh_inbox_icon {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-width: 40px !important;
    overflow: visible !important;
}}

/* Streamlit columns can clip fixed-width icon buttons by a pixel or two. */
.st-key-inbox_toolbar [data-testid="stHorizontalBlock"],
.st-key-inbox_toolbar [data-testid="column"],
.st-key-inbox_toolbar [data-testid="stColumn"] {{
    overflow: visible !important;
}}

.st-key-inbox_clear_search_icon .stButton,
.st-key-inbox_search_btn .stButton,
.st-key-refresh_inbox_icon .stButton {{
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}

.st-key-inbox_clear_search_icon button[data-testid^="stBaseButton"],
.st-key-inbox_search_btn button[data-testid^="stBaseButton"],
.st-key-refresh_inbox_icon button[data-testid^="stBaseButton"] {{
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;
    box-sizing: border-box !important;
    overflow: visible !important;
    padding: 0 !important;
    display: grid !important;
    place-items: center !important;

    background-color: #EEF1F4 !important;
    background-image: none !important;
    border: 1px solid #DDE3E8 !important;
    color: #1F2937 !important;
}}

.st-key-inbox_clear_search_icon button[data-testid^="stBaseButton"] > div,
.st-key-inbox_search_btn button[data-testid^="stBaseButton"] > div,
.st-key-refresh_inbox_icon button[data-testid^="stBaseButton"] > div,
.st-key-inbox_clear_search_icon button[data-testid^="stBaseButton"]
    [data-testid="stMarkdownContainer"],
.st-key-inbox_search_btn button[data-testid^="stBaseButton"]
    [data-testid="stMarkdownContainer"],
.st-key-refresh_inbox_icon button[data-testid^="stBaseButton"]
    [data-testid="stMarkdownContainer"] {{
    background: transparent !important;
}}

.st-key-inbox_clear_search_icon button[data-testid^="stBaseButton"]:hover,
.st-key-inbox_search_btn button[data-testid^="stBaseButton"]:hover,
.st-key-refresh_inbox_icon button[data-testid^="stBaseButton"]:hover {{
    background-color: rgba(59, 110, 165, 0.08) !important;
    border-color: #3B6EA5 !important;
    color: #2C5680 !important;
}}

.st-key-inbox_clear_search_icon [data-testid="stMarkdownContainer"],
.st-key-inbox_search_btn [data-testid="stMarkdownContainer"],
.st-key-refresh_inbox_icon [data-testid="stMarkdownContainer"],
.st-key-inbox_clear_search_icon .stButton > button div,
.st-key-inbox_clear_search_icon .stButton > button p,
.st-key-inbox_search_btn .stButton > button div,
.st-key-inbox_search_btn .stButton > button p,
.st-key-refresh_inbox_icon .stButton > button div,
.st-key-refresh_inbox_icon .stButton > button p {{
    width: auto !important;
    height: auto !important;
    min-width: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    display: grid !important;
    place-items: center !important;
    text-align: center !important;
    line-height: 1 !important;
}}

.st-key-inbox_clear_search_icon .stButton > button p {{
    transform: translateY(-1px) !important;
    font-size: 16px !important;
}}

.st-key-inbox_search_btn .stButton > button p,
.st-key-refresh_inbox_icon .stButton > button p {{
    transform: translate(1px, 1px) !important;
}}

/* Compact refresh / previous / next buttons */
.st-key-inbox_prev_page .stButton > button,
.st-key-inbox_next_page .stButton > button {{
    width: 30px !important;
    min-width: 30px !important;
    max-width: 30px !important;
    height: 30px !important;
    min-height: 30px !important;
    max-height: 30px !important;
    padding: 0 !important;
    display: grid !important;
    place-items: center !important;
}}

.st-key-inbox_prev_page [data-testid="stMarkdownContainer"],
.st-key-inbox_next_page [data-testid="stMarkdownContainer"],
.st-key-inbox_prev_page .stButton > button div,
.st-key-inbox_prev_page .stButton > button p,
.st-key-inbox_next_page .stButton > button div,
.st-key-inbox_next_page .stButton > button p {{
    width: auto !important;
    height: auto !important;
    margin: 0 !important;
    padding: 0 !important;
    display: grid !important;
    place-items: center !important;
    text-align: center !important;
    line-height: 1 !important;
}}

/* ---------------------------------------------------------------------- */
/* More compact inbox email cards                                          */
/* ---------------------------------------------------------------------- */
[class*="st-key-email_"] {{
    margin-bottom: 0.04rem !important;
}}

[class*="st-key-email_"] .stButton {{
    margin-bottom: 0 !important;
}}

[class*="st-key-email_"] .stButton > button {{
    min-height: 43px !important;
    padding: 0.25rem 0.72rem !important;
    font-size: 0.80rem !important;
    line-height: 1.15 !important;
    letter-spacing: 0.35px !important;
    border-width: 1.2px !important;
    border-color: #C7CCD1 !important;
}}

[class*="st-key-email_"] .stButton > button:hover {{
    border-color: #3B6EA5 !important;
}}

[class*="st-key-email_"] .stButton > button div,
[class*="st-key-email_"] .stButton > button p {{
    line-height: 1.15 !important;
    margin: 0 !important;
}}

[class*="st-key-email_"] .stButton > button[kind="primary"],
[class*="st-key-email_"] .stButton > button[kind="primary"] div,
[class*="st-key-email_"] .stButton > button[kind="primary"] p {{
    color: #FFFFFF !important;
}}

[class*="st-key-chk_"] {{
    padding-top: 0.22rem !important;
    margin-bottom: 0 !important;
}}

[class*="st-key-chk_"] [data-testid="stWidgetLabel"] {{
    display: none !important;
    width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}}

[class*="st-key-chk_"] [data-testid="stCheckbox"],
[class*="st-key-chk_"] [data-testid="stElementContainer"] {{
    width: fit-content !important;
}}

[data-testid="stHorizontalBlock"]:has([class*="st-key-chk_"]) {{
    gap: 0 !important;
}}


/* ---------------------------------------------------------------------- */
/* Stable fixed-header desktop workspace                                   */
/* ---------------------------------------------------------------------- */

/* Remove the Streamlit development bar that covers the application title. */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
#MainMenu {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
}}

/* The browser page does not compete with the panel scrollbars. */
html,
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow: hidden !important;
}}

[data-testid="stMainBlockContainer"] {{
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow: hidden !important;
    padding-top: 0.65rem !important;
    padding-bottom: 0.45rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
    max-width: 100% !important;
}}

/* MailMind title stays visible and is no longer covered. */
.st-key-app_brand_header {{
    position: sticky !important;
    top: 0 !important;
    z-index: 200 !important;
    padding: 0 !important;
    background:
        linear-gradient(
            180deg,
            rgba(238, 241, 244, 1) 0%,
            rgba(238, 241, 244, 0.98) 100%
        ) !important;
}}

.st-key-app_brand_header .brand-header {{
    margin-bottom: 0 !important;
}}

.st-key-app_brand_header .brand-mark {{
    font-size: 1.9rem !important;
    line-height: 1.08 !important;
}}

.st-key-app_brand_header .brand-tagline {{
    margin-top: 0.05rem !important;
    margin-bottom: 0.55rem !important;
}}

.st-key-app_brand_header .brand-rule {{
    margin: 0 0 0.35rem 0 !important;
}}

/* Preserve the working fixed-height Streamlit workspace. */
.st-key-mail_workspace,
.st-key-mail_workspace[data-testid="stVerticalBlockBorderWrapper"],
.st-key-mail_workspace > [data-testid="stVerticalBlockBorderWrapper"] {{
    height: calc(100dvh - 7.75rem) !important;
    max-height: calc(100dvh - 7.75rem) !important;
    min-height: 360px !important;
    overflow: hidden !important;
    box-shadow: none !important;
}}

.st-key-mail_workspace [data-testid="stHorizontalBlock"] {{
    width: 100% !important;
    height: 100% !important;
    min-width: 0 !important;
    min-height: 0 !important;
    align-items: stretch !important;
    overflow: hidden !important;
}}

/* Let both mail columns shrink inside the viewport instead of overflowing. */
.st-key-mail_workspace [data-testid="column"] {{
    min-width: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
}}

/* Inbox controls stay above the card list. */
.st-key-inbox_toolbar {{
    position: relative !important;
    top: auto !important;
    z-index: 20 !important;
    padding-top: 0.15rem !important;
    flex: 0 0 auto !important;
    background: rgba(238, 241, 244, 0.99) !important;
}}

/* Only the inbox cards scroll.
   Streamlit can place the fixed-height style on a nested border wrapper, so
   target both the keyed container and every matching wrapper inside it. */
.st-key-inbox_list_scroll,
.st-key-inbox_list_scroll[data-testid="stVerticalBlockBorderWrapper"],
.st-key-inbox_list_scroll > [data-testid="stVerticalBlockBorderWrapper"],
.st-key-inbox_list_scroll [data-testid="stVerticalBlockBorderWrapper"] {{
    height: calc(100dvh - 15.65rem) !important;
    max-height: calc(100dvh - 15.65rem) !important;
    min-height: 230px !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    scrollbar-gutter: stable;
    box-sizing: border-box !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: {c['bg_primary']} !important;
}}

/* Prevent the inner Streamlit row/columns from creating a horizontal scrollbar. */
.st-key-inbox_list_scroll [data-testid="stHorizontalBlock"],
.st-key-inbox_list_scroll [data-testid="column"] {{
    min-width: 0 !important;
    max-width: 100% !important;
}}

/* Small scroll-safe space after the last message so it is never clipped. */
.inbox-list-bottom-spacer {{
    display: block !important;
    width: 100% !important;
    height: 0.9rem !important;
    min-height: 0.9rem !important;
    flex: 0 0 0.9rem !important;
}}


/* Only the selected email body scrolls. */
.st-key-reader_content_scroll,
.st-key-reader_content_scroll[data-testid="stVerticalBlockBorderWrapper"],
.st-key-reader_content_scroll > [data-testid="stVerticalBlockBorderWrapper"],
.st-key-reader_content_scroll [data-testid="stVerticalBlockBorderWrapper"] {{
    height: calc(100dvh - 7rem) !important;
    max-height: calc(100dvh - 7rem) !important;
    min-height: 300px !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    scrollbar-gutter: stable;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}}

.st-key-reader_content_scroll .empty-state {{
    min-height: calc(100dvh - 10.15rem) !important;
    height: auto !important;
    max-width: 100% !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    border: 0 !important;
    box-shadow: none !important;
}}

/* Sidebar has its own scroll when needed. */
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    height: 100dvh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
}}

@media (max-height: 700px) {{
    .st-key-mail_workspace,
    .st-key-mail_workspace[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-mail_workspace > [data-testid="stVerticalBlockBorderWrapper"] {{
        height: calc(100dvh - 7.1rem) !important;
        max-height: calc(100dvh - 7.1rem) !important;
        min-height: 320px !important;
    }}

    .st-key-inbox_list_scroll,
    .st-key-inbox_list_scroll[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-inbox_list_scroll > [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-inbox_list_scroll [data-testid="stVerticalBlockBorderWrapper"] {{
        height: calc(100dvh - 14.7rem) !important;
        max-height: calc(100dvh - 14.7rem) !important;
        min-height: 210px !important;
    }}

    .st-key-reader_content_scroll,
    .st-key-reader_content_scroll[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-reader_content_scroll > [data-testid="stVerticalBlockBorderWrapper"] {{
        height: calc(100dvh - 8.05rem) !important;
        max-height: calc(100dvh - 8.05rem) !important;
        min-height: 270px !important;
    }}
}}

@media (max-width: 900px) {{
    html,
    body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {{
        height: auto !important;
        max-height: none !important;
        overflow-y: auto !important;
    }}

    .st-key-mail_workspace,
    .st-key-mail_workspace[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-mail_workspace > [data-testid="stVerticalBlockBorderWrapper"] {{
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
    }}

    .st-key-inbox_list_scroll,
    .st-key-reader_content_scroll {{
        height: 60dvh !important;
        max-height: 60dvh !important;
    }}
}}


/* Direct EMAIL CONTENT label—no wrapper container */
.reader-section-label {{
    margin: 0 0 0.35rem 0 !important;
    padding: 0 !important;
    border: 0 !important;
    box-shadow: none !important;
}}

</style>
"""


# Build the application header HTML.
def brand_header(title: str, tagline: str) -> str:
    return f"""
<div class="brand-header">
    <span class="brand-mark">{title}</span>
</div>
<div class="brand-tagline">{tagline}</div>
<hr class="brand-rule" />
"""


# Build a section label HTML block.
def section_label(text: str) -> str:
    return f'<div class="section-label">{text}</div>'
