# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
COLORS = {
    "bg_primary": "#14151B",     # app background — deep ink
    "bg_secondary": "#1A1C24",   # sidebar / panel background
    "bg_card": "#1F212B",        # panel/notice background
    "bg_input": "#1A1C24",
    "border": "#2E313F",
    "border_soft": "#262835",
    "text_primary": "#EDEAE1",   # warm ivory
    "text_secondary": "#A6A6B3",
    "text_muted": "#6F7080",
    "accent": "#C9A24B",         # brass / antique gold
    "accent_soft": "rgba(201, 162, 75, 0.14)",
    "accent_strong": "#DDBA6C",
}

FONT_DISPLAY = "'Playfair Display', Georgia, serif"
FONT_BODY = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"


def get_css() -> str:
    # Return the full <style> block to inject once at app startup.
    # NOTE: this triple-quoted string is the actual CSS payload being
    # returned, not a comment/docstring — it has to stay a real string
    # literal so the CSS content inside it is preserved as-is.
    c = COLORS
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600;700&display=swap');

/* ---------------------------------------------------------------------- */
/* Base                                                                    */
/* ---------------------------------------------------------------------- */
html, body, [class*="css"] {{
    font-family: {FONT_BODY};
}}

.stApp {{
    background: linear-gradient(180deg, {c['bg_primary']} 0%, #17181F 100%);
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

/* ---------------------------------------------------------------------- */
/* Layout: col_list / col_content                                         */
/* ---------------------------------------------------------------------- */
/* Deliberately NOT fighting Streamlit's own layout engine here.
   st.container(height=LIST_HEIGHT) in inbox.py already gets a native,
   working fixed-height scroll box from Streamlit itself — no CSS needed
   for that to behave correctly.
   
   An earlier version of this file tried to *additionally* lock the whole
   page to exactly one viewport height (html/body/stMainBlockContainer at
   100vh + overflow:hidden) and re-derive every container's height via a
   chased-through-6-layers flex/height:100%/!important chain, so that the
   Email Content column would also stretch to the bottom of the screen
   Gmail-style. That fought Streamlit's own sizing for
   st.container(height=...) rather than working with it, and was the
   actual cause of two bugs: the inbox list rendering with less usable
   height than intended (rows past that clipped point were unreachable,
   not just "need to scroll"), and the Email Content column — squeezed by
   the same artificial 100vh/overflow:hidden constraint — clipping its own
   "Email Content" title.
   
   Simpler and far less fragile: just let the page scroll normally. The
   inbox list still scrolls on its own (that's Streamlit's native
   behavior, untouched), and the Email Content column renders in normal
   flow at whatever height its content needs — if that runs past one
   viewport, the page scrolls, same as any ordinary web page. */

/* ---------------------------------------------------------------------- */
/* Sidebar                                                                 */
/* ---------------------------------------------------------------------- */
section[data-testid="stSidebar"] {{
    background: {c['bg_secondary']};
    border-right: 1px solid {c['border']};
}}

section[data-testid="stSidebar"] .block-container {{
    padding-top: 2rem;
}}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    font-family: {FONT_DISPLAY};
    color: {c['text_primary']};
}}

/* ---------------------------------------------------------------------- */
/* App header / brand mark                                                */
/* ---------------------------------------------------------------------- */
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
    background: linear-gradient(90deg, {c['accent']} 0%, {c['border']} 45%, transparent 100%);
    margin: 0 0 1.8rem 0;
}}

/* ---------------------------------------------------------------------- */
/* Section labels (small caps eyebrow above a block)                      */
/* ---------------------------------------------------------------------- */
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

/* ---------------------------------------------------------------------- */
/* Buttons                                                                 */
/* ---------------------------------------------------------------------- */
.stButton > button {{
    background: transparent;
    color: {c['text_primary']};
    border: 1px solid {c['border']};
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

/* Streamlit wraps the label in its own nested divs (markdown container,
   then a flex div around the <p>) that carry their own inline
   justify-content: center — those need overriding too, not just the
   <button> itself, or the text stays centered regardless of the rule
   above. !important is needed since the inline styles otherwise win. */
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
    color: #16171D;
    font-weight: 600;
}}

