"""Interactive room for Water Buddy's evolving hydration pet."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from water_buddy.domain import progress_summary
from water_buddy.pet import (
    care_for_pet,
    daily_quests,
    equip_accessory,
    pet_snapshot,
    rename_pet,
)
from water_buddy.ui import mount_page_ambience, page_intro, render_pet
from water_buddy.units import format_volume, normalize_units

mount_page_ambience("pet")

_ACTION_PRESENTATION: dict[str, tuple[str, str, str]] = {
    "play": ("Play together", "toys_fan", "Lift happiness with a quick bubble game."),
    "rest": ("Cozy rest", "bedtime", "Restore energy in the calm corner."),
    "encourage": ("Pep talk", "campaign", "Share a little kindness and confidence."),
    "cheer": ("Cheer", "celebration", "Celebrate today’s hydration momentum."),
    "pet": ("Gentle pat", "back_hand", "A small moment of care for your companion."),
    "treat": ("Bubble treat", "bubble", "Offer a playful, pet-safe room treat."),
    "hydrate": ("Share a sip", "water_drop", "Let today’s water power the bond."),
}

_ACCESSORY_PRESENTATION: dict[str, str] = {
    "none": "Natural glow",
    "seafoam_bow": "Seafoam bow",
    "sunny_visor": "Sunny visor",
    "coral_crown": "Coral crown",
    "star_shell": "Star shell",
    "samurai_fit": "Samurai fit",
    "cyborg_fit": "Cyborg fit",
    "cool_guy_fit": "Cool guy fit",
    "leaf": "Sea leaf",
    "bow": "Coral bow",
    "glasses": "Bubble glasses",
    "scarf": "Current scarf",
    "star": "Tide star",
    "crown": "Sunken crown",
}

_OUTFIT_REWARDS: tuple[dict[str, Any], ...] = (
    {
        "id": "samurai_fit",
        "name": "Samurai fit",
        "icon": "swords",
        "min_level": 10,
        "description": "Disciplined tide-guard armor for a companion with serious flow.",
    },
    {
        "id": "cyborg_fit",
        "name": "Cyborg fit",
        "icon": "memory",
        "min_level": 15,
        "description": "Luminous future-tech plating powered by your hydration streaks.",
    },
    {
        "id": "cool_guy_fit",
        "name": "Cool guy fit",
        "icon": "mode_cool",
        "min_level": 20,
        "description": "The final laid-back look for a fully leveled hydration legend.",
    },
)


def _first(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return default


def _save_feedback(message: str) -> None:
    st.session_state.store.save(st.session_state.data)
    st.session_state.flash_message = message


def _equip_look(
    accessory_id: str,
    label: str,
    *,
    sync_selector: bool = False,
) -> None:
    try:
        result = equip_accessory(st.session_state.data, accessory_id)
    except (TypeError, ValueError) as error:
        st.error(str(error), icon=":material/error:")
        return

    result_message = (
        str(result.get("message", ""))
        if isinstance(result, Mapping)
        else ""
    )
    if sync_selector:
        st.session_state["pet_accessory_choice"] = accessory_id
    _save_feedback(result_message or f"{label} equipped.")
    st.rerun()


def _run_care_action(action_id: str, label: str) -> None:
    try:
        result = care_for_pet(st.session_state.data, action_id)
    except (TypeError, ValueError) as error:
        st.error(str(error), icon=":material/info:")
        return

    if isinstance(result, Mapping) and not bool(result.get("applied", True)):
        reason = str(result.get("message") or result.get("reason") or "That care action needs a little time before it can be used again.")
        st.session_state.store.save(st.session_state.data)
        st.warning(reason, icon=":material/schedule:")
        return

    result_message = (
        str(result.get("message", ""))
        if isinstance(result, Mapping)
        else ""
    )
    _save_feedback(result_message or f"{label} gave your pet a little boost.")
    st.rerun()


@st.dialog("Rename your hydration pet", icon=":material/edit:", width="small")
def _rename_pet_dialog(current_name: str) -> None:
    st.caption("Choose a short name that feels at home across your Water Buddy journey.")
    with st.form("pet_rename_form", border=False):
        new_name = st.text_input(
            "Pet name",
            value=current_name,
            max_chars=24,
            placeholder="Aqua",
        )
        submitted = st.form_submit_button(
            "Save name",
            type="primary",
            icon=":material/check:",
            width="stretch",
        )
    if not submitted:
        return

    try:
        result = rename_pet(st.session_state.data, new_name)
    except (TypeError, ValueError) as error:
        st.error(str(error), icon=":material/error:")
        return

    saved_name = (
        str(result.get("name", ""))
        if isinstance(result, Mapping)
        else str(new_name).strip()
    )
    st.session_state.data.setdefault("profile", {})["mascot_name"] = saved_name
    st.session_state.pop("profile_mascot_name", None)
    _save_feedback(f"Your hydration pet is now {saved_name or 'Aqua'}.")
    st.rerun()


def _catalog_entries(
    raw_catalog: Any,
    fallback_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Normalize a list/dict catalog without assuming a domain schema version."""

    entries: list[dict[str, Any]] = []
    if isinstance(raw_catalog, Mapping):
        iterable: Sequence[Any] = [
            ({"id": item_id, **value} if isinstance(value, Mapping) else {"id": item_id, "label": value})
            for item_id, value in raw_catalog.items()
        ]
    elif isinstance(raw_catalog, Sequence) and not isinstance(raw_catalog, (str, bytes)):
        iterable = raw_catalog
    else:
        iterable = list(fallback_ids)

    for raw_item in iterable:
        if isinstance(raw_item, Mapping):
            item_id = str(_first(raw_item, "id", "key", "action", "value", default="")).strip()
            if not item_id:
                continue
            entries.append(
                {
                    "id": item_id,
                    "label": str(_first(raw_item, "label", "title", "name", default=item_id)),
                    "description": str(_first(raw_item, "description", "hint", default="")),
                    "icon": str(_first(raw_item, "icon", default="auto_awesome")),
                    "locked": bool(raw_item.get("locked", False)) or raw_item.get("unlocked") is False,
                    "unlocked": raw_item.get("unlocked"),
                    "equipped": bool(raw_item.get("equipped", False)),
                    "min_level": _first(
                        raw_item,
                        "min_level",
                        "required_level",
                        "unlock_level",
                        default=1,
                    ),
                }
            )
        else:
            item_id = str(raw_item).strip()
            if item_id:
                entries.append(
                    {
                        "id": item_id,
                        "label": item_id,
                        "description": "",
                        "icon": "auto_awesome",
                        "locked": False,
                        "unlocked": True,
                        "equipped": False,
                        "min_level": 1,
                    }
                )
    return entries


