"""Water Buddy's local sign-in and account creation experience."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from water_buddy.auth import AccountError, AccountStore
from water_buddy.ui import mount_page_ambience, render_brand, render_pet

mount_page_ambience("welcome")

LOGGER = logging.getLogger(__name__)
APP_ROOT = Path(__file__).resolve().parents[1]


def _finish_sign_in(account: dict[str, str], welcome_message: str) -> None:
    """Attach a public account record to this browser session."""

    st.session_state.auth_user = account
    st.session_state.flash_message = welcome_message
    for key in (
        "login_create_password",
        "login_confirm_password",
        "login_signin_password",
    ):
        st.session_state.pop(key, None)
    st.rerun()


account_store = st.session_state.get("account_store")
if not isinstance(account_store, AccountStore):
    try:
        account_store = AccountStore(APP_ROOT / "data" / "accounts.json")
    except AccountError as error:
        st.error(error.user_message, icon=":material/error:")
        st.caption("Check that Water Buddy can write to its data folder, then reload.")
        st.stop()
    st.session_state.account_store = account_store

st.html(
    """
    <style>
      .wb-login-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .42rem .72rem;
        border: 1px solid color-mix(in srgb, var(--wb-cyan) 35%, transparent);
        border-radius: 999px;
        background: color-mix(in srgb, var(--wb-cyan) 9%, transparent);
        color: var(--wb-cyan);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
      }
      .wb-login-title {
        max-width: 12ch;
        margin: 1rem 0 .8rem;
        color: var(--wb-ink);
        font-size: clamp(2.5rem, 6vw, 5.3rem);
        line-height: .94;
        letter-spacing: -.065em;
      }
      .wb-login-title span {
        color: transparent;
        background: linear-gradient(110deg, var(--wb-cyan), var(--wb-blue), #9f8cff);
        -webkit-background-clip: text;
        background-clip: text;
      }
      .wb-login-lede {
        max-width: 47ch;
        margin: 0 0 1rem;
        color: var(--wb-muted);
        font-size: 1.02rem;
        line-height: 1.7;
      }
      .wb-login-proof {
        display: flex;
        flex-wrap: wrap;
        gap: .55rem;
        margin: .9rem 0 1.25rem;
      }
      .wb-login-proof span {
        padding: .46rem .68rem;
        border: 1px solid var(--wb-line);
        border-radius: 999px;
        background: var(--wb-card);
        color: var(--wb-muted);
        font-size: .76rem;
        font-weight: 700;
      }
      .wb-login-note {
        margin-top: .65rem;
        color: var(--wb-muted);
        font-size: .78rem;
        line-height: 1.55;
      }
      @media (max-width: 760px) {
        .wb-login-title { max-width: 14ch; }
      }
    </style>
    """
)

render_brand()
st.space("small")

story, access = st.columns([1.12, 0.88], gap="large", vertical_alignment="center")

with story:
    st.html(
        """
        <span class="wb-login-eyebrow">A calmer way to hydrate</span>
        <h1 class="wb-login-title">Meet the buddy that <span>grows with you.</span></h1>
        <p class="wb-login-lede">
          Every glass powers a tiny companion, builds your streak, and turns a daily
          health habit into a world you will want to return to.
        </p>
        <div class="wb-login-proof" aria-label="Water Buddy benefits">
          <span>Private on-device data</span>
          <span>No API key needed</span>
          <span>Pet XP from real hydration</span>
        </div>
        """
    )
    render_pet(
        {
            "name": "Ripple",
            "level": 4,
            "xp": 68,
            "xp_to_next": 100,
            "stage": "Little ripple",
            "stage_index": 2,
            "energy": 86,
            "happiness": 94,
            "mood": "curious",
            "speech": "Create your space and I will grow with every mindful sip.",
            "equipped_accessory": "leaf",
        },
        0.72,
        compact=True,
    )

with access:
    with st.container(border=True, key="login-access-card"):
        st.subheader("Welcome to Water Buddy", anchor=False)
        st.caption("Your progress waits behind one simple, local account.")

        mode = st.segmented_control(
            "Account action",
            ["Sign in", "Create account"],
            default="Sign in",
            selection_mode="single",
            label_visibility="collapsed",
            width="stretch",
            key="login_mode",
        )

        if mode == "Create account":
            with st.form("create_account_form", clear_on_submit=False, border=False):
                display_name = st.text_input(
                    "Your name",
                    max_chars=48,
                    autocomplete="name",
                    placeholder="Ava",
                )
                email = st.text_input(
                    "Email address",
                    max_chars=254,
                    autocomplete="email",
                    placeholder="you@example.com",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    max_chars=256,
                    autocomplete="new-password",
                    help="Use 8 characters or more; a unique passphrase works best.",
                    key="login_create_password",
                )
                confirmation = st.text_input(
                    "Confirm password",
                    type="password",
                    max_chars=256,
                    autocomplete="new-password",
                    key="login_confirm_password",
                )
                understands_local_storage = st.checkbox(
                    "I understand this preview stores my account on this device."
                )
                create_submitted = st.form_submit_button(
                    "Create my Water Buddy",
                    type="primary",
                    icon=":material/arrow_forward:",
                    width="stretch",
                )

            if create_submitted:
                if password != confirmation:
                    st.error("Those passwords do not match.", icon=":material/error:")
                elif not understands_local_storage:
                    st.warning(
                        "Please confirm that you understand the local storage note.",
                        icon=":material/info:",
                    )
                else:
                    try:
                        account = account_store.register(display_name, email, password)
                    except AccountError as error:
                        st.error(error.user_message, icon=":material/error:")
                    except Exception:
                        LOGGER.exception("Unexpected account creation failure")
                        st.error(
                            "Water Buddy could not create the account. Please try again.",
                            icon=":material/error:",
                        )
                    else:
                        _finish_sign_in(
                            account,
                            f"Welcome, {account['display_name']} — your new buddy is ready!",
                        )
        else:
            with st.form("sign_in_form", clear_on_submit=False, border=False):
                email = st.text_input(
                    "Email address",
                    max_chars=254,
                    autocomplete="email",
                    placeholder="you@example.com",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    max_chars=256,
                    autocomplete="current-password",
                    key="login_signin_password",
                )
                sign_in_submitted = st.form_submit_button(
                    "Enter Water Buddy",
                    type="primary",
                    icon=":material/login:",
                    width="stretch",
                )

            if sign_in_submitted:
                try:
                    account = account_store.authenticate(email, password)
                except AccountError as error:
                    st.error(error.user_message, icon=":material/error:")
                except Exception:
                    LOGGER.exception("Unexpected sign-in failure")
                    st.error(
                        "Water Buddy could not sign you in. Please try again.",
                        icon=":material/error:",
                    )
                else:
                    _finish_sign_in(
                        account,
                        f"Welcome back, {account['display_name']}!",
                    )

        st.html(
            """
            <p class="wb-login-note">
              Water Buddy does not send email or upload credentials. This local sign-in
              separates profiles for people sharing this computer.
            </p>
            """
        )

st.caption(
    "By continuing, you are creating a local-only wellness profile. "
    "Water Buddy provides general guidance, not medical advice.",
    text_alignment="center",
)