.stButton > button[kind="primary"]:hover {{
    background: {c['accent_strong']};
    border-color: {c['accent_strong']};
    color: #16171D;
}}

/* ---------------------------------------------------------------------- */
/* Inputs                                                                  */
/* ---------------------------------------------------------------------- */
.stTextInput > div > div > input {{
    background: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 2px;
    font-family: {FONT_BODY};
}}

.stTextInput > div > div > input:focus {{
    border-color: {c['accent']};
    box-shadow: 0 0 0 1px {c['accent']};
}}

/* ---------------------------------------------------------------------- */
/* Tabs                                                                    */
/* ---------------------------------------------------------------------- */
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

/* ---------------------------------------------------------------------- */
/* Dividers                                                                */
/* ---------------------------------------------------------------------- */
hr {{
    border: none;
    border-top: 1px solid {c['border_soft']};
    margin: 0.9rem 0;
}}

/* ---------------------------------------------------------------------- */
/* Alerts / info / success boxes                                          */
/* ---------------------------------------------------------------------- */
.stAlert {{
    background: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: 3px;
}}

/* ---------------------------------------------------------------------- */
/* Small text used for account status in the sidebar                     */
/* ---------------------------------------------------------------------- */
.item-meta {{
    font-family: {FONT_BODY};
    font-size: 0.78rem;
    color: {c['text_muted']};
}}

/* ---------------------------------------------------------------------- */
/* Reading pane                                                            */
/* ---------------------------------------------------------------------- */
/* Wraps subject + meta in the same white "this is the actual email"
   surface the HTML body renders in (see ui/reader.py's components.html
   card) — before this, the subject/date sat on the app's dark theme
   while the body below was suddenly white, which read as a mismatched
   two-toned reader pane instead of one consistent email view. */
.reader-header {{
    background: #ffffff;
    border-radius: 6px 6px 0 0;
    padding: 18px 20px 14px 20px;
    margin-bottom: 0;
}}

.reader-subject {{
    font-family: {FONT_DISPLAY};
    font-size: 1.15rem;
    font-weight: 600;
    color: #1a1a1a;
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
    color: #5f6368;
}}

.reader-body {{
    font-family: {FONT_BODY};
    font-size: 0.95rem;
    line-height: 1.7;
    color: {c['text_primary']};
    white-space: pre-wrap;
}}

/* ---------------------------------------------------------------------- */
/* Attachment thumbnail grid (Gmail-style)                                */
/* ---------------------------------------------------------------------- */
/* flex-wrap + a fixed card width is what keeps a single attachment from
   stretching to fill the row — cards just wrap onto more lines as more
   attachments are added, same size either way. */
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
    background: #f1f3f4;
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

/* Small folded-corner ribbon in the bottom-right of the thumbnail,
   colored to match the file type — same visual cue Gmail uses on its
   attachment thumbnails. */
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

/* ---------------------------------------------------------------------- */
/* Empty / placeholder state ("Coming soon" notices)                     */
/* ---------------------------------------------------------------------- */
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
</style>
"""


# ---------------------------------------------------------------------------
# HTML helper snippets — used by ui/ modules for consistent markup
# ---------------------------------------------------------------------------

def brand_header(title: str, tagline: str) -> str:
    # Return the elegant serif brand header + tagline + hairline rule.
    # (Also a real returned HTML string, not a comment — kept as a
    # string literal for the same reason as get_css() above.)
    return f"""
<div class="brand-header">
    <span class="brand-mark">{title}</span>
</div>
<div class="brand-tagline">{tagline}</div>
<hr class="brand-rule" />
"""


def section_label(text: str) -> str:
    return f'<div class="section-label">{text}</div>'