def _action_entries(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_actions = _first(
        snapshot,
        "available_actions",
        "care_actions",
        "actions",
        default=None,
    )
    entries = _catalog_entries(raw_actions, ("play", "rest", "encourage"))
    for entry in entries:
        action_id = str(entry["id"]).casefold()
        presentation = _ACTION_PRESENTATION.get(action_id)
        if presentation:
            label, icon, description = presentation
            entry["label"] = label
            entry["icon"] = icon
            entry["description"] = entry["description"] or description
    return entries[:4]


def _accessory_entries(
    snapshot: Mapping[str, Any],
    pet_level: int,
) -> list[dict[str, Any]]:
    raw_accessories = _first(
        snapshot,
        "available_accessories",
        "unlocked_accessories",
        "accessories",
        default=None,
    )
    entries = _catalog_entries(
        raw_accessories,
        (
            "none",
            "leaf",
            "bow",
            "glasses",
            "scarf",
            "star",
            "crown",
            "samurai_fit",
            "cyborg_fit",
            "cool_guy_fit",
        ),
    )
    entries_by_id = {str(entry["id"]).casefold(): entry for entry in entries}
    for outfit in _OUTFIT_REWARDS:
        outfit_id = str(outfit["id"])
        if outfit_id not in entries_by_id:
            fallback = {
                "id": outfit_id,
                "label": outfit["name"],
                "description": outfit["description"],
                "icon": outfit["icon"],
                "locked": pet_level < int(outfit["min_level"]),
                "unlocked": pet_level >= int(outfit["min_level"]),
                "equipped": False,
                "min_level": outfit["min_level"],
            }
            entries.append(fallback)
            entries_by_id[outfit_id] = fallback

    outfit_details = {str(outfit["id"]): outfit for outfit in _OUTFIT_REWARDS}
    current_accessory = str(
        _first(snapshot, "equipped_accessory", "accessory", default="none")
    ).casefold()
    for entry in entries:
        entry_id = str(entry["id"]).casefold()
        outfit = outfit_details.get(entry_id)
        entry["label"] = _ACCESSORY_PRESENTATION.get(
            entry_id,
            str(entry["label"]).replace("_", " ").title(),
        )
        if outfit:
            entry["description"] = str(entry.get("description") or outfit["description"])
            entry["icon"] = str(entry.get("icon") or outfit["icon"])
        try:
            required_level = max(1, int(float(entry.get("min_level", 1))))
        except (TypeError, ValueError, OverflowError):
            required_level = int(outfit["min_level"]) if outfit else 1
        entry["min_level"] = required_level
        entry["locked"] = bool(entry.get("locked")) or pet_level < required_level
        entry["unlocked"] = not entry["locked"]
        entry["equipped"] = bool(entry.get("equipped")) or entry_id == current_accessory
    return sorted(entries, key=lambda entry: (int(entry["min_level"]), str(entry["label"])))


def _quest_entries(raw_quests: Any) -> list[Mapping[str, Any]]:
    if isinstance(raw_quests, Mapping):
        raw_quests = _first(raw_quests, "quests", "items", default=[])
    if not isinstance(raw_quests, Sequence) or isinstance(raw_quests, (str, bytes)):
        return []
    return [quest for quest in raw_quests if isinstance(quest, Mapping)]


data = st.session_state.data
summary = progress_summary(data)
preferences = data.get("preferences", {})
display_units = (
    normalize_units(preferences.get("units", "ml"))
    if isinstance(preferences, Mapping)
    else "ml"
)
if display_units not in {"ml", "oz"}:
    display_units = "ml"
snapshot_value = pet_snapshot(data)
snapshot: Mapping[str, Any] = (
    snapshot_value if isinstance(snapshot_value, Mapping) else {}
)

pet_name = str(_first(snapshot, "name", "pet_name", default="Aqua"))
try:
    pet_level = max(1, int(float(_first(snapshot, "level", default=1))))
except (TypeError, ValueError, OverflowError):
    pet_level = 1
pet_stage = str(
    _first(
        snapshot,
        "stage_label",
        "evolution_name",
        "evolution_stage",
        "stage",
        default="Dewdrop",
    )
)
pet_mood = str(_first(snapshot, "mood", "emotion", default="Content"))
accessory_entries = _accessory_entries(snapshot, pet_level)

page_intro(
    "Hydration pet",
    f"Welcome to {pet_name}’s room",
    "Your consistency gives this little water spirit energy, happiness, and new forms. Care for it, complete daily quests, and make the room your own.",
    f"Level {pet_level}",
)

render_pet(snapshot, summary["progress"])

st.subheader("Care & play")
st.caption("Care actions are gentle boosts. Your real hydration progress remains the strongest source of pet growth.")

actions = _action_entries(snapshot)
for row_start in range(0, len(actions), 4):
    row_actions = actions[row_start : row_start + 4]
    columns = st.columns(len(row_actions))
    for index, (column, action) in enumerate(zip(columns, row_actions)):
        action_id = str(action["id"])
        label = str(action["label"])
        with column.container(border=True, height="stretch"):
            st.markdown(f":material/{action['icon']}: **{label}**")
            st.caption(str(action["description"]) or "Spend a mindful moment together.")
            if st.button(
                label,
                key=f"pet_action_{row_start}_{index}",
                type="primary" if action_id.casefold() == "play" else "secondary",
                disabled=bool(action["locked"]),
                width="stretch",
            ):
                _run_care_action(action_id, label)

st.subheader("Level-up outfits")
st.caption(
    "Signature looks unlock through lifetime pet levels. Locked outfits stay visible so you always know what comes next."
)
outfits_by_id = {
    str(entry["id"]).casefold(): entry for entry in accessory_entries
}
outfit_columns = st.columns(3)
for outfit_column, outfit in zip(outfit_columns, _OUTFIT_REWARDS):
    outfit_id = str(outfit["id"])
    entry = outfits_by_id.get(outfit_id, outfit)
    required_level = int(entry.get("min_level", outfit["min_level"]))
    unlocked = not bool(entry.get("locked", pet_level < required_level))
    equipped = bool(entry.get("equipped", False))
    with outfit_column.container(border=True, height="stretch"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(
                f":material/{entry.get('icon', outfit['icon'])}: **{outfit['name']}**"
            )
            st.space("stretch")
            if equipped:
                st.badge("Equipped", icon=":material/check_circle:", color="green")
            elif unlocked:
                st.badge("Unlocked", icon=":material/lock_open:", color="blue")
            else:
                st.badge(
                    f"Level {required_level}",
                    icon=":material/lock:",
                    color="gray",
                )
        st.caption(str(entry.get("description") or outfit["description"]))
        st.progress(
            min(pet_level / required_level, 1.0),
            text=(
                "Ready to wear"
                if unlocked
                else f"Level {pet_level} of {required_level}"
            ),
        )
        button_label = (
            "Currently equipped"
            if equipped
            else "Equip outfit"
            if unlocked
            else f"Unlocks at level {required_level}"
        )
        button_icon = (
            ":material/check:"
            if equipped
            else ":material/checkroom:"
            if unlocked
            else ":material/lock:"
        )
        if st.button(
            button_label,
            icon=button_icon,
            key=f"pet_outfit_{outfit_id}",
            disabled=equipped or not unlocked,
            type="primary" if unlocked and not equipped else "secondary",
            width="stretch",
        ):
            _equip_look(outfit_id, str(outfit["name"]), sync_selector=True)

st.subheader("Room details")
wardrobe, quests_column = st.columns([.82, 1.18], gap="large")

with wardrobe:
    with st.container(border=True, height="stretch"):
        st.markdown(":material/checkroom: **Wardrobe**")
        st.caption("Unlocked looks are cosmetic — your pet stays itself underneath.")
        current_accessory = str(
            _first(snapshot, "equipped_accessory", "accessory", default="none")
        )
        unlocked_accessories = [
            item for item in accessory_entries if not bool(item.get("locked", False))
        ]
        if not any(
            str(item["id"]).casefold() == current_accessory.casefold()
            for item in unlocked_accessories
        ):
            unlocked_accessories.insert(
                0,
                {
                    "id": current_accessory,
                    "label": _ACCESSORY_PRESENTATION.get(current_accessory.casefold(), current_accessory.title()),
                    "locked": False,
                },
            )
        accessory_ids = [str(item["id"]) for item in unlocked_accessories]
        accessory_labels = {
            str(item["id"]): str(item["label"]) for item in unlocked_accessories
        }
        selector_key = "pet_accessory_choice"
        selected_state = str(st.session_state.get(selector_key, "")).casefold()
        if not any(
            accessory_id.casefold() == selected_state for accessory_id in accessory_ids
        ):
            st.session_state[selector_key] = (
                current_accessory
                if current_accessory in accessory_ids
                else accessory_ids[0]
            )
        selected_accessory = st.selectbox(
            "Choose an accessory",
            accessory_ids,
            format_func=lambda accessory_id: accessory_labels.get(accessory_id, accessory_id),
            key=selector_key,
        )
        if st.button(
            "Equip look",
            icon=":material/checkroom:",
            key="pet_equip_accessory",
            disabled=selected_accessory.casefold() == current_accessory.casefold(),
            width="stretch",
        ):
            equipped_label = accessory_labels.get(selected_accessory, selected_accessory)
            _equip_look(selected_accessory, equipped_label)

        if st.button(
            "Rename pet",
            icon=":material/edit:",
            key="open_pet_rename",
            width="stretch",
        ):
            _rename_pet_dialog(pet_name)

        st.space("small")
        with st.container(horizontal=True):
            st.metric("Level", pet_level, border=True)
            st.metric("Mood", pet_mood.title(), border=True)

with quests_column:
    with st.container(border=True, height="stretch"):
        st.markdown(":material/task_alt: **Today’s quests**")
        st.caption("Quests refresh with your day and reward ordinary healthy routines.")
        quests = _quest_entries(daily_quests(data))
        if not quests:
            st.info(
                "Your next quests are being prepared. Log a drink and check back.",
                icon=":material/hourglass_top:",
            )
        for quest_index, quest in enumerate(quests):
            title = str(_first(quest, "title", "name", default=f"Quest {quest_index + 1}"))
            description = str(_first(quest, "description", "hint", default="Build today’s hydration rhythm."))
            try:
                current = max(0, float(_first(quest, "current", "value", "progress_value", default=0)))
            except (TypeError, ValueError):
                current = 0
            try:
                target = max(1, float(_first(quest, "target", "goal", "max", default=1)))
            except (TypeError, ValueError):
                target = 1
            completed = bool(_first(quest, "completed", "complete", "done", default=current >= target))
            reward = _first(quest, "reward_xp", "xp", "reward", default=0)
            unit = str(_first(quest, "unit", default="")).strip()

            with st.container(border=True):
                heading, status = st.columns([1, .28], vertical_alignment="center")
                heading.markdown(f"**{title}**")
                if completed:
                    status.badge("Complete", icon=":material/check:", color="green")
                elif reward:
                    status.badge(f"+{reward} XP", icon=":material/auto_awesome:", color="blue")
                st.caption(description)
                display_current = min(current, target)
                unit_suffix = f" {unit}" if unit else ""
                progress_text = (
                    f"{format_volume(display_current, display_units)} of "
                    f"{format_volume(target, display_units)}"
                    if unit.casefold() == "ml"
                    else f"{display_current:g} of {target:g}{unit_suffix}"
                )
                st.progress(
                    min(current / target, 1.0),
                    text=progress_text,
                )

with st.expander("Evolution map", icon=":material/flare:"):
    st.caption("Your pet’s form changes as your lifetime bond grows. Accessories carry forward through every stage.")
    evolution_stages = (
        ("Dewdrop", "A tiny drop learning your rhythm."),
        ("Rippleling", "New fins appear as the bond strengthens."),
        ("Tidekin", "A confident companion powered by consistency."),
        ("Aqualume", "A radiant final form with an ocean-sized glow."),
    )
    stage_columns = st.columns(4)
    current_stage_token = pet_stage.casefold()
    for stage_column, (stage_name, stage_description) in zip(stage_columns, evolution_stages):
        with stage_column.container(border=True, height="stretch"):
            st.markdown(f"**{stage_name}**")
            st.caption(stage_description)
            if any(token in current_stage_token for token in stage_name.casefold().split()):
                st.badge("Current form", icon=":material/stars:", color="blue")
