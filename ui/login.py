"""Full-page login UI for the universal IMAP sign-in flow.

The existing provider detection, authentication, and saved-session logic are
preserved. Presentation and browser-input behavior are handled here.
"""

import html
import json

import streamlit as st
import streamlit.components.v1 as components

from controllers.microsoft_auth_controller import (
    get_microsoft_redirect_url,
    process_microsoft_callback,
    start_microsoft_login,
)
from email_handler.provider_detect import detect_provider
from services.auth_service import is_valid_email_address, login
from storage.session_store import create_session
from ui.markup import login_brand


def _render_login_dom_helpers(
    suppress_autofill: bool,
    has_email_error: bool,
    has_auth_error: bool,
) -> None:
    """Apply browser hints only; never rewrite or submit field values."""
    suppress_value = "true" if suppress_autofill else "false"
    email_error_value = "true" if has_email_error else "false"
    auth_error_value = "true" if has_auth_error else "false"
    components.html(
        f"""
        <script>
        (function() {{
          const root = window.parent;
          const doc = root.document;
          const suppressAutofill = {suppress_value};
          const hasEmailError = {email_error_value};
          const hasAuthError = {auth_error_value};

          // Remove every legacy login listener left by older app reruns. Those
          // handlers rewrote DOM values and could submit an older email value.
          if (root.__mailMindEnterHandler) {{
            doc.removeEventListener('keydown', root.__mailMindEnterHandler, true);
            root.__mailMindEnterHandler = null;
          }}
          if (root.__mailMindClickHandler) {{
            doc.removeEventListener('click', root.__mailMindClickHandler, true);
            root.__mailMindClickHandler = null;
          }}
          if (root.__mailMindTypingHandler) {{
            doc.removeEventListener('keydown', root.__mailMindTypingHandler, true);
            doc.removeEventListener('input', root.__mailMindTypingHandler, true);
            root.__mailMindTypingHandler = null;
          }}
          if (root.__mailMindFieldErrorClearHandler) {{
            doc.removeEventListener(
              'input',
              root.__mailMindFieldErrorClearHandler,
              true
            );
            root.__mailMindFieldErrorClearHandler = null;
          }}
          if (root.__mailMindLoginHelperTimer) {{
            root.clearInterval(root.__mailMindLoginHelperTimer);
            root.__mailMindLoginHelperTimer = null;
          }}
          root.__mailMindSyntheticLoginClick = false;
          root.__mailMindLastSubmit = 0;

          const getControls = () => ({{
            page: doc.querySelector('.st-key-login_page'),
            form: doc.querySelector('.st-key-login_form'),
            emailContainer: doc.querySelector('.st-key-login_email'),
            email: doc.querySelector('.st-key-login_email input'),
            passwordContainer: doc.querySelector('.st-key-login_password'),
            password: doc.querySelector('.st-key-login_password input'),
            button: doc.querySelector(
              '.st-key-login_form [data-testid="stFormSubmitButton"] button, ' +
              '.st-key-login_button button'
            )
          }});

          const hideApplyHints = () => {{
            doc.querySelectorAll(
              '.st-key-login_email *, .st-key-login_password *'
            ).forEach((element) => {{
              const value = (element.textContent || '').trim();
              if (value === 'Press Enter to apply') {{
                element.classList.add('mailmind-hidden-hint');
                element.setAttribute('aria-hidden', 'true');
              }}
            }});
          }};

          const applyAttributes = () => {{
            const {{
              page, emailContainer, email, passwordContainer, password, button
            }} = getControls();
            if (!page) return false;

            // Keep accessibility state in sync with the server-rendered error.
            // Visual error styling is handled entirely by CSS :has(...) selectors,
            // so it survives Streamlit DOM replacement and repeated identical errors.
            if (email) {{
              email.setAttribute('aria-invalid', hasEmailError ? 'true' : 'false');
            }}
            if (password) {{
              password.setAttribute('aria-invalid', hasAuthError ? 'true' : 'false');
            }}

            if (email) {{
              email.setAttribute('autocapitalize', 'off');
              email.setAttribute('autocorrect', 'off');
              email.setAttribute('spellcheck', 'false');
              email.setAttribute('autocomplete', 'off');
              email.setAttribute('name', 'mailmind_email_input');
              email.setAttribute('data-lpignore', 'true');
              email.setAttribute('data-1p-ignore', 'true');
              email.setAttribute('data-form-type', 'other');
            }}

            if (password) {{
              password.setAttribute('autocapitalize', 'off');
              password.setAttribute('autocorrect', 'off');
              password.setAttribute('spellcheck', 'false');
              password.setAttribute(
                'autocomplete',
                suppressAutofill ? 'new-password' : 'current-password'
              );
              password.setAttribute('name', 'mailmind_password_input');
              password.setAttribute('data-lpignore', 'true');
              password.setAttribute('data-1p-ignore', 'true');
              password.setAttribute('data-form-type', 'other');
            }}

            hideApplyHints();
            return true;
          }};

          // Submit with Enter anywhere on the login page, including while
          // the cursor is inside either field. Prevent Streamlit's first
          // "apply" Enter from swallowing the login submission, then click
          // the real form submit button once.
          const handleOutsideEnter = (event) => {{
            if (
              !event.isTrusted ||
              event.key !== 'Enter' ||
              event.repeat ||
              event.isComposing ||
              event.shiftKey ||
              event.ctrlKey ||
              event.altKey ||
              event.metaKey
            ) return;

            const {{ page, email, password, button }} = getControls();
            if (!page || !button || button.disabled) return;

            const now = Date.now();
            if (now - root.__mailMindLastSubmit < 700) return;
            root.__mailMindLastSubmit = now;

            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === 'function') {{
              event.stopImmediatePropagation();
            }}

            // Blur only to finish any active edit. The values themselves are
            // never rewritten, so validation always receives what is visible.
            if (event.target === email || event.target === password) {{
              event.target.blur();
            }}

            root.requestAnimationFrame(() => {{
              root.requestAnimationFrame(() => button.click());
            }});
          }};

          if (root.__mailMindStableEnterHandler) {{
            doc.removeEventListener(
              'keydown',
              root.__mailMindStableEnterHandler,
              true
            );
          }}
          root.__mailMindStableEnterHandler = handleOutsideEnter;
          doc.addEventListener(
            'keydown',
            root.__mailMindStableEnterHandler,
            true
          );

          // Keep server-side errors visible until the next explicit submit.
          // Browser autofill and Streamlit's value restoration can emit synthetic
          // input events; hiding errors on those events caused intermittent errors
          // that only appeared after a manual refresh.

          applyAttributes();
          let attempts = 0;
          root.__mailMindLoginHelperTimer = root.setInterval(() => {{
            applyAttributes();
            attempts += 1;
            if (attempts > 30) {{
              root.clearInterval(root.__mailMindLoginHelperTimer);
              root.__mailMindLoginHelperTimer = null;
            }}
          }}, 200);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def render_loading_page(
    title: str = "Signing you in",
    subtitle: str = "Please wait while we connect to your mailbox.",
    target=None,
) -> None:
    """Render a self-contained fixed overlay during login and inbox setup."""

    loading_html = f"""
<div role="status" aria-live="polite" class="login-loading-overlay">
  <div class="login-loading-card">
    <div class="login-loading-brand-row">
      <svg viewBox="0 0 72 72" aria-hidden="true" class="login-loading-logo">
        <defs>
          <linearGradient id="mailMindLoadingGradient" x1="9" y1="10" x2="64" y2="65" gradientUnits="userSpaceOnUse">
            <stop stop-color="#3A5674"></stop>
            <stop offset="1" stop-color="#28425B"></stop>
          </linearGradient>
        </defs>
        <path d="M14 17.5C10.96 17.5 8.5 19.96 8.5 23V49C8.5 52.04 10.96 54.5 14 54.5H25.5L36 44.5L46.5 54.5H58C61.04 54.5 63.5 52.04 63.5 49V23C63.5 19.96 61.04 17.5 58 17.5H47.5L36 28L24.5 17.5H14Z" fill="none" stroke="url(#mailMindLoadingGradient)" stroke-width="5.2" stroke-linejoin="round"></path>
        <path d="M9.5 23L31.7 42.2C34.15 44.32 37.85 44.32 40.3 42.2L62.5 23" fill="none" stroke="url(#mailMindLoadingGradient)" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round"></path>
      </svg>
      <div class="login-loading-brand-name">MailMind <span class="login-loading-brand-accent">AI</span></div>
    </div>
    <div class="login-loading-tagline">AI-Assisted Inbox &amp; Task Management</div>
    <div class="login-loading-content">
      <div aria-hidden="true" class="login-loading-spinner"></div>
      <div class="login-loading-title">{html.escape(title)}</div>
      <div class="login-loading-subtitle">{html.escape(subtitle)}</div>
    </div>
  </div>
</div>
"""
    renderer = target if target is not None else st
    renderer.markdown(loading_html.strip(), unsafe_allow_html=True)


def _visible_auth_error(result: dict) -> str:
    """Convert a technical IMAP failure into a stable user-facing message."""
    raw_error = str(result.get("error", ""))
    lowered_error = raw_error.lower()
    if "outlook.com requires oauth2" in lowered_error:
        return "Outlook.com requires the Continue with Microsoft button."
    if any(token in lowered_error for token in (
        "authenticationfailed",
        "invalid credentials",
        "login failed",
        "authenticate",
        "app password",
    )):
        return "Couldn't sign in. Check your email address and app password."
    return "Couldn't connect to the email server. Please try again."


def _set_form_error(slot, message: str, css_class: str) -> None:
    """Update a fixed error slot without relying on another browser refresh."""
    if message:
        slot.markdown(
            f'<p class="{css_class}">{html.escape(message)}</p>',
            unsafe_allow_html=True,
        )
    else:
        slot.empty()


def _queue_login_submit(email_address: str, password: str) -> bool:
    """Validate the visible form, then switch to a loading-only rerun."""
    email_address = (email_address or "").strip()
    password = password or ""

    st.session_state.login_error = ""
    st.session_state.login_email_error = ""
    st.session_state.microsoft_login_error = ""

    if not is_valid_email_address(email_address):
        st.session_state.login_email_error = (
            "Enter a complete email address, such as name@example.com."
        )
        return False

    if not password:
        st.session_state.login_error = "Enter your password to continue."
        return False

    # Snapshot exactly what the user submitted. Authentication happens on the
    # next rerun, where the login form is not rendered at all.
    st.session_state.pending_login_email = email_address
    st.session_state.pending_login_password = password
    st.session_state.login_authenticating = True
    st.rerun()
    return True


def _run_pending_login() -> None:
    """Authenticate while rendering only the full-page loading screen."""
    render_loading_page(
        title="Signing you in",
        subtitle="Checking your account and preparing a secure session.",
    )

    email_address = (
        st.session_state.get("pending_login_email") or ""
    ).strip()
    password = st.session_state.get("pending_login_password") or ""

    cache_key = f"detect::{email_address.lower()}"
    detection = st.session_state.get(cache_key)
    if detection is None:
        detection = detect_provider(email_address)
        st.session_state[cache_key] = detection

    if not detection.get("supported"):
        st.session_state.login_authenticating = False
        st.session_state.login_email_error = "Couldn't find this account"
        st.session_state.pending_login_password = ""
        st.rerun()

    result = login(email_address, password)
    if not result.get("success"):
        st.session_state.login_authenticating = False
        if result.get("field") == "email":
            st.session_state.login_email_error = (
                result.get("error") or "Couldn't find this account"
            )
        else:
            st.session_state.login_error = _visible_auth_error(result)
        st.session_state.pending_login_password = ""
        st.rerun()

    token = create_session(result["client"], email_address)
    st.session_state.imap_client = result["client"]
    st.session_state.logged_in = True
    st.session_state.email_address = email_address
    st.session_state.session_token = token
    st.session_state.post_login_loading = True
    st.session_state.login_authenticating = False
    st.session_state.login_error = ""
    st.session_state.login_email_error = ""
    st.session_state.pending_login_email = ""
    st.session_state.pending_login_password = ""
    st.query_params["s"] = token
    st.rerun()


def _render_microsoft_redirect_page() -> None:
    """Redirect the top-level browser tab to Microsoft.

    Streamlit rewrites ordinary external links to open in a new tab. A V1
    HTML component also runs inside a sandboxed iframe, so navigating directly
    from that iframe is unreliable. This helper creates the redirect anchor
    inside Streamlit's top-level document and clicks that anchor there. The
    current MailMind tab is therefore reused for Microsoft sign-in and for the
    OAuth callback.
    """
    redirect_url = get_microsoft_redirect_url()
    if not redirect_url:
        st.session_state.microsoft_login_active = False
        st.session_state.microsoft_login_error = (
            "Microsoft sign-in could not be opened. Click Continue with Microsoft again."
        )
        st.rerun()

    render_loading_page(
        title="Opening Microsoft sign-in",
        subtitle="You will return here automatically after approving mailbox access.",
    )

    # json.dumps safely quotes the URL for JavaScript without exposing the
    # client secret (the authorization URL never contains that secret).
    redirect_url_js = json.dumps(redirect_url)
    components.html(
        f"""
        <script>
        (function() {{
          const root = window.parent;
          const doc = root.document;
          const url = {redirect_url_js};
          const markerName = '__mailMindMicrosoftSameTabRedirect';
          const anchorId = 'mailmind-microsoft-same-tab-redirect';

          // Prevent repeated Streamlit reruns from navigating more than once
          // while the current page is leaving localhost.
          if (root[markerName] === url) return;
          root[markerName] = url;

          let anchor = doc.getElementById(anchorId);
          if (!anchor) {{
            anchor = doc.createElement('a');
            anchor.id = anchorId;
            anchor.style.display = 'none';
            anchor.setAttribute('aria-hidden', 'true');
            doc.body.appendChild(anchor);
          }}

          anchor.href = url;
          anchor.target = '_self';
          anchor.rel = 'noopener';

          // The anchor belongs to the top-level Streamlit document, not the
          // component iframe. Its explicit _self target keeps OAuth in one tab.
          root.requestAnimationFrame(() => anchor.click());
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def render_login_page() -> None:
    """Render login, process a Graph callback, or redirect to Microsoft."""
    if process_microsoft_callback():
        return

    if st.session_state.get("microsoft_login_active"):
        _render_microsoft_redirect_page()
        return

    if st.session_state.get("login_authenticating"):
        _run_pending_login()
        return

    suppress_autofill = bool(
        st.session_state.get("suppress_login_autofill", True)
    )

    with st.container(key="login_page"):
        left_space, card_column, right_space = st.columns([1.1, 0.95, 1.1])
        del left_space, right_space

        with card_column:
            with st.container(key="login_card"):
                st.markdown(login_brand(), unsafe_allow_html=True)

                with st.form(
                    key="login_form",
                    clear_on_submit=False,
                    enter_to_submit=True,
                    border=False,
                ):
                    email_address = st.text_input(
                        "Email address",
                        key="login_email",
                        placeholder="you@example.com",
                        autocomplete="off",
                    )
                    email_error_slot = st.empty()

                    password = st.text_input(
                        "Password",
                        type="password",
                        key="login_password",
                        placeholder="App password or account password",
                        autocomplete=(
                            "new-password"
                            if suppress_autofill
                            else "current-password"
                        ),
                    )
                    auth_error_slot = st.empty()

                    st.markdown(
                        '<p class="login-enter-hint">Press Enter to login</p>',
                        unsafe_allow_html=True,
                    )

                    login_clicked = st.form_submit_button(
                        "Login",
                        key="login_button",
                        type="primary",
                        use_container_width=True,
                    )

                if login_clicked:
                    _queue_login_submit(email_address, password)

                st.markdown(
                    '<div class="login-or-divider"><span>or</span></div>',
                    unsafe_allow_html=True,
                )

                microsoft_clicked = st.button(
                    "Continue with Microsoft",
                    key="microsoft_login_button",
                    type="primary",
                    use_container_width=True,
                )
                if microsoft_clicked:
                    if start_microsoft_login():
                        st.rerun()

                microsoft_error = st.session_state.get(
                    "microsoft_login_error", ""
                )
                if microsoft_error:
                    st.markdown(
                        f'<p class="login-auth-inline-error">{html.escape(microsoft_error)}</p>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    """
                    <p class="login-help-text">
                        Outlook/Hotmail accounts must use <strong>Continue with Microsoft</strong>.<br class="desktop-break" />
                        Gmail, Yahoo, and some other providers may require a generated<br class="desktop-break" />
                        <strong>app password</strong> when 2-factor authentication is enabled.
                    </p>
                    """,
                    unsafe_allow_html=True,
                )

                email_error = st.session_state.get("login_email_error", "")
                auth_error = st.session_state.get("login_error", "")
                _set_form_error(
                    email_error_slot,
                    email_error,
                    "login-email-inline-error",
                )
                _set_form_error(
                    auth_error_slot,
                    auth_error,
                    "login-auth-inline-error",
                )

                _render_login_dom_helpers(
                    suppress_autofill,
                    bool(email_error),
                    bool(auth_error),
                )
