"""Water Buddy's Streamlit entrypoint and shared application shell."""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from uuid import UUID

import streamlit as st

from water_buddy.audio import sound_bytes
from water_buddy.auth import AccountError, AccountStore
from water_buddy.domain import (
    WaterLogCooldownError,
    add_water,
    dismiss_reminder,
    normalize_theme,
    progress_summary,
    reminder_is_due,
    snooze_reminder,
)
from water_buddy.interaction_audio import mount_interface_sounds
from water_buddy.pet import pet_snapshot
from water_buddy.storage import JsonStore, StorageError
from water_buddy.streamlit_theme import mount_streamlit_theme
from water_buddy.ui import inject_global_styles, render_brand, render_pet
from water_buddy.units import format_volume

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = (
    Path(os.environ.get("WATER_BUDDY_DATA_DIR", APP_ROOT / "data"))
    .expanduser()
    .resolve()
)
ACCOUNT_PATH = DATA_DIR / "accounts.json"
USER_DATA_DIR = DATA_DIR / "users"

_USER_SCOPED_SESSION_KEYS = frozenset(
    {
        "account_init_error",
        "active_user_id",
        "auth_user",
        "cancel_full_reset",
        "cancel_reset_today",
        "celebrate_once",
        "confirm_full_reset",
        "confirm_reset_today",
        "data",
        "delete_selected_water_entry",
        "flash_message",
        "goal_minus_250",
        "goal_plus_250",
        "keep_selected_water_entry",
        "last_reminder_prompt",
        "open_delete_selected_entry",
        "open_full_reset",
        "open_pet_rename",
        "open_reset_today",
        "pending_water_buddy_restore",
        "save_profile_plan",
        "sound_event",
        "store",
        "today_entries_table",
        "undo_last_water",
    }
)
_USER_SCOPED_SESSION_PREFIXES = (
    "coach_",
    "custom_log_",
    "home_",
    "insights_",
    "log_",
    "pet_",
    "profile_",
    "reminder_",
    "reminders_",
    "restore_",
)

st.set_page_config(
    page_title="Water Buddy",
    page_icon=":material/water_drop:",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "About": "Water Buddy is your private, local-first hydration companion.",
    },
)


def _clear_mounted_user() -> None:
    """Remove every known user-bound value after invalid authentication.

    The account store and any ``login_`` form keys intentionally survive so the
    welcome page can recover without discarding an in-progress sign-in.
    """

    for key in list(st.session_state):
        if key in _USER_SCOPED_SESSION_KEYS or key.startswith(
            _USER_SCOPED_SESSION_PREFIXES
        ):
            st.session_state.pop(key, None)


def _initialize_app() -> None:
    """Initialize account state, then load the signed-in user's data."""

    if "account_store" not in st.session_state:
        try:
            st.session_state.account_store = AccountStore(ACCOUNT_PATH)
        except AccountError as error:
            st.session_state.account_init_error = error.user_message
            return
        else:
            st.session_state.pop("account_init_error", None)

    user = st.session_state.get("auth_user")
    if not isinstance(user, Mapping) or not user.get("user_id"):
        # Do not leave a previous profile mounted after sign-out or an app reload.
        _clear_mounted_user()
        return

    try:
        safe_user_id = UUID(str(user["user_id"])).hex
    except (ValueError, TypeError, AttributeError):
        _clear_mounted_user()
        return

    if (
        st.session_state.get("active_user_id") != safe_user_id
        or "store" not in st.session_state
        or "data" not in st.session_state
    ):
        user_path = USER_DATA_DIR / f"{safe_user_id}.json"
        store = JsonStore(user_path)
        primary_was_missing = not store.path.exists()
        backup_existed = store.backup_path.exists()
        is_new_profile = primary_was_missing and not backup_existed
        try:
            data = store.load()
            if is_new_profile:
                display_name = str(
                    user.get("display_name") or "Hydration hero"
                ).strip()
                data.setdefault("profile", {})["name"] = display_name[:48]
                store.save(data)
        except StorageError:
            st.session_state.account_init_error = (
                "Water Buddy could not safely open this hydration profile. "
                "The original data was not overwritten."
            )
            return

        if store.last_recovery_path is not None:
            if store.last_backup_recovery_path is not None:
                st.session_state.flash_message = (
                    "Damaged profile files were preserved and a safe new profile was "
                    "started. You can inspect the recovery copies in the data folder."
                )
            elif not backup_existed:
                st.session_state.flash_message = (
                    "Damaged profile data was preserved and a safe new profile was "
                    "started. You can inspect the recovery copy in the data folder."
                )
            else:
                st.session_state.flash_message = (
                    "Water Buddy recovered your profile from its safety backup."
                )
        elif store.last_backup_recovery_path is not None:
            if primary_was_missing:
                st.session_state.flash_message = (
                    "A damaged safety backup was preserved and a safe new profile "
                    "was started. You can inspect the recovery copy in the data "
                    "folder."
                )
            else:
                st.session_state.flash_message = (
                    "Water Buddy rebuilt a damaged safety backup while keeping your "
                    "profile intact."
                )
        elif primary_was_missing and backup_existed:
            st.session_state.flash_message = (
                "Water Buddy recovered your profile from its safety backup."
            )
        st.session_state.store = store
        st.session_state.data = data
        st.session_state.active_user_id = safe_user_id
        st.session_state.pop("account_init_error", None)

    st.session_state.setdefault("flash_message", None)
    st.session_state.setdefault("sound_event", None)
    st.session_state.setdefault("celebrate_once", False)
    st.session_state.setdefault("reminder_dialog_pending", False)
    st.session_state.setdefault("last_reminder_prompt", None)


def _sign_out() -> None:
    """End only the current browser session; persisted account data stays intact."""

    st.session_state.clear()


def _save_with_flash(message: str) -> None:
    st.session_state.store.save(st.session_state.data)
    st.session_state.flash_message = message


def _close_reminder_dialog() -> None:
    st.session_state.reminder_dialog_pending = False
    st.session_state.last_reminder_prompt = None

    data = st.session_state.get("data")
    if not isinstance(data, MutableMapping) or "store" not in st.session_state:
        return

    dismiss_reminder(data)
    _save_with_flash("Reminder dismissed. Your next one is scheduled.")


@st.dialog(
    "Time for a water break",
    width="small",
    icon=":material/water_drop:",
    on_dismiss=_close_reminder_dialog,
)
def _show_reminder_dialog() -> None:
    data = st.session_state.data
    summary = progress_summary(data)
    preferences = data.get("preferences", {})
    units = preferences.get("units", "ml") if isinstance(preferences, Mapping) else "ml"
    quick_amounts = (
        preferences.get("quick_log_amounts_ml", ())
        if isinstance(preferences, Mapping)
        else ()
    )
    try:
        reminder_amount_ml = (
            int(quick_amounts[0])
            if isinstance(quick_amounts, (list, tuple)) and quick_amounts
            else 250
        )
    except (TypeError, ValueError, OverflowError):
        reminder_amount_ml = 250
    if not 1 <= reminder_amount_ml <= 5000:
        reminder_amount_ml = 250
    reminder_amount_label = format_volume(reminder_amount_ml, units)
    reminder_pet = pet_snapshot(data)
    reminder_pet["speech"] = "A few mindful sips can reset your focus."
    render_pet(reminder_pet, summary["progress"], compact=True)

    guard_message: str | None = None
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if st.button(
            f"Log {reminder_amount_label}",
            type="primary",
            icon=":material/add:",
            key="reminder_log_water",
        ):
            before = summary["progress"]
            try:
                updated = add_water(data, reminder_amount_ml, source="Reminder")
            except WaterLogCooldownError as error:
                st.session_state.sound_event = None
                guard_message = (
                    f"{error.user_message} Sip Guard prevented an accidental "
                    "double-count; this interval is not drinking advice."
                )
            else:
                dismiss_reminder(data)
                if before < 1 <= updated["progress"]:
                    st.session_state.celebrate_once = True
                    st.session_state.sound_event = "goal"
                else:
                    st.session_state.sound_event = "water"
                _save_with_flash(f"{reminder_amount_label} added — nice work!")
                st.session_state.reminder_dialog_pending = False
                st.rerun()

        if st.button(
            "Snooze 10 min",
            icon=":material/snooze:",
            key="reminder_snooze",
        ):
            snooze_reminder(data, minutes=10)
            _save_with_flash("Reminder snoozed for 10 minutes.")
            st.session_state.reminder_dialog_pending = False
            st.rerun()

    if guard_message:
        st.warning(guard_message, icon=":material/shield:")

    if st.button(
        "Dismiss",
        type="tertiary",
        icon=":material/check:",
        key="reminder_dismiss",
        width="stretch",
    ):
        dismiss_reminder(data)
        _save_with_flash("Reminder dismissed. Your next one is scheduled.")
        st.session_state.reminder_dialog_pending = False
        st.rerun()


@st.fragment(run_every="15s")
def _reminder_watch() -> None:
    """Refresh only the reminder clock while the app tab is active."""

    data = st.session_state.data
    if not reminder_is_due(data):
        return

    token = data.get("preferences", {}).get("next_reminder_at") or "due"
    if st.session_state.last_reminder_prompt != token:
        st.session_state.last_reminder_prompt = token
        st.session_state.reminder_dialog_pending = True
        st.session_state.sound_event = "reminder"
        st.rerun()


_initialize_app()

session_data = st.session_state.get("data")
preferences = (
    session_data.get("preferences", {})
    if isinstance(session_data, Mapping)
    else {}
)
preferences = preferences if isinstance(preferences, Mapping) else {}
# Water Buddy's saved preference is the theme authority. Its four display
# themes also select the matching dark or light mode for Streamlit's shell.
theme = normalize_theme(preferences.get("theme", "Dark"))
background_motion = bool(preferences.get("background_motion", True))
sound_enabled = bool(preferences.get("sound_enabled", True))
interface_sound_volume = str(
    preferences.get("interface_sound_volume", "Balanced")
).title()
if interface_sound_volume not in {"Soft", "Balanced", "Vivid"}:
    interface_sound_volume = "Balanced"

inject_global_styles(theme, motion_enabled=background_motion)
mount_streamlit_theme(theme)
mount_interface_sounds(sound_enabled, interface_sound_volume)

account_init_error = st.session_state.get("account_init_error")
if account_init_error:
    render_brand()
    st.error(account_init_error, icon=":material/error:")
    st.caption(
        "Check that Water Buddy can write to its data folder, then reload the app."
    )
    with st.container(horizontal=True):
        if st.button("Retry", icon=":material/refresh:"):
            st.session_state.pop("account_init_error", None)
            st.rerun()
        st.button(
            "Sign out",
            icon=":material/logout:",
            type="tertiary",
            key="recovery_sign_out",
            on_click=_sign_out,
        )
    st.stop()

if "auth_user" not in st.session_state:
    login_navigation = st.navigation(
        [
            st.Page(
                "app_pages/login.py",
                title="Welcome",
                icon=":material/water_drop:",
                url_path="welcome",
                default=True,
            )
        ],
        position="hidden",
    )
    login_navigation.run()
    st.stop()

pages = {
    "": [
        st.Page(
            "app_pages/home.py",
            title="Home",
            icon=":material/home:",
            url_path="home",
            default=True,
        ),
        st.Page(
            "app_pages/log_water.py",
            title="Log water",
            icon=":material/water_drop:",
            url_path="log",
        ),
        st.Page(
            "app_pages/pet.py",
            title="Pet room",
            icon=":material/pets:",
            url_path="pet",
        ),
    ],
    "Progress": [
        st.Page(
            "app_pages/insights.py",
            title="Insights",
            icon=":material/monitoring:",
            url_path="insights",
        ),
        st.Page(
            "app_pages/achievements.py",
            title="Achievements",
            icon=":material/workspace_premium:",
            url_path="achievements",
        ),
    ],
    "Your plan": [
        st.Page(
            "app_pages/reminders.py",
            title="Reminders",
            icon=":material/notifications:",
            url_path="reminders",
        ),
        st.Page(
            "app_pages/coach.py",
            title="FLOW coach",
            icon=":material/chat_bubble:",
            url_path="coach",
        ),
        st.Page(
            "app_pages/profile.py",
            title="Profile",
            icon=":material/tune:",
            url_path="profile",
        ),
    ],
}

navigation = st.navigation(
    pages,
    position="sidebar",
    expanded=True,
)

account = st.session_state.auth_user
with st.sidebar:
    render_brand(compact=True)
    st.caption(
        f":material/lock: Signed in as **{account.get('display_name', 'Water Buddy')}**"
    )
    st.button(
        "Sign out",
        icon=":material/logout:",
        type="tertiary",
        key="account_sign_out",
        on_click=_sign_out,
    )

flash_message = st.session_state.pop("flash_message", None)
if flash_message:
    st.toast(flash_message, icon=":material/check_circle:")

sound_event = st.session_state.pop("sound_event", None)
if sound_event and sound_enabled:
    with st.container(key="sound-cue"):
        st.audio(sound_bytes(sound_event), autoplay=True, width=1)

reminders_enabled = bool(preferences.get("reminders_enabled", True))
daily_goal_complete = bool(progress_summary(st.session_state.data).get("goal_met"))
if reminders_enabled and not daily_goal_complete:
    _reminder_watch()
elif daily_goal_complete:
    st.session_state.reminder_dialog_pending = False
if st.session_state.reminder_dialog_pending:
    _show_reminder_dialog()

navigation.run()

st.space("large")
st.caption(
    "Water Buddy keeps this account's hydration data on this device. "
    "Guidance is educational and is not medical advice.",
    text_alignment="center",
)
