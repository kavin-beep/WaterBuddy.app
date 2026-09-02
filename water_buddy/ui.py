"""Reusable visual primitives for the Water Buddy Streamlit app.

The components in this module intentionally use CSS-only motion.  They are
safe to render with :func:`streamlit.html`: every value that can originate in
application state is escaped before it is interpolated into markup, and no
JavaScript or remote asset is used.
"""

from __future__ import annotations

import html
import math
import re
from collections.abc import Mapping

import streamlit as st

from water_buddy.pet import hourly_pet_message
from water_buddy.units import format_volume

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_PAGE_AMBIENCE_VARIANTS = frozenset(
    {
        "welcome",
        "home",
        "log",
        "pet",
        "insights",
        "achievements",
        "reminders",
        "coach",
        "profile",
    }
)


def _escape(value: object) -> str:
    """Return an HTML-safe representation of an application value."""

    return html.escape(str(value), quote=True)


def _percent(progress: float, *, ratio_hint: bool = False) -> float:
    """Normalize a ratio or percentage without dropping over-goal progress.

    Hydration ratios can legitimately rise above ``1`` after the daily goal is
    complete.  ``ratio_hint`` keeps values such as ``1.25`` at a full 100%
    instead of misreading them as 1.25 percent.
    """

    try:
        value = float(progress)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    if 0.0 <= value <= (5.0 if ratio_hint else 1.0):
        value *= 100.0
    return min(100.0, max(0.0, value))


def _safe_color(value: str, fallback: str = "#2DD4BF") -> str:
    """Restrict CSS color values to a six-digit hexadecimal token."""

    candidate = str(value).strip()
    return _escape(candidate if _HEX_COLOR.fullmatch(candidate) else fallback)


def mount_page_ambience(page: str) -> None:
    """Mount a hidden, whitelisted route marker for CSS-only ambience."""

    candidate = page.strip().casefold() if isinstance(page, str) else ""
    variant = candidate if candidate in _PAGE_AMBIENCE_VARIANTS else "home"
    st.html(
        f'<span class="wb-page-ambience--{variant}" hidden aria-hidden="true"></span>',
        width="content",
    )


def inject_global_styles(
    theme: str = "Dark",
    motion_enabled: bool = True,
) -> None:
    """Install Water Buddy's explicit, accessible visual theme.

    The selected Water Buddy mode is authoritative and does not inherit colors
    from Streamlit's surrounding light/dark context. ``motion_enabled=False``
    pauses decorative and component motion while preserving every layout and
    state cue. The defaults keep existing zero- and one-argument calls valid.
    """

    requested_theme = str(theme).strip().casefold()
    palettes = {
        "dark": {
            "background": "#030817",
            "surface": "#09152C",
            "elevated": "#0E1D39",
            "field": "#FFFFFF",
            "field_text": "#10213D",
            "field_muted": "#526780",
            "overlay": "#071329F2",
            "text": "#FFFFFF",
            "muted": "#A4B5CE",
            "line": "#233657",
            "soft_line": "#182A49",
            "primary": "#2856D8",
            "royal": "#3157F6",
            "action_end": "#0E7490",
            "cyan": "#38D9F2",
            "aqua": "#2DD4BF",
            "violet": "#8B7CF6",
            "shadow": "#01040C",
            "scheme": "dark",
            "background_size": "auto",
        },
        "light": {
            "background": "#F5F8FE",
            "surface": "#FFFFFF",
            "elevated": "#EDF3FC",
            "field": "#F8FAFE",
            "field_text": "#10213D",
            "field_muted": "#526780",
            "overlay": "#FFFFFFF2",
            "text": "#10213D",
            "muted": "#526780",
            "line": "#C9D7EA",
            "soft_line": "#DDE6F2",
            "primary": "#1D4ED8",
            "royal": "#3157F6",
            "action_end": "#0E7490",
            "cyan": "#0891B2",
            "aqua": "#0F766E",
            "violet": "#6D28D9",
            "shadow": "#5B6F91",
            "scheme": "light",
            "background_size": "auto",
        },
        "japanese": {
            "background": "#F7F1E6",
            "surface": "#FFFDF8",
            "elevated": "#EFE5D5",
            "field": "#FBF6EC",
            "field_text": "#211A17",
            "field_muted": "#665A50",
            "overlay": "#FFFDF8F2",
            "text": "#211A17",
            "muted": "#665A50",
            "line": "#D8C9B8",
            "soft_line": "#E8DDCF",
            "primary": "#B4232E",
            "royal": "#7E1822",
            "action_end": "#3F7255",
            "cyan": "#B4232E",
            "aqua": "#3F7255",
            "violet": "#78516F",
            "shadow": "#5A4337",
            "scheme": "light",
            "background_size": "auto",
        },
        "cyber": {
            "background": "#02040B",
            "surface": "#080D19",
            "elevated": "#10192C",
            "field": "#FFFFFF",
            "field_text": "#10213D",
            "field_muted": "#526780",
            "overlay": "#050A14F2",
            "text": "#FFFFFF",
            "muted": "#AFBDD3",
            "line": "#2A3B5E",
            "soft_line": "#182741",
            "primary": "#7C3AED",
            "royal": "#D91B8C",
            "action_end": "#007C91",
            "cyan": "#00F5FF",
            "aqua": "#39FF9C",
            "violet": "#FF3DF2",
            "shadow": "#000000",
            "scheme": "dark",
            "background_size": "2.75rem 2.75rem, 2.75rem 2.75rem, auto, auto, auto",
        },
    }
    mode = requested_theme if requested_theme in palettes else "dark"
    palette = palettes[mode]
    color_scheme = palette["scheme"]
    if mode == "japanese":
        app_background = """
            radial-gradient(circle at 88% 10%, color-mix(in srgb, #C93643 18%, transparent) 0 5rem, transparent 5.1rem),
            repeating-linear-gradient(135deg, transparent 0 3rem, color-mix(in srgb, #8F5B43 4%, transparent) 3.05rem 3.1rem),
            radial-gradient(circle at 10% -8%, color-mix(in srgb, var(--wb-blue) 12%, transparent), transparent 31rem),
            radial-gradient(circle at 93% 8%, color-mix(in srgb, var(--wb-aqua) 10%, transparent), transparent 26rem)
        """
    elif mode == "cyber":
        app_background = """
            linear-gradient(color-mix(in srgb, var(--wb-cyan) 7%, transparent) 1px, transparent 1px),
            linear-gradient(90deg, color-mix(in srgb, var(--wb-violet) 6%, transparent) 1px, transparent 1px),
            radial-gradient(circle at 10% -8%, color-mix(in srgb, var(--wb-violet) 25%, transparent), transparent 31rem),
            radial-gradient(circle at 93% 8%, color-mix(in srgb, var(--wb-cyan) 19%, transparent), transparent 26rem),
            radial-gradient(circle at 52% 112%, color-mix(in srgb, var(--wb-aqua) 10%, transparent), transparent 30rem)
        """
    else:
        app_background = """
            radial-gradient(circle at 10% -8%, color-mix(in srgb, var(--wb-blue) 18%, transparent), transparent 31rem),
            radial-gradient(circle at 93% 8%, color-mix(in srgb, var(--wb-cyan) 13%, transparent), transparent 26rem),
            radial-gradient(circle at 52% 112%, color-mix(in srgb, var(--wb-violet) 9%, transparent), transparent 30rem)
        """
    motion_override = "" if bool(motion_enabled) else """
        .stApp::before,
        .stApp::after,
        .stApp *,
        [data-baseweb="popover"] *,
        [data-testid="stPopoverBody"] * {
            animation: none !important;
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
        }
        .stApp::before,
        .stApp::after {
            will-change: auto !important;
        }
        .wb-confetti {
            display: none !important;
        }
    """

    st.html(
        f"""
        <style>
        /* ---------- Explicit Water Buddy design tokens ---------- */
        :root,
        .stApp {{
            --wb-bg: {palette["background"]};
            --wb-surface: {palette["surface"]};
            --wb-elevated: {palette["elevated"]};
            --wb-field: {palette["field"]};
            --wb-field-ink: {palette["field_text"]};
            --wb-field-muted: {palette["field_muted"]};
            --wb-overlay: {palette["overlay"]};
            --wb-ink: {palette["text"]};
            --wb-muted: {palette["muted"]};
            --wb-cyan: {palette["cyan"]};
            --wb-aqua: {palette["aqua"]};
            --wb-blue: {palette["primary"]};
            --wb-royal: {palette["royal"]};
            --wb-action-end: {palette["action_end"]};
            --wb-violet: {palette["violet"]};
            --wb-route-primary: var(--wb-cyan);
            --wb-route-secondary: var(--wb-blue);
            --wb-route-tertiary: var(--wb-aqua);
            --wb-warning: #F59E0B;
            --wb-danger: #FB7185;
            --wb-card: color-mix(in srgb, var(--wb-surface) 76%, transparent);
            --wb-line: {palette["line"]};
            --wb-soft-line: {palette["soft_line"]};
            --wb-shadow: 0 24px 70px color-mix(in srgb, {palette["shadow"]} 28%, transparent);
            --wb-glow: 0 18px 60px color-mix(in srgb, var(--wb-cyan) 24%, transparent);
            --primary-color: {palette["primary"]};
            --background-color: {palette["background"]};
            --secondary-background-color: {palette["surface"]};
            --text-color: {palette["text"]};
            --border-color: {palette["line"]};
            color-scheme: {color_scheme};
        }}

        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .stApp {{
            background: var(--wb-bg) !important;
            color: var(--wb-ink) !important;
        }}

        .stApp {{
            position: relative;
            isolation: isolate;
            min-height: 100vh;
            background: {app_background}, var(--wb-bg) !important;
            background-size: {palette["background_size"]};
            color: var(--wb-ink);
        }}

        /* Water Buddy owns every readable surface. These rules intentionally
           override Streamlit's host light/dark mode after each app rerun. */
        .stApp :where(
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stMetric"],
            [data-testid="stExpander"],
            [data-testid="stForm"],
            [data-testid="stStatusWidget"],
            [data-testid="stAlert"],
            [data-testid="stAlertContainer"],
            [data-testid="stFileUploaderDropzone"],
            [data-testid="stDataFrame"],
            [data-testid="stTable"]
        ) {{
            border-color: var(--wb-line) !important;
            background-color: var(--wb-surface) !important;
            color: var(--wb-ink) !important;
        }}

        .stApp :where(
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stMetric"],
            [data-testid="stExpander"],
            [data-testid="stForm"],
            [data-testid="stStatusWidget"],
            [data-testid="stAlert"],
            [data-testid="stAlertContainer"]
        ) :where(h1, h2, h3, h4, h5, h6, p, span, label, li, strong) {{
            color: var(--wb-ink) !important;
        }}

        .stApp :where(
            [data-baseweb="input"],
            [data-baseweb="textarea"],
            [data-baseweb="select"] > div,
            [data-testid="stNumberInputContainer"],
            [data-testid="stDateInputField"],
            [data-testid="stDateTimeInputField"],
            [data-testid="stTimeInput"] > div,
            [data-testid="stMultiSelect"] > div,
            [data-testid="stChatInput"]
        ) {{
            border-color: var(--wb-line) !important;
            background-color: var(--wb-field) !important;
            color: var(--wb-ink) !important;
        }}

        .stApp :where(input, textarea),
        .stApp [data-baseweb="select"] :where(div, span),
        .stApp [data-testid="stMultiSelect"] :where(div, span),
        .stApp [data-testid="stButtonGroup"] button {{
            color: var(--wb-ink) !important;
        }}

        [data-baseweb="popover"] :where(div, span, p, label, li),
        [data-testid="stPopoverBody"] :where(div, span, p, label, li),
        [data-testid="stDialog"] :where(h1, h2, h3, h4, p, span, label, li) {{
            color: var(--wb-ink) !important;
        }}

        .stApp::before,
        .stApp::after {{
            content: "";
            position: fixed;
            z-index: -1;
            pointer-events: none;
            will-change: transform, opacity;
        }}

        .stApp::before {{
            inset: -24vh -18vw;
            opacity: .58;
            background:
                radial-gradient(ellipse at 18% 26%, color-mix(in srgb, var(--wb-blue) 27%, transparent), transparent 31%),
                radial-gradient(ellipse at 78% 18%, color-mix(in srgb, var(--wb-cyan) 21%, transparent), transparent 28%),
                radial-gradient(ellipse at 58% 78%, color-mix(in srgb, var(--wb-violet) 16%, transparent), transparent 34%);
            filter: blur(56px) saturate(112%);
            animation: wb-aurora-drift 22s ease-in-out infinite alternate;
        }}

        .stApp::after {{
            inset: 0;
            opacity: .32;
            background-image:
                radial-gradient(circle, color-mix(in srgb, var(--wb-cyan) 48%, transparent) 0 1px, transparent 1.8px),
                radial-gradient(circle, color-mix(in srgb, var(--wb-blue) 36%, transparent) 0 1.6px, transparent 2.4px),
                radial-gradient(circle, color-mix(in srgb, var(--wb-aqua) 30%, transparent) 0 2px, transparent 2.8px);
            background-position: 7% 15%, 58% 62%, 88% 28%;
            background-size: 9.5rem 12rem, 15rem 17rem, 21rem 23rem;
            mask-image: linear-gradient(to bottom, #000 0%, rgba(0,0,0,.72) 70%, transparent 100%);
            animation: wb-background-bubbles 34s linear infinite;
        }}

        /* ---------- Route-specific ambient motion ---------- */
        .wb-page-ambience--welcome,
        .wb-page-ambience--home,
        .wb-page-ambience--log,
        .wb-page-ambience--pet,
        .wb-page-ambience--insights,
        .wb-page-ambience--achievements,
        .wb-page-ambience--reminders,
        .wb-page-ambience--coach,
        .wb-page-ambience--profile {{
            display: none !important;
        }}

        .stApp :where(
            [data-testid="stElementContainer"],
            .stElementContainer
        ):has(> .stHtml > :is(
            .wb-page-ambience--welcome,
            .wb-page-ambience--home,
            .wb-page-ambience--log,
            .wb-page-ambience--pet,
            .wb-page-ambience--insights,
            .wb-page-ambience--achievements,
            .wb-page-ambience--reminders,
            .wb-page-ambience--coach,
            .wb-page-ambience--profile
        )) {{
            display: none !important;
        }}

        /* Each route owns a three-note decorative palette. These tokens never
           replace semantic status colors or the AA-safe primary action ramp. */
        .stApp:has(.wb-page-ambience--welcome) {{
            --wb-route-primary: #A78BFA;
            --wb-route-secondary: #FB9A8A;
            --wb-route-tertiary: #5EEAD4;
        }}

        .stApp:has(.wb-page-ambience--home) {{
            --wb-route-primary: #2DD4BF;
            --wb-route-secondary: #FB7185;
            --wb-route-tertiary: #FBBF24;
        }}

        .stApp:has(.wb-page-ambience--log) {{
            --wb-route-primary: #10B981;
            --wb-route-secondary: #A3E635;
            --wb-route-tertiary: #F59E0B;
        }}

        .stApp:has(.wb-page-ambience--pet) {{
            --wb-route-primary: #FB7185;
            --wb-route-secondary: #C084FC;
            --wb-route-tertiary: #FBBF24;
        }}

        .stApp:has(.wb-page-ambience--insights) {{
            --wb-route-primary: #6366F1;
            --wb-route-secondary: #D946EF;
            --wb-route-tertiary: #5EEAD4;
        }}

        .stApp:has(.wb-page-ambience--achievements) {{
            --wb-route-primary: #FBBF24;
            --wb-route-secondary: #F97316;
            --wb-route-tertiary: #FB7185;
        }}

        .stApp:has(.wb-page-ambience--reminders) {{
            --wb-route-primary: #F97316;
            --wb-route-secondary: #F43F5E;
            --wb-route-tertiary: #8B5CF6;
        }}

        .stApp:has(.wb-page-ambience--coach) {{
            --wb-route-primary: #10B981;
            --wb-route-secondary: #8B5CF6;
            --wb-route-tertiary: #EC4899;
        }}

        .stApp:has(.wb-page-ambience--profile) {{
            --wb-route-primary: #D946EF;
            --wb-route-secondary: #FB7185;
            --wb-route-tertiary: #F59E0B;
        }}

        /* Welcome: fine rain passing over soft landing ripples. */
        .stApp:has(.wb-page-ambience--welcome)::before {{
            inset: -22vh -12vw;
            opacity: .23;
            background-image:
                linear-gradient(112deg, transparent 45%, color-mix(in srgb, var(--wb-route-primary) 42%, transparent) 48% 49%, transparent 52%),
                linear-gradient(112deg, transparent 46%, color-mix(in srgb, var(--wb-route-secondary) 28%, transparent) 48.5% 49.5%, transparent 52%);
            background-position: 0 0, 3rem -5rem;
            background-repeat: repeat;
            background-size: 7rem 11rem, 11rem 17rem;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, #000, rgba(0,0,0,.82) 72%, transparent);
            mask-image: linear-gradient(to bottom, #000, rgba(0,0,0,.82) 72%, transparent);
            animation: wb-ambience-welcome-rain 18s linear infinite;
        }}

        .stApp:has(.wb-page-ambience--welcome)::after {{
            inset: 45vh -10vw -18vh;
            opacity: .22;
            background-image: repeating-radial-gradient(
                ellipse at 50% 100%,
                transparent 0 2.7rem,
                color-mix(in srgb,
                    color-mix(in srgb, var(--wb-route-tertiary) 64%, var(--wb-route-primary)) 28%,
                    transparent) 2.78rem 2.86rem,
                transparent 2.96rem 5.7rem
            );
            background-position: center bottom;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: none;
            -webkit-mask-image: linear-gradient(to top, #000, transparent 88%);
            mask-image: linear-gradient(to top, #000, transparent 88%);
            animation: wb-ambience-welcome-ripples 8.5s ease-out infinite;
        }}

        /* Home: broad currents and a breathing tide line. */
        .stApp:has(.wb-page-ambience--home)::before {{
            inset: -18vh -16vw;
            opacity: .44;
            background:
                radial-gradient(ellipse at 10% 72%, color-mix(in srgb, var(--wb-route-primary) 24%, transparent), transparent 39%),
                radial-gradient(ellipse at 76% 24%, color-mix(in srgb, var(--wb-route-secondary) 19%, transparent), transparent 35%),
                radial-gradient(ellipse at 58% 88%, color-mix(in srgb, var(--wb-route-tertiary) 13%, transparent), transparent 31%);
            background-position: center;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: blur(48px) saturate(112%);
            -webkit-mask-image: none;
            mask-image: none;
            animation: wb-ambience-home-current 20s ease-in-out infinite alternate;
        }}

        .stApp:has(.wb-page-ambience--home)::after {{
            inset: auto -12vw -17vh;
            height: 64vh;
            opacity: .26;
            background-image:
                repeating-radial-gradient(
                    ellipse at 50% 118%,
                    transparent 0 3.1rem,
                    color-mix(in srgb,
                        color-mix(in srgb, var(--wb-route-primary) 58%, var(--wb-route-secondary)) 24%,
                        transparent) 3.18rem 3.26rem,
                    transparent 3.36rem 6.5rem
                ),
                linear-gradient(to top, color-mix(in srgb, var(--wb-route-tertiary) 9%, transparent), transparent 72%);
            background-position: center bottom;
            background-repeat: no-repeat;
            background-size: 112% 100%, 100% 100%;
            filter: none;
            -webkit-mask-image: linear-gradient(to top, #000, transparent 90%);
            mask-image: linear-gradient(to top, #000, transparent 90%);
            animation: wb-ambience-home-tide 12s ease-in-out infinite;
        }}

        /* Log: two independent columns of bubbles rising through the page. */
        .stApp:has(.wb-page-ambience--log)::before {{
            inset: -24vh 0 -20vh;
            opacity: .32;
            background-image:
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-primary) 46%, transparent) 0 .2rem, transparent .27rem),
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-secondary) 34%, transparent) 0 .34rem, transparent .42rem),
                radial-gradient(circle, transparent 0 .48rem, color-mix(in srgb, var(--wb-route-tertiary) 28%, transparent) .52rem .58rem, transparent .63rem);
            background-position: 8% 2%, 54% 38%, 87% 12%;
            background-repeat: repeat;
            background-size: 8rem 12rem, 13rem 17rem, 18rem 23rem;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, transparent, #000 14%, #000 90%, transparent);
            mask-image: linear-gradient(to bottom, transparent, #000 14%, #000 90%, transparent);
            animation: wb-ambience-log-bubbles 19s linear infinite;
        }}

        .stApp:has(.wb-page-ambience--log)::after {{
            inset: -18vh 0 -18vh;
            opacity: .19;
            background-image:
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-primary) 40%, transparent) 0 .12rem, transparent .2rem),
                linear-gradient(90deg,
                    transparent 0 17%,
                    color-mix(in srgb, var(--wb-route-secondary) 13%, transparent) 17.2% 17.35%,
                    transparent 17.6% 72%,
                    color-mix(in srgb, var(--wb-route-tertiary) 12%, transparent) 72.2% 72.35%,
                    transparent 72.6% 100%);
            background-position: 28% 0, center;
            background-repeat: repeat, no-repeat;
            background-size: 11rem 15rem, 100% 100%;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, transparent, #000 18% 84%, transparent);
            mask-image: linear-gradient(to bottom, transparent, #000 18% 84%, transparent);
            animation: wb-ambience-log-stream 26s linear infinite;
        }}

        /* Pet: a lazy orbital ring with playful, blinking sparkles. */
        .stApp:has(.wb-page-ambience--pet)::before {{
            inset: 6vh 8vw;
            opacity: .2;
            background: repeating-conic-gradient(
                from 8deg at 50% 48%,
                transparent 0 13deg,
                color-mix(in srgb,
                    color-mix(in srgb, var(--wb-route-primary) 62%, var(--wb-route-secondary)) 33%,
                    transparent) 13.5deg 14deg,
                transparent 14.5deg 30deg
            );
            background-position: center;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: drop-shadow(0 0 1.2rem color-mix(in srgb, var(--wb-route-tertiary) 14%, transparent));
            -webkit-mask-image: radial-gradient(circle at 50% 48%, transparent 0 8.8rem, #000 9rem 9.15rem, transparent 9.35rem 15rem, #000 15.15rem 15.28rem, transparent 15.5rem);
            mask-image: radial-gradient(circle at 50% 48%, transparent 0 8.8rem, #000 9rem 9.15rem, transparent 9.35rem 15rem, #000 15.15rem 15.28rem, transparent 15.5rem);
            animation: wb-ambience-pet-orbit 42s linear infinite;
        }}

        .stApp:has(.wb-page-ambience--pet)::after {{
            inset: 0;
            opacity: .3;
            background-image:
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-primary) 58%, transparent) 0 1px, transparent 2px),
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-secondary) 48%, transparent) 0 1.4px, transparent 2.4px),
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-tertiary) 42%, transparent) 0 2px, transparent 2.8px);
            background-position: 9% 16%, 62% 31%, 88% 72%;
            background-repeat: repeat;
            background-size: 9rem 13rem, 15rem 19rem, 23rem 27rem;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, #000, rgba(0,0,0,.72) 76%, transparent);
            mask-image: linear-gradient(to bottom, #000, rgba(0,0,0,.72) 76%, transparent);
            animation: wb-ambience-pet-sparkles 7s steps(2, end) infinite;
        }}

        /* Insights: a perspective data grid with a scanning pulse. */
        .stApp:has(.wb-page-ambience--insights)::before {{
            inset: 28vh -16vw -38vh;
            opacity: .18;
            background-image:
                linear-gradient(color-mix(in srgb, var(--wb-route-primary) 25%, transparent) 1px, transparent 1px),
                linear-gradient(90deg, color-mix(in srgb, var(--wb-route-tertiary) 22%, transparent) 1px, transparent 1px);
            background-position: center bottom;
            background-repeat: repeat;
            background-size: 4rem 4rem;
            filter: none;
            transform-origin: 50% 100%;
            -webkit-mask-image: linear-gradient(to top, #000, transparent 88%);
            mask-image: linear-gradient(to top, #000, transparent 88%);
            animation: wb-ambience-insights-grid 13s linear infinite;
        }}

        .stApp:has(.wb-page-ambience--insights)::after {{
            inset: 0;
            opacity: .2;
            background-image:
                linear-gradient(90deg,
                    transparent 0 45%,
                    color-mix(in srgb, var(--wb-route-secondary) 30%, transparent) 48%,
                    color-mix(in srgb, var(--wb-route-secondary) 52%, transparent) 50%,
                    color-mix(in srgb, var(--wb-route-secondary) 30%, transparent) 52%,
                    transparent 55% 100%),
                radial-gradient(circle at 18% 62%, color-mix(in srgb, var(--wb-route-tertiary) 38%, transparent) 0 .22rem, transparent .32rem),
                radial-gradient(circle at 71% 35%, color-mix(in srgb, var(--wb-route-primary) 42%, transparent) 0 .18rem, transparent .3rem);
            background-position: -70vw 0, center, center;
            background-repeat: no-repeat;
            background-size: 32vw 100%, 100% 100%, 100% 100%;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, transparent, #000 18% 82%, transparent);
            mask-image: linear-gradient(to bottom, transparent, #000 18% 82%, transparent);
            animation: wb-ambience-insights-pulse 9s ease-in-out infinite;
        }}

        /* Achievements: drifting constellations crossed by brief glints. */
        .stApp:has(.wb-page-ambience--achievements)::before {{
            inset: -8vh -6vw;
            opacity: .28;
            background-image:
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-primary) 58%, transparent) 0 1.2px, transparent 2px),
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-secondary) 50%, transparent) 0 1px, transparent 1.8px),
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-tertiary) 44%, transparent) 0 1.6px, transparent 2.4px);
            background-position: 6% 12%, 46% 72%, 88% 28%;
            background-repeat: repeat;
            background-size: 12rem 16rem, 19rem 23rem, 27rem 31rem;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, #000, rgba(0,0,0,.76) 74%, transparent);
            mask-image: linear-gradient(to bottom, #000, rgba(0,0,0,.76) 74%, transparent);
            animation: wb-ambience-achievements-stars 30s ease-in-out infinite alternate;
        }}

        .stApp:has(.wb-page-ambience--achievements)::after {{
            inset: 4vh -12vw;
            opacity: .16;
            background-image:
                linear-gradient(28deg, transparent 48.8%, color-mix(in srgb, var(--wb-route-secondary) 30%, transparent) 49.6% 50%, transparent 50.8%),
                linear-gradient(142deg, transparent 49%, color-mix(in srgb, var(--wb-route-primary) 24%, transparent) 49.6% 50%, transparent 50.7%),
                radial-gradient(circle at 50% 50%, color-mix(in srgb, var(--wb-route-tertiary) 62%, transparent) 0 .2rem, transparent 1.2rem);
            background-position: 0 0, 4rem 7rem, 52% 34%;
            background-repeat: repeat, repeat, no-repeat;
            background-size: 24rem 19rem, 31rem 27rem, 100% 100%;
            filter: none;
            -webkit-mask-image: linear-gradient(105deg, transparent, #000 16% 84%, transparent);
            mask-image: linear-gradient(105deg, transparent, #000 16% 84%, transparent);
            animation: wb-ambience-achievements-glint 8s ease-in-out infinite;
        }}

        /* Reminders: clock ticks above concentric notification ripples. */
        .stApp:has(.wb-page-ambience--reminders)::before {{
            inset: 8vh 14vw;
            opacity: .2;
            background: repeating-conic-gradient(
                from -1deg at 50% 46%,
                color-mix(in srgb,
                    color-mix(in srgb, var(--wb-route-primary) 62%, var(--wb-route-secondary)) 38%,
                    transparent) 0 .65deg,
                transparent .9deg 30deg
            );
            background-position: center;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: none;
            transform-origin: 50% 46%;
            -webkit-mask-image: radial-gradient(circle at 50% 46%, transparent 0 10rem, #000 10.15rem 10.7rem, transparent 10.9rem 16rem, #000 16.1rem 16.3rem, transparent 16.5rem);
            mask-image: radial-gradient(circle at 50% 46%, transparent 0 10rem, #000 10.15rem 10.7rem, transparent 10.9rem 16rem, #000 16.1rem 16.3rem, transparent 16.5rem);
            animation: wb-ambience-reminders-clock 36s steps(12, end) infinite;
        }}

        .stApp:has(.wb-page-ambience--reminders)::after {{
            inset: 0;
            opacity: .2;
            background-image: repeating-radial-gradient(
                circle at 50% 46%,
                transparent 0 4.2rem,
                color-mix(in srgb,
                    color-mix(in srgb, var(--wb-route-tertiary) 68%, var(--wb-route-secondary)) 22%,
                    transparent) 4.28rem 4.36rem,
                transparent 4.48rem 8.7rem
            );
            background-position: center;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: none;
            -webkit-mask-image: radial-gradient(circle at 50% 46%, #000, transparent 72%);
            mask-image: radial-gradient(circle at 50% 46%, #000, transparent 72%);
            animation: wb-ambience-reminders-ripple 9s ease-out infinite;
        }}

        /* Coach: crossing current paths and softly firing neural nodes. */
        .stApp:has(.wb-page-ambience--coach)::before {{
            inset: -12vh -20vw;
            opacity: .2;
            background-image:
                repeating-radial-gradient(ellipse at -8% 52%, transparent 0 5rem, color-mix(in srgb, var(--wb-route-primary) 24%, transparent) 5.08rem 5.16rem, transparent 5.28rem 10.2rem),
                repeating-radial-gradient(ellipse at 108% 46%, transparent 0 7rem, color-mix(in srgb, var(--wb-route-secondary) 20%, transparent) 7.08rem 7.16rem, transparent 7.28rem 14.2rem);
            background-position: -3rem 0, 4rem 2rem;
            background-repeat: repeat;
            background-size: 42rem 28rem, 56rem 36rem;
            filter: none;
            -webkit-mask-image: linear-gradient(90deg, transparent, #000 12% 88%, transparent);
            mask-image: linear-gradient(90deg, transparent, #000 12% 88%, transparent);
            animation: wb-ambience-coach-currents 24s ease-in-out infinite alternate;
        }}

        .stApp:has(.wb-page-ambience--coach)::after {{
            inset: 0;
            opacity: .26;
            background-image:
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-primary) 52%, transparent) 0 .16rem, transparent .28rem),
                radial-gradient(circle, color-mix(in srgb, var(--wb-route-secondary) 46%, transparent) 0 .22rem, transparent .34rem),
                radial-gradient(circle, transparent 0 .5rem, color-mix(in srgb, var(--wb-route-tertiary) 28%, transparent) .54rem .6rem, transparent .68rem);
            background-position: 12% 18%, 67% 42%, 88% 76%;
            background-repeat: repeat;
            background-size: 13rem 17rem, 21rem 25rem, 31rem 35rem;
            filter: none;
            -webkit-mask-image: linear-gradient(to bottom, transparent, #000 12% 82%, transparent);
            mask-image: linear-gradient(to bottom, transparent, #000 12% 82%, transparent);
            animation: wb-ambience-coach-nodes 6.5s ease-in-out infinite;
        }}

        /* Profile: slow, spacious aurora clouds and translucent ribbons. */
        .stApp:has(.wb-page-ambience--profile)::before {{
            inset: -28vh -22vw;
            opacity: .48;
            background:
                radial-gradient(ellipse at 16% 30%, color-mix(in srgb, var(--wb-route-primary) 22%, transparent), transparent 33%),
                radial-gradient(ellipse at 82% 22%, color-mix(in srgb, var(--wb-route-secondary) 19%, transparent), transparent 29%),
                radial-gradient(ellipse at 56% 82%, color-mix(in srgb, var(--wb-route-tertiary) 17%, transparent), transparent 36%);
            background-position: center;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: blur(64px) saturate(108%);
            -webkit-mask-image: none;
            mask-image: none;
            animation: wb-ambience-profile-aurora 38s ease-in-out infinite alternate;
        }}

        .stApp:has(.wb-page-ambience--profile)::after {{
            inset: -18vh -24vw;
            opacity: .13;
            background-image:
                linear-gradient(118deg, transparent 0 18%, color-mix(in srgb, var(--wb-route-primary) 34%, transparent) 25%, transparent 33% 58%, color-mix(in srgb, var(--wb-route-secondary) 26%, transparent) 66%, transparent 74%),
                linear-gradient(74deg, transparent 0 34%, color-mix(in srgb, var(--wb-route-tertiary) 24%, transparent) 42%, transparent 50%);
            background-position: center;
            background-repeat: no-repeat;
            background-size: 100% 100%;
            filter: blur(26px);
            -webkit-mask-image: linear-gradient(90deg, transparent, #000 18% 82%, transparent);
            mask-image: linear-gradient(90deg, transparent, #000 18% 82%, transparent);
            animation: wb-ambience-profile-ribbons 32s ease-in-out infinite alternate;
        }}

        .stApp, .stApp button, .stApp input, .stApp textarea, .stApp select {{
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        [data-testid="stMainBlockContainer"] {{
            width: 100%;
            min-width: 0;
            max-width: 1320px;
            padding-top: clamp(1.35rem, 3vw, 2.7rem);
            padding-bottom: 4rem;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            background:
                linear-gradient(180deg,
                    color-mix(in srgb, var(--wb-surface) 92%, transparent),
                    color-mix(in srgb, var(--wb-bg) 90%, transparent));
            border-right: 1px solid var(--wb-soft-line);
        }}

        /* The shared shell mounts its optional, non-visual feedback audio here. */
        .st-key-sound-cue {{
            display: none;
        }}

        .stApp h1, .stApp h2, .stApp h3 {{
            letter-spacing: -0.035em;
        }}

        .stApp p, .stApp label, .stApp [data-testid="stCaptionContainer"] {{
            line-height: 1.62;
        }}

        .stApp .stButton > button,
        .stApp .stDownloadButton > button,
        .stApp [data-testid="stFormSubmitButton"] > button {{
            min-height: 2.75rem;
            border-radius: 999px;
            border-color: var(--wb-line);
            font-weight: 720;
            letter-spacing: -0.01em;
            padding-inline: 1.15rem;
            box-shadow: 0 8px 24px color-mix(in srgb, #020617 10%, transparent);
            transition: transform 180ms ease, box-shadow 180ms ease,
                border-color 180ms ease, filter 180ms ease;
        }}

        .stApp .stButton > button:hover,
        .stApp .stDownloadButton > button:hover,
        .stApp [data-testid="stFormSubmitButton"] > button:hover {{
            transform: translateY(-2px);
            border-color: color-mix(in srgb, var(--wb-cyan) 62%, var(--wb-line));
            box-shadow: 0 13px 32px color-mix(in srgb, var(--wb-blue) 20%, transparent);
        }}

        .stApp button[kind="primary"],
        .stApp button[data-testid="stBaseButton-primary"] {{
            background: linear-gradient(125deg, var(--wb-blue), var(--wb-royal) 55%, var(--wb-action-end));
            border: 1px solid color-mix(in srgb, #FFFFFF 22%, transparent);
            color: #FFFFFF;
        }}

        .stApp button:focus-visible,
        .stApp input:focus-visible,
        .stApp textarea:focus-visible,
        .stApp [tabindex]:focus-visible {{
            outline: 3px solid var(--wb-cyan);
            outline-offset: 3px;
        }}

        .stApp [data-testid="stMetric"],
        .stApp [data-testid="stExpander"],
        .stApp [data-testid="stForm"] {{
            border-radius: 1.35rem;
            border-color: var(--wb-line);
            background: color-mix(in srgb, var(--wb-surface) 70%, transparent);
            box-shadow: 0 16px 44px color-mix(in srgb, #020617 8%, transparent);
        }}

        .stApp [data-testid="stMetric"] {{
            padding: 1rem 1.1rem;
        }}

        /* ---------- Native Streamlit surfaces ---------- */
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: transparent !important;
        }}

        [data-testid="stHeader"],
        [data-testid="stAppHeader"] {{
            border-bottom: 1px solid color-mix(in srgb, var(--wb-line) 74%, transparent);
            background: color-mix(in srgb, var(--wb-bg) 82%, transparent) !important;
            box-shadow: 0 8px 30px color-mix(in srgb, {palette["shadow"]} 12%, transparent);
            backdrop-filter: blur(18px) saturate(135%);
        }}

        [data-testid="stToolbar"],
        [data-testid="stAppToolbar"] {{
            color: var(--wb-ink) !important;
        }}

        [data-testid="stToolbar"] button,
        [data-testid="stAppToolbar"] button,
        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stExpandSidebarButton"] button {{
            border: 1px solid transparent !important;
            border-radius: .75rem !important;
            background: transparent !important;
            color: var(--wb-muted) !important;
        }}

        [data-testid="stToolbar"] button:hover,
        [data-testid="stAppToolbar"] button:hover,
        [data-testid="stSidebarCollapseButton"] button:hover,
        [data-testid="stExpandSidebarButton"] button:hover {{
            border-color: var(--wb-line) !important;
            background: var(--wb-elevated) !important;
            color: var(--wb-ink) !important;
        }}

        .stApp [data-testid="stMarkdown"],
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stWidgetLabel"],
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6,
        .stApp p,
        .stApp label {{
            color: var(--wb-ink);
        }}

        .stApp [data-testid="stCaptionContainer"],
        .stApp small {{
            color: var(--wb-muted) !important;
        }}

        .stApp a {{
            color: color-mix(in srgb, var(--wb-cyan) 80%, var(--wb-ink));
            text-decoration-color: color-mix(in srgb, var(--wb-cyan) 38%, transparent);
            text-underline-offset: .2em;
        }}

        .stApp code,
        .stApp pre {{
            border-color: var(--wb-line) !important;
            background: var(--wb-field) !important;
            color: var(--wb-ink) !important;
        }}

        /* Top and sidebar navigation */
        [data-testid="stTopNavSection"] {{
            gap: .18rem;
            padding: .28rem;
            border: 1px solid color-mix(in srgb, var(--wb-line) 76%, transparent);
            border-radius: 999px;
            background: color-mix(in srgb, var(--wb-surface) 72%, transparent);
            box-shadow: inset 0 1px 0 color-mix(in srgb, #FFFFFF 8%, transparent),
                0 10px 28px color-mix(in srgb, {palette["shadow"]} 10%, transparent);
            backdrop-filter: blur(14px);
        }}

        [data-testid="stTopNavLink"],
        [data-testid="stTopNavDropdownLink"],
        [data-testid="stTopNavPopover"] button {{
            min-height: 2.25rem;
            border: 0 !important;
            border-radius: 999px !important;
            background: transparent !important;
            color: var(--wb-muted) !important;
            font-weight: 680;
            transition: color 160ms ease, background 160ms ease, transform 160ms ease;
        }}

        [data-testid="stTopNavLink"]:hover,
        [data-testid="stTopNavDropdownLink"]:hover,
        [data-testid="stTopNavPopover"] button:hover {{
            background: var(--wb-elevated) !important;
            color: var(--wb-ink) !important;
        }}

        [data-testid="stTopNavLink"][aria-current="page"],
        [data-testid="stTopNavDropdownLink"][aria-current="page"],
        [data-testid="stTopNavLinkContainer"]:has([aria-current="page"]) [data-testid="stTopNavLink"] {{
            background: linear-gradient(130deg,
                var(--wb-blue),
                var(--wb-royal) 55%,
                var(--wb-action-end)) !important;
            color: #FFFFFF !important;
            box-shadow: 0 7px 20px color-mix(in srgb, var(--wb-blue) 30%, transparent);
        }}

        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"] {{
            color: var(--wb-ink) !important;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            background:
                radial-gradient(circle at 20% 0%, color-mix(in srgb, var(--wb-blue) 13%, transparent), transparent 16rem),
                color-mix(in srgb, var(--wb-surface) 94%, var(--wb-bg)) !important;
        }}

        [data-testid="stSidebarNavLink"] {{
            border-radius: .8rem;
            color: var(--wb-muted) !important;
        }}

        [data-testid="stSidebarNavLink"]:hover,
        [data-testid="stSidebarNavLink"][aria-current="page"] {{
            background: var(--wb-elevated) !important;
            color: var(--wb-ink) !important;
        }}

        /* Buttons */
        .stApp button[kind="secondary"],
        .stApp button[data-testid="stBaseButton-secondary"],
        .stApp button[kind="tertiary"],
        .stApp button[data-testid="stBaseButton-tertiary"] {{
            border: 1px solid var(--wb-line) !important;
            background: color-mix(in srgb, var(--wb-elevated) 82%, transparent) !important;
            color: var(--wb-ink) !important;
        }}

        .stApp button[kind="tertiary"],
        .stApp button[data-testid="stBaseButton-tertiary"] {{
            background: transparent !important;
            box-shadow: none;
        }}

        .stApp button:disabled,
        .stApp [aria-disabled="true"] {{
            cursor: not-allowed !important;
            filter: saturate(.4);
            opacity: .48 !important;
        }}

        /* Text, number, date, time, and selection fields */
        .stApp [data-baseweb="input"],
        .stApp [data-baseweb="base-input"],
        .stApp [data-baseweb="textarea"],
        .stApp [data-baseweb="select"],
        .stApp [data-baseweb="select"] > div,
        .stApp [data-testid="stNumberInputContainer"],
        .stApp [data-testid="stDateInputField"],
        .stApp [data-testid="stDateTimeInputField"],
        .stApp [data-testid="stTimeInput"] > div,
        .stApp [data-testid="stMultiSelect"] > div {{
            border-color: var(--wb-line) !important;
            border-radius: .9rem !important;
            background: var(--wb-field) !important;
            color: var(--wb-field-ink) !important;
            box-shadow: inset 0 1px 0 color-mix(in srgb, #FFFFFF 5%, transparent);
        }}

        /* Base Web paints an extra inner layer in some Streamlit releases.
           Color that layer too so dark-theme text never lands on a white box. */
        .stApp [data-baseweb="input"] > div,
        .stApp [data-baseweb="base-input"],
        .stApp [data-baseweb="base-input"] > div,
        .stApp [data-baseweb="textarea"] > div,
        .stApp [data-baseweb="select"] > div,
        .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        .stApp [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
            background-color: var(--wb-field) !important;
            color: var(--wb-field-ink) !important;
        }}

        .stApp [data-baseweb="input"]:focus-within,
        .stApp [data-baseweb="textarea"]:focus-within,
        .stApp [data-baseweb="select"] > div:focus-within,
        .stApp [data-testid="stNumberInputContainer"]:focus-within,
        .stApp [data-testid="stDateInputField"]:focus-within,
        .stApp [data-testid="stTimeInput"] > div:focus-within {{
            border-color: color-mix(in srgb, var(--wb-cyan) 66%, var(--wb-line)) !important;
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--wb-cyan) 14%, transparent) !important;
        }}

        .stApp input,
        .stApp textarea,
        .stApp [data-baseweb="select"] span,
        .stApp [data-baseweb="select"] p {{
            background-color: transparent !important;
            color: var(--wb-field-ink) !important;
            -webkit-text-fill-color: var(--wb-field-ink) !important;
            font-weight: 600;
            caret-color: var(--wb-cyan);
        }}

        .stApp input:-webkit-autofill,
        .stApp input:-webkit-autofill:hover,
        .stApp input:-webkit-autofill:focus {{
            -webkit-box-shadow: 0 0 0 1000px var(--wb-field) inset !important;
            -webkit-text-fill-color: var(--wb-field-ink) !important;
            caret-color: var(--wb-cyan);
        }}

        .stApp input::placeholder,
        .stApp textarea::placeholder {{
            color: var(--wb-field-muted) !important;
            -webkit-text-fill-color: var(--wb-field-muted) !important;
            opacity: 1;
        }}

        .stApp [data-testid="stNumberInput"] button,
        .stApp [data-testid="stTimeInput"] button,
        .stApp [data-testid="stDateInput"] button {{
            border-color: var(--wb-line) !important;
            background: var(--wb-elevated) !important;
            color: var(--wb-muted) !important;
        }}

        /* Segments, pills, radio, toggles, and sliders */
        .stApp [data-testid="stButtonGroup"] {{
            gap: .2rem;
            padding: .24rem;
            border: 1px solid var(--wb-line);
            border-radius: 1rem;
            background: var(--wb-field);
        }}

        .stApp [data-testid="stButtonGroup"] button {{
            border: 0 !important;
            border-radius: .72rem !important;
            background: transparent !important;
            color: var(--wb-muted) !important;
            box-shadow: none;
        }}

        .stApp [data-testid="stButtonGroup"] button[aria-pressed="true"],
        .stApp [data-testid="stButtonGroup"] button[aria-selected="true"] {{
            background: var(--wb-elevated) !important;
            color: var(--wb-ink) !important;
            box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--wb-cyan) 28%, var(--wb-line));
        }}

        .stApp [data-testid="stCheckbox"],
        .stApp [data-testid="stRadio"],
        .stApp [data-testid="stToggle"] {{
            color: var(--wb-ink) !important;
        }}

        .stApp input[type="checkbox"],
        .stApp input[type="radio"] {{
            accent-color: var(--wb-blue);
        }}

        .stApp [role="slider"] {{
            border-color: color-mix(in srgb, var(--wb-cyan) 55%, #FFFFFF) !important;
            background: var(--wb-blue) !important;
            box-shadow: 0 0 0 .25rem color-mix(in srgb, var(--wb-blue) 16%, transparent),
                0 4px 14px color-mix(in srgb, var(--wb-blue) 24%, transparent) !important;
        }}

        /* Tabs, expanders, forms, and bordered content */
        .stApp [data-testid="stTabs"] [role="tablist"] {{
            gap: .24rem;
            padding: .28rem;
            border: 1px solid var(--wb-line);
            border-radius: 1rem;
            background: color-mix(in srgb, var(--wb-surface) 72%, transparent);
        }}

        .stApp [data-testid="stTab"] {{
            border-radius: .72rem;
            color: var(--wb-muted) !important;
        }}

        .stApp [data-testid="stTab"][aria-selected="true"] {{
            background: var(--wb-elevated) !important;
            color: var(--wb-ink) !important;
        }}

        .stApp [data-testid="stMetric"],
        .stApp [data-testid="stExpander"],
        .stApp [data-testid="stForm"],
        .stApp [data-testid="stStatusWidget"],
        .stApp div[data-testid="stVerticalBlockBorderWrapper"] {{
            border: 1px solid var(--wb-line) !important;
            background: color-mix(in srgb, var(--wb-surface) 84%, transparent) !important;
            color: var(--wb-ink) !important;
            backdrop-filter: blur(14px);
        }}

        /* Route color is limited to non-semantic card edges. Alerts, status
           widgets, and action controls deliberately keep their system colors. */
        .stApp:has(:is(
            .wb-page-ambience--welcome,
            .wb-page-ambience--home,
            .wb-page-ambience--log,
            .wb-page-ambience--pet,
            .wb-page-ambience--insights,
            .wb-page-ambience--achievements,
            .wb-page-ambience--reminders,
            .wb-page-ambience--coach,
            .wb-page-ambience--profile
        )) [data-testid="stMetric"],
        .stApp:has(:is(
            .wb-page-ambience--welcome,
            .wb-page-ambience--home,
            .wb-page-ambience--log,
            .wb-page-ambience--pet,
            .wb-page-ambience--insights,
            .wb-page-ambience--achievements,
            .wb-page-ambience--reminders,
            .wb-page-ambience--coach,
            .wb-page-ambience--profile
        )) [data-testid="stExpander"],
        .stApp:has(:is(
            .wb-page-ambience--welcome,
            .wb-page-ambience--home,
            .wb-page-ambience--log,
            .wb-page-ambience--pet,
            .wb-page-ambience--insights,
            .wb-page-ambience--achievements,
            .wb-page-ambience--reminders,
            .wb-page-ambience--coach,
            .wb-page-ambience--profile
        )) [data-testid="stForm"],
        .stApp:has(:is(
            .wb-page-ambience--welcome,
            .wb-page-ambience--home,
            .wb-page-ambience--log,
            .wb-page-ambience--pet,
            .wb-page-ambience--insights,
            .wb-page-ambience--achievements,
            .wb-page-ambience--reminders,
            .wb-page-ambience--coach,
            .wb-page-ambience--profile
        )) div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: color-mix(in srgb, var(--wb-route-primary) 24%, var(--wb-line)) !important;
        }}

        .stApp [data-testid="stExpander"] summary:hover {{
            background: var(--wb-elevated) !important;
        }}

        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricLabel"] {{
            color: var(--wb-ink) !important;
        }}

        .stApp [data-testid="stMetricDelta"] {{
            color: var(--wb-aqua) !important;
        }}

        /* Progress, messages, uploads, data, and chat */
        .stApp [data-testid="stProgress"] > div,
        .stApp [role="progressbar"] {{
            border-radius: 999px;
            background: var(--wb-field);
        }}

        .stApp [data-testid="stProgress"] [role="progressbar"] > div {{
            background: linear-gradient(90deg, var(--wb-blue), var(--wb-cyan), var(--wb-aqua)) !important;
            box-shadow: 0 0 16px color-mix(in srgb, var(--wb-cyan) 30%, transparent);
        }}

        [data-testid="stToast"] {{
            border: 1px solid var(--wb-line) !important;
            border-radius: 1rem !important;
            background: var(--wb-overlay) !important;
            color: var(--wb-ink) !important;
            box-shadow: 0 16px 40px color-mix(in srgb, {palette["shadow"]} 22%, transparent) !important;
            backdrop-filter: blur(18px);
        }}

        .stApp [data-testid="stFileUploaderDropzone"] {{
            border: 1px dashed color-mix(in srgb, var(--wb-cyan) 35%, var(--wb-line)) !important;
            border-radius: 1.2rem;
            background: color-mix(in srgb, var(--wb-field) 84%, transparent) !important;
            color: var(--wb-muted) !important;
        }}

        .stApp [data-testid="stDataFrame"],
        .stApp [data-testid="stTable"] {{
            overflow: hidden;
            border: 1px solid var(--wb-line);
            border-radius: 1rem;
            background: var(--wb-surface);
        }}

        .stApp [data-testid="stBottom"] {{
            border-top: 1px solid color-mix(in srgb, var(--wb-line) 74%, transparent);
            background: color-mix(in srgb, var(--wb-bg) 82%, transparent) !important;
            backdrop-filter: blur(18px);
        }}

        .stApp [data-testid="stChatInput"] {{
            border-color: var(--wb-line) !important;
            border-radius: 1rem !important;
            background: var(--wb-field) !important;
            color: var(--wb-ink) !important;
            box-shadow: 0 12px 30px color-mix(in srgb, {palette["shadow"]} 12%, transparent);
        }}

        .stApp [data-testid="stChatInput"] textarea {{
            background: transparent !important;
        }}

        /* Portaled overlays: popovers, menus, calendars, tooltips, dialogs. */
        [data-baseweb="popover"] > div,
        [data-testid="stPopoverBody"],
        [data-testid="stTopNavPopoverBody"],
        [role="listbox"],
        [role="menu"],
        [role="tooltip"] {{
            border: 1px solid var(--wb-line) !important;
            border-radius: 1rem !important;
            background: var(--wb-overlay) !important;
            color: var(--wb-ink) !important;
            box-shadow: 0 22px 60px color-mix(in srgb, {palette["shadow"]} 34%, transparent) !important;
            backdrop-filter: blur(20px) saturate(135%);
        }}

        [data-baseweb="popover"] *,
        [data-testid="stPopoverBody"] *,
        [data-testid="stTopNavPopoverBody"] * {{
            color: var(--wb-ink);
        }}

        [role="option"],
        [role="menuitem"] {{
            border-radius: .7rem;
            color: var(--wb-ink) !important;
        }}

        [role="option"]:hover,
        [role="option"][aria-selected="true"],
        [role="menuitem"]:hover {{
            background: var(--wb-elevated) !important;
        }}

        [data-testid="stDialog"] [role="dialog"],
        [data-testid="stDialog"] > div {{
            border: 1px solid var(--wb-line) !important;
            border-radius: 1.6rem !important;
            background: var(--wb-overlay) !important;
            color: var(--wb-ink) !important;
            box-shadow: 0 30px 90px color-mix(in srgb, {palette["shadow"]} 46%, transparent) !important;
            backdrop-filter: blur(22px) saturate(130%);
        }}

        [data-testid="stDialog"]::backdrop {{
            background: color-mix(in srgb, var(--wb-bg) 72%, transparent) !important;
            backdrop-filter: blur(6px);
        }}

        /* ---------- Responsive containment and safe native wrapping ---------- */
        .stApp *,
        .stApp *::before,
        .stApp *::after {{
            box-sizing: border-box;
        }}

        .stApp :where(
            [data-testid="stMainBlockContainer"],
            [data-testid="stVerticalBlock"],
            [data-testid="stHorizontalBlock"],
            [data-testid="stLayoutWrapper"],
            [data-testid="stElementContainer"],
            [data-testid="column"],
            [data-testid="stColumn"],
            [data-testid="stMarkdown"],
            [data-testid="stMarkdownContainer"],
            [data-testid="stMetric"],
            [data-testid="stAlert"],
            [data-testid="stAlertContainer"],
            [data-testid="stForm"],
            [data-testid="stExpander"],
            [data-testid="stButtonGroup"],
            .stElementContainer,
            .stHtml
        ) {{
            min-inline-size: 0;
            max-inline-size: 100%;
        }}

        .stApp :where(
            [data-testid="stVerticalBlock"],
            [data-testid="stHorizontalBlock"],
            [data-testid="stLayoutWrapper"],
            [data-testid="stElementContainer"],
            [data-testid="column"],
            [data-testid="stColumn"],
            [data-testid="stMetric"],
            [data-testid="stAlert"],
            [data-testid="stAlertContainer"]
        ) > * {{
            min-inline-size: 0;
            max-inline-size: 100%;
        }}

        .stApp :where(
            h1, h2, h3, h4, h5, h6,
            p, li, dt, dd, figcaption, label, a,
            [data-testid="stMarkdownContainer"],
            [data-testid="stCaptionContainer"],
            [data-testid="stWidgetLabel"],
            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"],
            [data-testid="stMetricDelta"],
            [data-testid^="stAlertContent"],
            [data-testid="stStatusWidget"],
            [data-testid="stToast"]
        ) {{
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow-wrap: anywhere;
            word-break: normal;
            hyphens: auto;
        }}

        .stApp :where(
            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"],
            [data-testid="stMetricDelta"],
            [data-testid="stMetricLabel"] *,
            [data-testid="stMetricValue"] *,
            [data-testid="stMetricDelta"] *
        ) {{
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: normal !important;
        }}

        .stApp :where(
            .stButton,
            .stDownloadButton,
            [data-testid="stFormSubmitButton"]
        ),
        .stApp :where(
            .stButton,
            .stDownloadButton,
            [data-testid="stFormSubmitButton"]
        ) > button {{
            min-inline-size: 0;
            max-inline-size: 100%;
        }}

        .stApp :where(
            .stButton,
            .stDownloadButton,
            [data-testid="stFormSubmitButton"],
            [data-testid="stButtonGroup"]
        ) button,
        .stApp :where(
            .stButton,
            .stDownloadButton,
            [data-testid="stFormSubmitButton"],
            [data-testid="stButtonGroup"]
        ) button :where(p, span) {{
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow-wrap: anywhere;
            word-break: normal;
            white-space: normal !important;
        }}

        .stApp :where(
            .material-symbols-rounded,
            [data-testid="stIconMaterial"]
        ) {{
            flex: 0 0 auto;
            overflow-wrap: normal;
            word-break: keep-all;
            white-space: nowrap !important;
        }}

        .stApp span.stMarkdownBadge {{
            display: inline-flex;
            flex-wrap: wrap;
            align-items: center;
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow: visible;
            overflow-wrap: anywhere;
            text-overflow: clip;
            white-space: normal !important;
        }}

        .stApp :where(
            [data-testid="stTopNavLink"],
            [data-testid="stTopNavDropdownLink"],
            [data-testid="stTopNavPopover"] button,
            [data-testid="stSidebarNavLink"],
            [data-testid="stTab"],
            [data-testid="stExpander"] summary
        ) {{
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow-wrap: anywhere;
            word-break: normal;
        }}

        .stApp :where(
            [data-testid="stTopNavLink"],
            [data-testid="stTopNavDropdownLink"],
            [data-testid="stTopNavPopover"] button,
            [data-testid="stSidebarNavLink"],
            [data-testid="stTab"],
            [data-testid="stExpander"] summary
        ) :where(p, span) {{
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow-wrap: anywhere;
            word-break: normal;
            white-space: normal !important;
        }}

        .stApp :where(
            [data-testid="stCheckbox"],
            [data-testid="stRadio"],
            [data-testid="stToggle"]
        ) label {{
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow-wrap: anywhere;
            white-space: normal;
        }}

        .stApp pre {{
            max-inline-size: 100%;
            overflow-x: auto;
        }}

        :is(
            [data-baseweb="popover"],
            [data-testid="stPopoverBody"],
            [data-testid="stTopNavPopoverBody"],
            [data-testid="stDialog"],
            [data-testid="stToast"]
        ) :where(
            p, li, dt, dd, label, a,
            [data-testid="stMarkdownContainer"],
            [data-testid="stCaptionContainer"],
            [role="option"],
            [role="menuitem"]
        ) {{
            min-inline-size: 0;
            max-inline-size: 100%;
            overflow-wrap: anywhere;
            word-break: normal;
            white-space: normal;
        }}

        /* ---------- Shared component foundation ---------- */
        .wb-brand,
        .wb-page-intro,
        .wb-mascot,
        .wb-pet,
        .wb-bottle-card,
        .wb-badge-card,
        .wb-empty-state {{
            box-sizing: border-box;
            min-width: 0;
            max-width: 100%;
            color: var(--wb-ink);
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }}

        .wb-brand *,
        .wb-page-intro *,
        .wb-mascot *,
        .wb-pet *,
        .wb-bottle-card *,
        .wb-badge-card *,
        .wb-empty-state * {{
            box-sizing: border-box;
        }}

        .stApp .stHtml:has(> :is(
            .wb-page-intro,
            .wb-mascot,
            .wb-pet,
            .wb-bottle-card,
            .wb-badge-card,
            .wb-empty-state
        )) {{
            width: 100%;
            container-type: inline-size;
        }}

        .wb-brand__copy,
        .wb-page-intro__copy,
        .wb-page-intro__badge,
        .wb-mascot__copy,
        .wb-mascot__status,
        .wb-mascot__name,
        .wb-mascot__message,
        .wb-mascot__meter-label,
        .wb-pet__speech,
        .wb-pet__panel,
        .wb-pet__kicker,
        .wb-pet__stage,
        .wb-pet__mood,
        .wb-pet__name,
        .wb-pet__level,
        .wb-pet__stat-label,
        .wb-pet__hint,
        .wb-bottle__copy,
        .wb-bottle__eyebrow,
        .wb-bottle__value,
        .wb-bottle__percent,
        .wb-badge-card__top,
        .wb-badge-card__state,
        .wb-badge-card__title,
        .wb-badge-card__description,
        .wb-empty-state__title,
        .wb-empty-state__description {{
            min-width: 0;
            max-width: 100%;
            overflow-wrap: anywhere;
            word-break: normal;
            hyphens: auto;
        }}

        .wb-page-intro__badge,
        .wb-mascot__status,
        .wb-pet__kicker,
        .wb-pet__stage,
        .wb-pet__stat-label,
        .wb-mascot__meter-label,
        .wb-bottle__percent,
        .wb-badge-card__top,
        .wb-badge-card__state {{
            flex-wrap: wrap;
            white-space: normal;
        }}

        .wb-page-intro__badge::before,
        .wb-mascot__status-dot,
        .wb-pet__stage::before,
        .wb-empty-state__icon {{
            flex: 0 0 auto;
        }}

        .wb-mascot__meter-label > *,
        .wb-pet__kicker > *,
        .wb-pet__stat-label > *,
        .wb-badge-card__top > * {{
            min-width: 0;
            max-width: 100%;
        }}

        /* ---------- Brand lockup ---------- */
        .wb-brand {{
            display: inline-flex;
            align-items: center;
            gap: .72rem;
            min-width: 0;
            max-width: 100%;
            user-select: none;
        }}

        .wb-brand__mark {{
            position: relative;
            flex: 0 0 auto;
            display: grid;
            place-items: center;
            width: 2.6rem;
            height: 2.6rem;
            border-radius: .9rem;
            background: linear-gradient(140deg, var(--wb-cyan), var(--wb-blue) 58%, var(--wb-violet));
            box-shadow: 0 10px 30px color-mix(in srgb, var(--wb-blue) 35%, transparent),
                inset 0 1px 0 rgba(255,255,255,.46);
            overflow: hidden;
        }}

        .wb-brand__mark::before {{
            content: "";
            width: .88rem;
            height: 1.12rem;
            border-radius: 55% 45% 55% 45% / 67% 43% 57% 33%;
            background: #FFFFFF;
            transform: rotate(35deg);
            box-shadow: 0 3px 10px rgba(8,47,73,.18);
        }}

        .wb-brand__mark::after {{
            content: "";
            position: absolute;
            top: .35rem;
            right: .42rem;
            width: .34rem;
            height: .34rem;
            border-radius: 50%;
            background: rgba(255,255,255,.72);
        }}

        .wb-brand__name {{
            display: block;
            margin: 0;
            font-size: 1.08rem;
            font-weight: 850;
            letter-spacing: -.035em;
            line-height: 1.05;
        }}

        .wb-brand__tagline {{
            display: block;
            margin-top: .22rem;
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 750;
            letter-spacing: .105em;
            line-height: 1;
            text-transform: uppercase;
        }}

        .wb-brand--compact .wb-brand__mark {{
            width: 2.18rem;
            height: 2.18rem;
            border-radius: .75rem;
        }}

        .wb-brand--compact .wb-brand__name {{ font-size: .95rem; }}
        .wb-brand--compact .wb-brand__tagline {{ display: none; }}

        /* ---------- Page introduction ---------- */
        .wb-page-intro {{
            position: relative;
            isolation: isolate;
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1.5rem;
            margin: 0 0 1.65rem;
            padding: clamp(1.45rem, 3vw, 2.35rem);
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--wb-route-primary) 28%, var(--wb-line));
            border-radius: clamp(1.35rem, 2vw, 2rem);
            background:
                linear-gradient(120deg,
                    color-mix(in srgb, var(--wb-route-primary) 14%, var(--wb-surface)),
                    color-mix(in srgb, var(--wb-surface) 84%, transparent) 58%,
                    color-mix(in srgb, var(--wb-route-secondary) 9%, var(--wb-surface)));
            box-shadow: var(--wb-shadow);
        }}

        .wb-page-intro::before {{
            content: "";
            position: absolute;
            z-index: -1;
            width: 16rem;
            height: 16rem;
            right: -5rem;
            top: -8rem;
            border-radius: 50%;
            background: color-mix(in srgb, var(--wb-route-tertiary) 23%, transparent);
            filter: blur(20px);
        }}

        .wb-page-intro::after {{
            content: "";
            position: absolute;
            z-index: -1;
            inset: 0;
            opacity: .16;
            background-image: radial-gradient(currentColor .6px, transparent .6px);
            background-size: 16px 16px;
            mask-image: linear-gradient(90deg, transparent 35%, #000);
        }}

        .wb-page-intro__copy {{
            flex: 1 1 auto;
            max-width: 52rem;
        }}

        .wb-eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: .48rem;
            margin: 0 0 .7rem;
            color: color-mix(in srgb, var(--wb-route-primary) 42%, var(--wb-ink));
            font-size: .71rem;
            font-weight: 850;
            letter-spacing: .14em;
            text-transform: uppercase;
        }}

        .wb-eyebrow::before {{
            content: "";
            width: 1.45rem;
            height: 2px;
            border-radius: 99px;
            background: linear-gradient(90deg,
                var(--wb-route-primary),
                var(--wb-route-secondary),
                var(--wb-route-tertiary));
            box-shadow: 0 0 14px color-mix(in srgb, var(--wb-route-primary) 70%, transparent);
        }}

        .wb-page-intro__title {{
            max-width: 21ch;
            margin: 0;
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 880;
            letter-spacing: -.057em;
            line-height: .98;
            text-wrap: balance;
        }}

        .wb-page-intro__description {{
            max-width: 65ch;
            margin: .9rem 0 0;
            color: var(--wb-muted);
            font-size: clamp(.94rem, 1.25vw, 1.08rem);
            line-height: 1.65;
            text-wrap: pretty;
        }}

        .wb-page-intro__badge {{
            flex: 0 1 auto;
            display: inline-flex;
            align-items: center;
            gap: .5rem;
            margin-bottom: .15rem;
            padding: .62rem .88rem;
            border: 1px solid color-mix(in srgb, var(--wb-route-secondary) 31%, var(--wb-line));
            border-radius: 999px;
            background: color-mix(in srgb, var(--wb-route-tertiary) 10%, var(--wb-surface));
            color: var(--wb-ink);
            font-size: .76rem;
            font-weight: 780;
            white-space: normal;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.12);
        }}

        .wb-page-intro__badge::before {{
            content: "";
            width: .48rem;
            height: .48rem;
            border-radius: 50%;
            background: var(--wb-route-tertiary);
            box-shadow: 0 0 0 .25rem color-mix(in srgb, var(--wb-route-tertiary) 14%, transparent),
                0 0 16px color-mix(in srgb, var(--wb-route-tertiary) 72%, transparent);
        }}

        /* ---------- FLOW mascot ---------- */
        .wb-mascot {{
            position: relative;
            display: grid;
            grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr);
            align-items: center;
            min-height: 23.5rem;
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--wb-route-primary) 24%, var(--wb-line));
            border-radius: 2rem;
            background:
                radial-gradient(circle at 25% 42%, color-mix(in srgb, var(--wb-cyan) 15%, transparent), transparent 35%),
                linear-gradient(145deg,
                    color-mix(in srgb, var(--wb-surface) 93%, transparent),
                    color-mix(in srgb, var(--wb-blue) 8%, var(--wb-surface)));
            box-shadow: var(--wb-shadow);
        }}

        .wb-mascot__scene {{
            position: relative;
            display: grid;
            place-items: center;
            min-width: 0;
            min-height: 23.5rem;
        }}

        .wb-mascot__halo {{
            position: absolute;
            width: 13.8rem;
            height: 13.8rem;
            border: 1px solid color-mix(in srgb, var(--wb-cyan) 27%, transparent);
            border-radius: 50%;
            background: radial-gradient(circle,
                color-mix(in srgb, var(--wb-blue) 18%, transparent),
                transparent 68%);
            box-shadow: 0 0 70px color-mix(in srgb, var(--wb-cyan) 18%, transparent),
                inset 0 0 44px color-mix(in srgb, var(--wb-blue) 12%, transparent);
            animation: wb-halo-pulse 3.5s ease-in-out infinite;
        }}

        .wb-mascot__orbit {{
            position: absolute;
            width: 17.2rem;
            height: 17.2rem;
            border: 1px dashed color-mix(in srgb, var(--wb-cyan) 25%, transparent);
            border-radius: 50%;
            animation: wb-orbit 22s linear infinite;
        }}

        .wb-mascot__orbit::before,
        .wb-mascot__orbit::after {{
            content: "";
            position: absolute;
            border-radius: 50%;
            background: var(--wb-cyan);
            box-shadow: 0 0 16px var(--wb-cyan);
        }}

        .wb-mascot__orbit::before {{ width: .55rem; height: .55rem; top: 1.45rem; left: 2.3rem; }}
        .wb-mascot__orbit::after {{ width: .33rem; height: .33rem; right: .8rem; bottom: 4rem; }}

        .wb-drop-character {{
            position: relative;
            z-index: 2;
            width: 11.7rem;
            height: 13.8rem;
            transform-origin: 50% 90%;
            animation: wb-float 3.6s ease-in-out infinite;
        }}

        .wb-drop__tip {{
            position: absolute;
            z-index: 1;
            top: .75rem;
            left: 50%;
            width: 4rem;
            height: 4rem;
            border-radius: 1.1rem .55rem 1.1rem .55rem;
            background: linear-gradient(140deg, #63ECFF, #2B8CFF 56%, #3157F6);
            transform: translateX(-50%) rotate(45deg);
            box-shadow: inset 2px 2px 1px rgba(255,255,255,.34);
        }}

        .wb-drop__body {{
            position: absolute;
            z-index: 2;
            left: 50%;
            bottom: .85rem;
            width: 10.2rem;
            height: 10.8rem;
            border: 1px solid rgba(255,255,255,.4);
            border-radius: 52% 48% 46% 54% / 56% 56% 44% 44%;
            background:
                radial-gradient(circle at 32% 25%, rgba(255,255,255,.92) 0 .42rem, transparent .48rem),
                radial-gradient(circle at 38% 31%, rgba(255,255,255,.35) 0 .84rem, transparent .9rem),
                linear-gradient(145deg, #63ECFF 2%, #25B8F4 35%, #2E77F5 68%, #3546D8 100%);
            transform: translateX(-50%);
            box-shadow:
                inset -1.1rem -1.2rem 2.2rem rgba(20,49,174,.24),
                inset .7rem .75rem 1.25rem rgba(255,255,255,.18),
                0 1.2rem 2.8rem rgba(19,98,230,.3);
            overflow: visible;
        }}

        .wb-drop__body::after {{
            content: "";
            position: absolute;
            inset: .55rem;
            border-radius: inherit;
            border-top: 1px solid rgba(255,255,255,.52);
            opacity: .72;
        }}

        .wb-drop__face {{
            position: absolute;
            z-index: 3;
            inset: 0;
        }}

        .wb-eye {{
            position: absolute;
            top: 4rem;
            width: .9rem;
            height: 1.08rem;
            border-radius: 50%;
            background: #08245C;
            box-shadow: inset .22rem .18rem 0 rgba(255,255,255,.86);
            transform-origin: center;
            animation: wb-blink 5s infinite;
        }}

        .wb-eye--left {{ left: 3rem; }}
        .wb-eye--right {{ right: 3rem; }}

        .wb-cheek {{
            position: absolute;
            top: 5.42rem;
            width: 1.18rem;
            height: .54rem;
            border-radius: 50%;
            background: rgba(255,135,189,.42);
            filter: blur(.5px);
        }}

        .wb-cheek--left {{ left: 1.82rem; }}
        .wb-cheek--right {{ right: 1.82rem; }}

        .wb-mouth {{
            position: absolute;
            top: 5.42rem;
            left: 50%;
            width: 1.5rem;
            height: .78rem;
            border: .2rem solid #08245C;
            border-top: 0;
            border-radius: 0 0 1.2rem 1.2rem;
            transform: translateX(-50%);
            transition: all 280ms ease;
        }}

        .wb-arm {{
            position: absolute;
            z-index: 0;
            top: 7.9rem;
            width: 2.65rem;
            height: .48rem;
            border-radius: 99px;
            background: #2689EC;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.28);
            transform-origin: center right;
        }}

        .wb-arm::after {{
            content: "";
            position: absolute;
            width: .72rem;
            height: .72rem;
            top: -.13rem;
            border-radius: 50%;
            background: #3DBAF2;
        }}

        .wb-arm--left {{ left: -.9rem; transform: rotate(17deg); }}
        .wb-arm--left::after {{ left: -.17rem; }}
        .wb-arm--right {{ right: -.9rem; transform: rotate(-17deg); transform-origin: center left; }}
        .wb-arm--right::after {{ right: -.17rem; }}

        .wb-mascot__shadow {{
            position: absolute;
            z-index: 1;
            bottom: 2.95rem;
            width: 8rem;
            height: 1.05rem;
            border-radius: 50%;
            background: color-mix(in srgb, var(--wb-blue) 34%, transparent);
            filter: blur(9px);
            animation: wb-shadow-breathe 3.6s ease-in-out infinite;
        }}

        .wb-bubble {{
            position: absolute;
            z-index: 1;
            bottom: 3.5rem;
            width: .72rem;
            height: .72rem;
            border: 1px solid color-mix(in srgb, var(--wb-cyan) 70%, white);
            border-radius: 50%;
            background: color-mix(in srgb, var(--wb-cyan) 10%, transparent);
            box-shadow: inset .12rem .12rem 0 rgba(255,255,255,.58),
                0 0 12px color-mix(in srgb, var(--wb-cyan) 35%, transparent);
            opacity: 0;
            animation: wb-bubble-rise 4.2s ease-in infinite;
        }}

        .wb-bubble--one {{ left: 15%; animation-delay: -.4s; }}
        .wb-bubble--two {{ left: 27%; width: .44rem; height: .44rem; animation-delay: -2.1s; }}
        .wb-bubble--three {{ right: 17%; width: 1rem; height: 1rem; animation-delay: -1.25s; }}
        .wb-bubble--four {{ right: 30%; width: .5rem; height: .5rem; animation-delay: -3.2s; }}

        .wb-mascot__copy {{
            position: relative;
            z-index: 2;
            align-self: stretch;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-width: 0;
            padding: clamp(1.6rem, 4vw, 3rem) clamp(1.6rem, 4vw, 3.2rem) clamp(1.6rem, 4vw, 3rem) 1rem;
        }}

        .wb-mascot__status {{
            display: inline-flex;
            align-items: center;
            align-self: flex-start;
            gap: .48rem;
            padding: .44rem .66rem;
            border: 1px solid var(--wb-line);
            border-radius: 999px;
            background: color-mix(in srgb, var(--wb-surface) 75%, transparent);
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 850;
            letter-spacing: .12em;
            text-transform: uppercase;
        }}

        .wb-mascot__status-dot {{
            width: .48rem;
            height: .48rem;
            border-radius: 50%;
            background: var(--wb-aqua);
            box-shadow: 0 0 12px var(--wb-aqua);
        }}

        .wb-mascot__name {{
            margin: .9rem 0 .45rem;
            font-size: clamp(2rem, 4vw, 3.25rem);
            font-weight: 900;
            letter-spacing: -.065em;
            line-height: .95;
        }}

        .wb-mascot__message {{
            max-width: 34ch;
            margin: 0;
            color: var(--wb-muted);
            font-size: .96rem;
            line-height: 1.62;
            text-wrap: pretty;
        }}

        .wb-mascot__meter-label {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.35rem 0 .48rem;
            color: var(--wb-muted);
            font-size: .7rem;
            font-weight: 760;
        }}

        .wb-mascot__meter-label strong {{ color: var(--wb-ink); }}

        .wb-mascot__meter {{
            height: .56rem;
            overflow: hidden;
            border: 1px solid var(--wb-soft-line);
            border-radius: 99px;
            background: color-mix(in srgb, var(--wb-bg) 50%, transparent);
        }}

        .wb-mascot__meter-fill {{
            width: var(--wb-progress);
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, var(--wb-blue), var(--wb-cyan), var(--wb-aqua));
            box-shadow: 0 0 18px color-mix(in srgb, var(--wb-cyan) 55%, transparent);
            transition: width 650ms cubic-bezier(.2,.8,.2,1);
        }}

        /* Mascot state reactions */
        .wb-state-thirsty .wb-drop-character {{ animation: wb-thirsty 3.4s ease-in-out infinite; filter: saturate(.68); }}
        .wb-state-thirsty .wb-eye {{ height: .48rem; top: 4.35rem; box-shadow: none; border-radius: 99px; }}
        .wb-state-thirsty .wb-mouth {{ width: 1.2rem; height: .58rem; top: 5.85rem; border: .18rem solid #08245C; border-bottom: 0; border-radius: 1rem 1rem 0 0; }}
        .wb-state-thirsty .wb-arm--left {{ transform: rotate(-15deg); }}
        .wb-state-thirsty .wb-arm--right {{ transform: rotate(15deg); }}
        .wb-state-thirsty .wb-mascot__status-dot {{ background: var(--wb-warning); box-shadow: 0 0 12px var(--wb-warning); }}

        .wb-state-waking .wb-drop-character {{ animation: wb-waking 3s ease-in-out infinite; }}
        .wb-state-waking .wb-mouth {{ width: .7rem; height: .7rem; border: .17rem solid #08245C; border-radius: 50%; }}
        .wb-state-waking .wb-bubble {{ animation-duration: 5.3s; }}

        .wb-state-flowing .wb-drop-character {{ animation: wb-float 3.1s ease-in-out infinite; }}
        .wb-state-flowing .wb-arm--right {{ animation: wb-small-wave 2.2s ease-in-out infinite; }}

        .wb-state-thriving .wb-drop-character {{ animation: wb-happy-bounce 2.5s ease-in-out infinite; }}
        .wb-state-thriving .wb-drop__body {{ filter: saturate(1.13) brightness(1.04); }}
        .wb-state-thriving .wb-arm--right {{ animation: wb-wave 1.8s ease-in-out infinite; }}
        .wb-state-thriving .wb-mascot__halo {{ box-shadow: 0 0 88px color-mix(in srgb, var(--wb-cyan) 31%, transparent); }}

        .wb-state-goal .wb-drop-character {{ animation: wb-celebrate 1.9s ease-in-out infinite; }}
        .wb-state-goal .wb-drop__body {{ filter: saturate(1.2) brightness(1.08); }}
        .wb-state-goal .wb-eye {{ height: .38rem; top: 4.35rem; box-shadow: none; border-radius: 99px; }}
        .wb-state-goal .wb-mouth {{ width: 1.75rem; height: .92rem; }}
        .wb-state-goal .wb-arm--left {{ animation: wb-wave-left 1.35s ease-in-out infinite; }}
        .wb-state-goal .wb-arm--right {{ animation: wb-wave 1.35s ease-in-out infinite; }}
        .wb-state-goal .wb-mascot__halo {{ animation-duration: 1.6s; }}

        .wb-mascot--compact {{
            grid-template-columns: minmax(5.5rem, 8.5rem) minmax(0, 1fr);
            min-height: 11rem;
            border-radius: 1.5rem;
        }}

        .wb-mascot--compact .wb-mascot__scene {{ min-height: 11rem; transform: scale(.57); }}
        .wb-mascot--compact .wb-mascot__copy {{ padding: 1.15rem 1.2rem 1.15rem .15rem; }}
        .wb-mascot--compact .wb-mascot__name {{ margin-top: .62rem; font-size: 1.65rem; }}
        .wb-mascot--compact .wb-mascot__message {{ font-size: .82rem; line-height: 1.48; }}
        .wb-mascot--compact .wb-mascot__meter-label {{ margin-top: .75rem; }}

        /* ---------- Hydration pet room ---------- */
        .wb-pet {{
            --wb-pet-glow: #38BDF8;
            position: relative;
            isolation: isolate;
            display: grid;
            grid-template-columns: minmax(0, 1.25fr) minmax(0, .75fr);
            min-height: 32rem;
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--wb-route-primary) 24%, var(--wb-line));
            border-radius: 2.1rem;
            background: color-mix(in srgb, var(--wb-surface) 84%, transparent);
            box-shadow: var(--wb-shadow);
        }}

        .wb-pet__room {{
            position: relative;
            min-width: 0;
            min-height: 32rem;
            overflow: hidden;
            background:
                radial-gradient(circle at 50% 22%, color-mix(in srgb, var(--wb-cyan) 15%, transparent), transparent 15rem),
                linear-gradient(180deg,
                    color-mix(in srgb, #15376B 40%, var(--wb-surface)) 0 70%,
                    color-mix(in srgb, #08152D 58%, var(--wb-surface)) 70% 100%);
        }}

        .wb-pet__room::before {{
            content: "";
            position: absolute;
            inset: 0 0 30%;
            opacity: .14;
            background-image:
                linear-gradient(color-mix(in srgb, var(--wb-cyan) 22%, transparent) 1px, transparent 1px),
                linear-gradient(90deg, color-mix(in srgb, var(--wb-cyan) 22%, transparent) 1px, transparent 1px);
            background-size: 2.1rem 2.1rem;
            mask-image: linear-gradient(#000, transparent 90%);
        }}

        .wb-pet__room::after {{
            content: "";
            position: absolute;
            z-index: 1;
            right: -4rem;
            bottom: -4rem;
            left: -4rem;
            height: 13rem;
            border-radius: 50% 50% 0 0 / 18% 18% 0 0;
            background:
                radial-gradient(ellipse at 50% 18%, color-mix(in srgb, var(--wb-blue) 17%, transparent), transparent 45%),
                color-mix(in srgb, #071226 72%, var(--wb-surface));
            box-shadow: inset 0 1px 0 color-mix(in srgb, var(--wb-cyan) 14%, transparent);
        }}

        .wb-pet__window {{
            position: absolute;
            z-index: 1;
            top: 2.6rem;
            right: 2.8rem;
            width: 7.7rem;
            height: 7.7rem;
            overflow: hidden;
            border: .45rem solid color-mix(in srgb, #1D3A6C 72%, var(--wb-line));
            border-radius: 50%;
            background:
                radial-gradient(circle at 67% 28%, #D7FBFF 0 .28rem, transparent .32rem),
                radial-gradient(circle at 35% 35%, rgba(255,255,255,.58) 0 .12rem, transparent .16rem),
                linear-gradient(145deg, #113D70, #0D6D92 55%, #20A7B8);
            box-shadow: 0 0 0 .18rem color-mix(in srgb, var(--wb-cyan) 18%, transparent),
                inset 0 0 2.2rem rgba(12,35,82,.36), 0 1rem 2.6rem rgba(1,8,25,.28);
        }}

        .wb-pet__window::before {{
            content: "";
            position: absolute;
            width: 10rem;
            height: 2.1rem;
            top: .35rem;
            left: -2rem;
            background: rgba(255,255,255,.12);
            transform: rotate(-32deg);
        }}

        .wb-pet__window::after {{
            content: "";
            position: absolute;
            inset: 48% 0 auto;
            height: 1px;
            background: rgba(255,255,255,.18);
            box-shadow: 0 .58rem 0 rgba(255,255,255,.08), 0 1.2rem 0 rgba(255,255,255,.05);
        }}

        .wb-pet__shelf {{
            position: absolute;
            z-index: 2;
            top: 12.2rem;
            left: 2.2rem;
            width: 7.2rem;
            height: .52rem;
            border-radius: 99px;
            background: linear-gradient(90deg, #1D4E7A, #227AA0, #1D4E7A);
            box-shadow: 0 .48rem .8rem rgba(1,8,24,.28), inset 0 1px rgba(255,255,255,.2);
        }}

        .wb-pet__shelf::before {{
            content: "";
            position: absolute;
            left: .82rem;
            bottom: .52rem;
            width: 1.8rem;
            height: 2.25rem;
            border-radius: 1rem 1rem .35rem .35rem;
            background:
                radial-gradient(ellipse at 30% 0, #5EEAD4 0 18%, transparent 21%),
                radial-gradient(ellipse at 62% 8%, #2DD4BF 0 22%, transparent 25%),
                linear-gradient(180deg, transparent 45%, #155E75 46%);
        }}

        .wb-pet__shelf::after {{
            content: "";
            position: absolute;
            right: .75rem;
            bottom: .52rem;
            width: 2.7rem;
            height: 1.55rem;
            border-radius: .35rem .75rem .24rem .24rem;
            background: linear-gradient(135deg, #3157F6, #7C3AED);
            box-shadow: inset 0 1px rgba(255,255,255,.24), -.55rem .15rem 0 -.35rem #22D3EE;
        }}

        .wb-pet__rug {{
            position: absolute;
            z-index: 2;
            left: 50%;
            bottom: 2rem;
            width: min(70%, 24rem);
            height: 5.7rem;
            border: 1px solid color-mix(in srgb, var(--wb-cyan) 17%, transparent);
            border-radius: 50%;
            background:
                radial-gradient(ellipse, color-mix(in srgb, var(--wb-blue) 32%, transparent), transparent 68%),
                color-mix(in srgb, #122C5B 60%, transparent);
            box-shadow: inset 0 0 2rem rgba(34,211,238,.08), 0 .7rem 1.7rem rgba(0,0,0,.25);
            transform: translateX(-50%);
        }}

        .wb-pet__bubble {{
            position: absolute;
            z-index: 2;
            bottom: 5rem;
            width: .72rem;
            height: .72rem;
            border: 1px solid rgba(165,243,252,.72);
            border-radius: 50%;
            background: rgba(34,211,238,.08);
            box-shadow: inset .13rem .13rem rgba(255,255,255,.45), 0 0 1rem rgba(34,211,238,.25);
            animation: wb-pet-bubble 5.8s ease-in infinite;
        }}

        .wb-pet__bubble--one {{ left: 12%; animation-delay: -1s; }}
        .wb-pet__bubble--two {{ left: 29%; width: .42rem; height: .42rem; animation-delay: -3.4s; }}
        .wb-pet__bubble--three {{ right: 17%; width: 1rem; height: 1rem; animation-delay: -2.2s; }}

        .wb-pet__speech {{
            position: absolute;
            z-index: 8;
            top: 2.2rem;
            left: clamp(1.2rem, 4vw, 3rem);
            max-width: min(52%, 17rem);
            padding: .78rem .95rem;
            border: 1px solid color-mix(in srgb, var(--wb-cyan) 27%, var(--wb-line));
            border-radius: 1rem 1rem 1rem .3rem;
            background: color-mix(in srgb, var(--wb-surface) 88%, transparent);
            color: var(--wb-ink);
            font-size: .78rem;
            font-weight: 640;
            line-height: 1.45;
            box-shadow: 0 .8rem 2rem rgba(1,8,24,.22), inset 0 1px rgba(255,255,255,.12);
            backdrop-filter: blur(12px);
            animation: wb-pet-speech 4.5s ease-in-out infinite;
        }}

        .wb-pet__speech::after {{
            content: "";
            position: absolute;
            left: 1rem;
            bottom: -.45rem;
            width: .8rem;
            height: .8rem;
            border-right: 1px solid color-mix(in srgb, var(--wb-cyan) 27%, var(--wb-line));
            border-bottom: 1px solid color-mix(in srgb, var(--wb-cyan) 27%, var(--wb-line));
            background: color-mix(in srgb, var(--wb-surface) 92%, transparent);
            transform: rotate(45deg);
        }}

        .wb-pet__character-wrap {{
            position: absolute;
            z-index: 6;
            left: 50%;
            bottom: 3.2rem;
            width: 13.5rem;
            height: 16.5rem;
            transform: translateX(-50%);
        }}

        .wb-pet__tap-target {{
            position: absolute;
            z-index: 2;
            inset: 0;
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            border: 0;
            border-radius: 48%;
            background: transparent;
            color: inherit;
            cursor: pointer;
            -webkit-tap-highlight-color: transparent;
        }}

        .wb-pet__tap-target:focus-visible {{
            outline: 3px solid var(--wb-cyan);
            outline-offset: .3rem;
        }}

        .wb-pet__tap-target:is(:hover, :focus) .wb-pet__character {{
            filter: saturate(1.16) brightness(1.06);
        }}

        .wb-pet__tap-target:focus .wb-pet__character {{
            animation: wb-pet-boop .9s cubic-bezier(.2,.8,.2,1) both;
        }}

        .wb-pet__tap-target:active .wb-pet__character {{
            scale: .94 1.04;
        }}

        .wb-pet__speech {{
            transition: opacity 180ms ease, visibility 180ms ease, transform 180ms ease;
        }}

        .wb-pet__speech--tap {{
            visibility: hidden;
            opacity: 0;
            animation: none;
            transform: translateY(.35rem) scale(.96);
        }}

        .wb-pet:has(.wb-pet__tap-target:focus) .wb-pet__speech--default {{
            visibility: hidden;
            opacity: 0;
        }}

        .wb-pet:has(.wb-pet__tap-target:focus) .wb-pet__speech--tap {{
            visibility: visible;
            opacity: 1;
            transform: translateY(0) scale(1);
        }}

        .wb-pet__aura {{
            position: absolute;
            z-index: -1;
            inset: 1.3rem -.2rem .2rem;
            border: 1px solid color-mix(in srgb, var(--wb-pet-glow) 33%, transparent);
            border-radius: 50%;
            background: radial-gradient(circle, color-mix(in srgb, var(--wb-pet-glow) 20%, transparent), transparent 65%);
            box-shadow: 0 0 4.5rem color-mix(in srgb, var(--wb-pet-glow) 22%, transparent);
            animation: wb-pet-aura 3.6s ease-in-out infinite;
        }}

        .wb-pet__character {{
            position: absolute;
            inset: 0;
            transform-origin: 50% 92%;
            animation: wb-pet-idle 3.4s ease-in-out infinite;
        }}

        .wb-pet__tip {{
            position: absolute;
            z-index: 2;
            top: 1.35rem;
            left: 50%;
            width: 4.65rem;
            height: 4.65rem;
            border-radius: 1.35rem .58rem 1.35rem .58rem;
            background: linear-gradient(145deg, #70F0FF, #28B8F1 46%, #3157F6);
            box-shadow: inset .18rem .2rem rgba(255,255,255,.3);
            transform: translateX(-50%) rotate(45deg);
        }}

        .wb-pet__body {{
            position: absolute;
            z-index: 3;
            left: 50%;
            bottom: 1.05rem;
            width: 11.65rem;
            height: 12.4rem;
            overflow: visible;
            border: 1px solid rgba(255,255,255,.38);
            border-radius: 53% 47% 46% 54% / 56% 56% 44% 44%;
            background:
                radial-gradient(circle at 31% 24%, rgba(255,255,255,.9) 0 .38rem, transparent .44rem),
                radial-gradient(circle at 37% 29%, rgba(255,255,255,.28) 0 .9rem, transparent .98rem),
                linear-gradient(145deg, #67E8F9, #20B6EB 35%, #2874ED 68%, #4835CB);
            box-shadow: inset -1.2rem -1.4rem 2.4rem rgba(33,30,145,.25),
                inset .7rem .8rem 1.4rem rgba(255,255,255,.16),
                0 1.25rem 2.8rem rgba(20,77,218,.34);
            transform: translateX(-50%);
        }}

        .wb-pet__belly {{
            position: absolute;
            z-index: 1;
            left: 50%;
            bottom: .72rem;
            width: 6.4rem;
            height: 4.9rem;
            border-radius: 50%;
            background: radial-gradient(ellipse, rgba(159,242,255,.24), transparent 72%);
            transform: translateX(-50%);
        }}

        .wb-pet__eye {{
            position: absolute;
            z-index: 5;
            top: 4.55rem;
            width: 1.18rem;
            height: 1.4rem;
            border-radius: 52% 48% 50% 50%;
            background: #061E52;
            box-shadow: inset .3rem .25rem rgba(255,255,255,.9), 0 .15rem .2rem rgba(1,8,24,.16);
            transform-origin: center;
            animation: wb-pet-blink 5.4s infinite;
        }}

        .wb-pet__eye--left {{ left: 3.15rem; }}
        .wb-pet__eye--right {{ right: 3.15rem; }}

        .wb-pet__cheek {{
            position: absolute;
            z-index: 4;
            top: 6.05rem;
            width: 1.32rem;
            height: .58rem;
            border-radius: 50%;
            background: rgba(252,138,190,.42);
            filter: blur(.7px);
        }}

        .wb-pet__cheek--left {{ left: 1.75rem; }}
        .wb-pet__cheek--right {{ right: 1.75rem; }}

        .wb-pet__mouth {{
            position: absolute;
            z-index: 5;
            top: 6.1rem;
            left: 50%;
            width: 1.65rem;
            height: .85rem;
            border: .2rem solid #061E52;
            border-top: 0;
            border-radius: 0 0 1.2rem 1.2rem;
            transform: translateX(-50%);
        }}

        .wb-pet__fin {{
            position: absolute;
            z-index: 1;
            top: 8rem;
            width: 3.25rem;
            height: 2.15rem;
            border: 1px solid rgba(255,255,255,.28);
            background: linear-gradient(135deg, rgba(82,225,247,.92), rgba(39,101,224,.92));
            box-shadow: inset 0 1px rgba(255,255,255,.22);
        }}

        .wb-pet__fin--left {{
            left: -.9rem;
            border-radius: 80% 20% 70% 30%;
            transform: rotate(-24deg);
            transform-origin: right center;
        }}

        .wb-pet__fin--right {{
            right: -.9rem;
            border-radius: 20% 80% 30% 70%;
            transform: rotate(24deg);
            transform-origin: left center;
        }}

        .wb-pet__crest {{
            position: absolute;
            z-index: 1;
            top: 2.25rem;
            left: 50%;
            width: 7.7rem;
            height: 2.6rem;
            border-radius: 50%;
            background: linear-gradient(90deg, transparent, rgba(45,212,191,.58), transparent);
            filter: blur(1px);
            transform: translateX(-50%) rotate(-9deg);
        }}

        .wb-pet__crest::before,
        .wb-pet__crest::after {{
            content: "";
            position: absolute;
            top: -.25rem;
            width: 2.1rem;
            height: 3.2rem;
            border-radius: 70% 30% 65% 35%;
            background: linear-gradient(160deg, rgba(103,232,249,.72), rgba(49,87,246,.28));
            transform: rotate(24deg);
        }}

        .wb-pet__crest::before {{ left: .45rem; }}
        .wb-pet__crest::after {{ right: .45rem; transform: scaleX(-1) rotate(24deg); }}

        .wb-pet__accessory {{
            position: absolute;
            z-index: 9;
            top: 2.55rem;
            left: 50%;
            display: none;
            transform: translateX(-50%);
        }}

        .wb-pet__gear {{
            position: absolute;
            display: none;
            pointer-events: none;
        }}

        .wb-accessory-crown .wb-pet__accessory {{
            display: block;
            width: 4.5rem;
            height: 2.5rem;
            clip-path: polygon(0 88%, 7% 22%, 30% 58%, 50% 4%, 70% 58%, 93% 22%, 100% 88%);
            background: linear-gradient(145deg, #FEF08A, #FBBF24 58%, #D97706);
            filter: drop-shadow(0 .42rem .38rem rgba(110,62,5,.25));
        }}

        .wb-accessory-glasses .wb-pet__accessory {{
            display: block;
            top: 6.5rem;
            width: 3.05rem;
            height: 1px;
            border-top: .19rem solid #092454;
        }}

        .wb-accessory-glasses .wb-pet__accessory::before,
        .wb-accessory-glasses .wb-pet__accessory::after {{
            content: "";
            position: absolute;
            top: -.55rem;
            width: 1.35rem;
            height: 1.05rem;
            border: .2rem solid #092454;
            border-radius: .48rem;
            background: rgba(186,248,255,.14);
        }}

        .wb-accessory-glasses .wb-pet__accessory::before {{ left: -.18rem; }}
        .wb-accessory-glasses .wb-pet__accessory::after {{ right: -.18rem; }}

        .wb-accessory-leaf .wb-pet__accessory {{
            display: block;
            top: 3.05rem;
            width: 2.7rem;
            height: 1.35rem;
            border-radius: 100% 0 100% 0;
            background: linear-gradient(145deg, #A7F3D0, #10B981);
            box-shadow: inset 0 1px rgba(255,255,255,.35), 0 .35rem .7rem rgba(6,95,70,.2);
            transform: translateX(-50%) rotate(-16deg);
        }}

        .wb-accessory-bow .wb-pet__accessory {{
            display: block;
            top: 4.05rem;
            margin-left: 3.45rem;
            width: 1rem;
            height: 1rem;
            border-radius: .3rem;
            background: #F472B6;
            box-shadow: 0 .35rem .7rem rgba(131,24,67,.23);
        }}

        .wb-accessory-bow .wb-pet__accessory::before,
        .wb-accessory-bow .wb-pet__accessory::after {{
            content: "";
            position: absolute;
            top: -.2rem;
            width: 1.28rem;
            height: 1.35rem;
            border-radius: 70% 30% 70% 30%;
            background: linear-gradient(145deg, #F9A8D4, #EC4899);
        }}

        .wb-accessory-bow .wb-pet__accessory::before {{ right: .68rem; transform: rotate(-18deg); }}
        .wb-accessory-bow .wb-pet__accessory::after {{ left: .68rem; transform: scaleX(-1) rotate(-18deg); }}

        .wb-accessory-scarf .wb-pet__accessory {{
            display: block;
            top: 9.3rem;
            width: 8.2rem;
            height: 1.2rem;
            border-radius: 99px;
            background: linear-gradient(90deg, #FB7185, #F43F5E, #BE123C);
            box-shadow: inset 0 1px rgba(255,255,255,.25), 0 .4rem .8rem rgba(136,19,55,.18);
        }}

        .wb-accessory-star .wb-pet__accessory {{
            display: block;
            top: 4.1rem;
            margin-left: 3.4rem;
            width: 1.9rem;
            height: 1.9rem;
            clip-path: polygon(50% 0, 61% 36%, 100% 38%, 69% 60%, 80% 100%, 50% 76%, 20% 100%, 31% 60%, 0 38%, 39% 36%);
            background: linear-gradient(145deg, #FEF08A, #F59E0B);
            filter: drop-shadow(0 0 .65rem rgba(251,191,36,.52));
            animation: wb-pet-star 3s ease-in-out infinite;
        }}

        /* Full costume accessories share fixed, non-user-controlled gear layers. */
        .wb-accessory-samurai .wb-pet__accessory,
        .wb-accessory-cyborg .wb-pet__accessory,
        .wb-accessory-cool-guy .wb-pet__accessory {{
            inset: 0;
            display: block;
            width: 100%;
            height: 100%;
            margin: 0;
            border: 0;
            background: none;
            filter: none;
            clip-path: none;
            transform: none;
        }}

        .wb-accessory-samurai .wb-pet__gear,
        .wb-accessory-cyborg .wb-pet__gear,
        .wb-accessory-cool-guy .wb-pet__gear {{
            display: block;
        }}

        .wb-accessory-samurai .wb-pet__crest,
        .wb-accessory-cyborg .wb-pet__crest,
        .wb-accessory-cool-guy .wb-pet__crest {{
            display: none;
        }}

        /* Samurai fit: ceremonial kabuto, crest, cheek guards, and lamellar shoulders. */
        .wb-accessory-samurai .wb-pet__gear--head {{
            z-index: 4;
            top: -1.05rem;
            left: 50%;
            width: 7.65rem;
            height: 4.25rem;
            border: 1px solid rgba(255,255,255,.25);
            border-radius: 52% 48% 24% 24% / 62% 62% 38% 38%;
            background:
                linear-gradient(90deg, transparent 47%, rgba(251,191,36,.8) 48% 52%, transparent 53%),
                linear-gradient(145deg, #314468 2%, #13233F 46%, #071225 78%, #243A61);
            box-shadow: inset .7rem .6rem 1rem rgba(255,255,255,.1),
                inset -.8rem -.55rem 1rem rgba(1,8,24,.38),
                0 .65rem 1.2rem rgba(1,8,24,.28);
            clip-path: polygon(12% 10%, 32% 0, 50% 7%, 68% 0, 88% 10%, 100% 64%, 87% 93%, 65% 76%, 50% 94%, 35% 76%, 13% 93%, 0 64%);
            transform: translateX(-50%);
        }}

        .wb-accessory-samurai .wb-pet__gear--head::before {{
            content: "";
            position: absolute;
            top: -1.5rem;
            left: 50%;
            width: 3.75rem;
            height: 2.35rem;
            border: .42rem solid #F5C451;
            border-bottom: 0;
            border-radius: 60% 60% 0 0;
            filter: drop-shadow(0 .22rem .3rem rgba(104,63,6,.34));
            transform: translateX(-50%) rotate(-3deg);
        }}

        .wb-accessory-samurai .wb-pet__gear--head::after {{
            content: "";
            position: absolute;
            top: .22rem;
            left: 50%;
            width: .52rem;
            height: 3.15rem;
            background: linear-gradient(180deg, #FFF3A6, #E5A92D 65%, #9A5B0B);
            clip-path: polygon(50% 0, 100% 16%, 70% 100%, 30% 100%, 0 16%);
            transform: translateX(-50%);
            animation: wb-samurai-glint 4.8s ease-in-out infinite;
        }}

        .wb-accessory-samurai .wb-pet__gear--face {{
            z-index: 3;
            top: 2.55rem;
            left: 50%;
            width: 9rem;
            height: 4rem;
            background:
                linear-gradient(90deg,
                    #172A48 0 18%, #324A70 19% 25%, transparent 26% 74%,
                    #324A70 75% 81%, #172A48 82% 100%);
            clip-path: polygon(0 0, 28% 12%, 23% 100%, 7% 82%, 0 35%, 100% 35%, 93% 82%, 77% 100%, 72% 12%, 100% 0);
            filter: drop-shadow(0 .45rem .42rem rgba(1,8,24,.25));
            transform: translateX(-50%);
        }}

        .wb-accessory-samurai .wb-pet__gear--face::before,
        .wb-accessory-samurai .wb-pet__gear--face::after {{
            content: "";
            position: absolute;
            top: .48rem;
            width: .36rem;
            height: 2.75rem;
            border-radius: 99px;
            background: repeating-linear-gradient(180deg, #E5A92D 0 .22rem, #8B540D .23rem .4rem);
        }}

        .wb-accessory-samurai .wb-pet__gear--face::before {{ left: 1.22rem; transform: rotate(9deg); }}
        .wb-accessory-samurai .wb-pet__gear--face::after {{ right: 1.22rem; transform: rotate(-9deg); }}

        .wb-accessory-samurai .wb-pet__gear--body {{
            z-index: 2;
            top: 7.35rem;
            left: 50%;
            width: 13.1rem;
            height: 4.4rem;
            border-top: 1px solid rgba(255,255,255,.24);
            background:
                repeating-linear-gradient(180deg, rgba(246,196,81,.7) 0 .12rem, transparent .13rem .68rem),
                linear-gradient(100deg, #0B1830, #2B426A 19%, #101E39 38%, transparent 39% 61%, #101E39 62%, #2B426A 81%, #0B1830);
            box-shadow: inset 0 .65rem 1rem rgba(255,255,255,.06), 0 .7rem 1rem rgba(1,8,24,.18);
            clip-path: polygon(0 20%, 23% 0, 42% 16%, 50% 6%, 58% 16%, 77% 0, 100% 20%, 91% 92%, 67% 76%, 50% 100%, 33% 76%, 9% 92%);
            transform: translateX(-50%);
        }}

        .wb-accessory-samurai .wb-pet__gear--body::before {{
            content: "";
            position: absolute;
            inset: .45rem 4.35rem .1rem;
            border: 1px solid rgba(245,196,81,.62);
            border-radius: .5rem;
            background: linear-gradient(145deg, rgba(49,68,104,.92), rgba(7,18,37,.86));
        }}

        /* Cyborg fit: alloy temple panel, optical visor, core, and circuit traces. */
        .wb-accessory-cyborg .wb-pet__gear--head {{
            z-index: 3;
            top: 1.4rem;
            right: -.2rem;
            width: 4.75rem;
            height: 5.9rem;
            border: 1px solid rgba(165,243,252,.42);
            border-left: 0;
            border-radius: 20% 48% 46% 20%;
            background:
                linear-gradient(120deg, transparent 0 18%, rgba(111,134,168,.72) 19% 34%, rgba(20,35,58,.82) 35% 100%);
            box-shadow: inset -.6rem .2rem 1rem rgba(56,217,242,.12), .45rem .2rem 1rem rgba(1,8,24,.22);
            clip-path: polygon(24% 0, 82% 8%, 100% 34%, 89% 81%, 54% 100%, 11% 80%, 22% 57%, 0 36%);
        }}

        .wb-accessory-cyborg .wb-pet__gear--head::before {{
            content: "";
            position: absolute;
            inset: .7rem .42rem .72rem 1.05rem;
            opacity: .72;
            background:
                linear-gradient(90deg, transparent 0 44%, #58E8F7 45% 51%, transparent 52%),
                linear-gradient(0deg, transparent 0 36%, #58E8F7 37% 42%, transparent 43%);
            background-size: 1.4rem 1.25rem;
            filter: drop-shadow(0 0 .24rem #22D3EE);
        }}

        .wb-accessory-cyborg .wb-pet__gear--head::after {{
            content: "";
            position: absolute;
            top: -1.25rem;
            right: .8rem;
            width: .18rem;
            height: 1.7rem;
            border-radius: 99px;
            background: linear-gradient(#91F4FF, #188CB4);
            box-shadow: 0 -.18rem 0 .2rem #38D9F2, 0 -.18rem .7rem .25rem rgba(56,217,242,.55);
        }}

        .wb-accessory-cyborg .wb-pet__gear--face {{
            z-index: 5;
            top: 4.15rem;
            left: 50%;
            width: 7.15rem;
            height: 2rem;
            overflow: hidden;
            border: 1px solid rgba(145,244,255,.68);
            border-radius: .55rem 1rem .55rem 1rem;
            background:
                linear-gradient(100deg, rgba(3,12,29,.9), rgba(18,50,76,.72) 48%, rgba(3,12,29,.9));
            box-shadow: inset 0 0 .8rem rgba(34,211,238,.2), 0 0 .75rem rgba(56,217,242,.32);
            clip-path: polygon(3% 8%, 96% 0, 100% 64%, 86% 100%, 8% 92%, 0 44%);
            transform: translateX(-50%);
        }}

        .wb-accessory-cyborg .wb-pet__gear--face::before {{
            content: "";
            position: absolute;
            inset: 0 auto 0 -28%;
            width: 26%;
            background: linear-gradient(90deg, transparent, rgba(145,244,255,.84), transparent);
            filter: blur(1px);
            animation: wb-cyborg-scan 3.2s ease-in-out infinite;
        }}

        .wb-accessory-cyborg .wb-pet__gear--face::after {{
            content: "";
            position: absolute;
            right: .75rem;
            bottom: .34rem;
            width: 1.35rem;
            height: .18rem;
            border-radius: 99px;
            background: #38D9F2;
            box-shadow: 0 0 .65rem #22D3EE;
        }}

        .wb-accessory-cyborg .wb-pet__gear--body {{
            z-index: 3;
            top: 7.3rem;
            left: 50%;
            width: 8.25rem;
            height: 4.8rem;
            border: 1px solid rgba(165,243,252,.36);
            border-radius: 42% 42% 48% 48%;
            background:
                linear-gradient(120deg, rgba(19,35,59,.84), rgba(113,137,171,.5) 28%, rgba(13,28,51,.8) 55%, rgba(57,80,112,.62));
            box-shadow: inset 0 .6rem .9rem rgba(255,255,255,.07), 0 .6rem 1.1rem rgba(1,8,24,.2);
            clip-path: polygon(12% 8%, 40% 0, 50% 13%, 60% 0, 88% 8%, 100% 54%, 82% 100%, 18% 100%, 0 54%);
            transform: translateX(-50%);
        }}

        .wb-accessory-cyborg .wb-pet__gear--body::before {{
            content: "";
            position: absolute;
            top: 1.05rem;
            left: 50%;
            width: 1.65rem;
            height: 1.65rem;
            border: .22rem solid #9FF5FC;
            border-radius: 50%;
            background: radial-gradient(circle, #FFFFFF 0 12%, #38D9F2 18% 38%, #3157F6 54%, #0B1730 58%);
            box-shadow: 0 0 .95rem rgba(56,217,242,.78), inset 0 0 .45rem rgba(255,255,255,.65);
            transform: translateX(-50%);
            animation: wb-cyborg-core 2.4s ease-in-out infinite;
        }}

        .wb-accessory-cyborg .wb-pet__gear--body::after {{
            content: "";
            position: absolute;
            inset: .7rem .85rem;
            opacity: .7;
            background:
                linear-gradient(90deg, transparent 0 18%, #38D9F2 19% 21%, transparent 22% 78%, #38D9F2 79% 81%, transparent 82%),
                linear-gradient(0deg, transparent 0 72%, #38D9F2 73% 76%, transparent 77%);
            filter: drop-shadow(0 0 .22rem rgba(56,217,242,.65));
        }}

        /* Cool Guy fit: soft-brim cap, polished sunglasses, and cropped jacket. */
        .wb-accessory-cool-guy .wb-pet__gear--head {{
            z-index: 4;
            top: -.72rem;
            left: 50%;
            width: 7.15rem;
            height: 3.55rem;
            border: 1px solid rgba(255,255,255,.2);
            border-radius: 60% 46% 22% 18% / 72% 65% 35% 28%;
            background: linear-gradient(145deg, #263E75, #16264F 62%, #0B1532);
            box-shadow: inset .55rem .45rem .85rem rgba(255,255,255,.09),
                1.3rem 1.85rem 0 -1.2rem #0A1532,
                0 .6rem 1rem rgba(1,8,24,.2);
            clip-path: polygon(7% 20%, 29% 2%, 72% 0, 94% 23%, 100% 78%, 67% 74%, 49% 90%, 0 82%);
            transform: translateX(-50%) rotate(-4deg);
        }}

        .wb-accessory-cool-guy .wb-pet__gear--head::before {{
            content: "";
            position: absolute;
            right: -.95rem;
            bottom: -.05rem;
            width: 3.75rem;
            height: .8rem;
            border-radius: 0 99px 99px 0;
            background: linear-gradient(90deg, #101E42, #263E75);
            box-shadow: 0 .28rem .45rem rgba(1,8,24,.2);
            transform: rotate(5deg);
        }}

        .wb-accessory-cool-guy .wb-pet__gear--face {{
            z-index: 6;
            top: 4.22rem;
            left: 50%;
            width: 6.55rem;
            height: 1.8rem;
            overflow: hidden;
            border: .18rem solid #071225;
            border-radius: .85rem .85rem 1.05rem 1.05rem;
            background:
                linear-gradient(90deg, rgba(3,9,23,.94) 0 44%, transparent 44.5% 55.5%, rgba(3,9,23,.94) 56% 100%);
            box-shadow: inset 0 .22rem .32rem rgba(103,232,249,.14), 0 .35rem .55rem rgba(1,8,24,.22);
            clip-path: polygon(0 4%, 45% 12%, 50% 34%, 55% 12%, 100% 4%, 93% 94%, 59% 88%, 50% 54%, 41% 88%, 7% 94%);
            transform: translateX(-50%);
        }}

        .wb-accessory-cool-guy .wb-pet__gear--face::before {{
            content: "";
            position: absolute;
            top: .18rem;
            left: .5rem;
            width: 1.6rem;
            height: .24rem;
            border-radius: 99px;
            background: rgba(255,255,255,.56);
            box-shadow: 3.55rem .2rem 0 -.04rem rgba(255,255,255,.4);
            transform: rotate(-9deg);
            animation: wb-cool-lens 4.2s ease-in-out infinite;
        }}

        .wb-accessory-cool-guy .wb-pet__gear--body {{
            z-index: 3;
            top: 7.45rem;
            left: 50%;
            width: 10.9rem;
            height: 5rem;
            border-top: 1px solid rgba(255,255,255,.2);
            border-radius: 34% 34% 45% 45%;
            background:
                linear-gradient(112deg, #16294E 0 34%, #38BDF8 35% 37%, transparent 38% 62%, #38BDF8 63% 65%, #16294E 66% 100%);
            box-shadow: inset 0 .65rem .9rem rgba(255,255,255,.06), 0 .55rem 1rem rgba(1,8,24,.18);
            clip-path: polygon(4% 16%, 34% 0, 50% 34%, 66% 0, 96% 16%, 100% 76%, 76% 100%, 58% 74%, 50% 92%, 42% 74%, 24% 100%, 0 76%);
            transform: translateX(-50%);
        }}

        .wb-accessory-cool-guy .wb-pet__gear--body::before {{
            content: "";
            position: absolute;
            top: .3rem;
            left: 50%;
            width: 2.9rem;
            height: 3.6rem;
            border-inline: .18rem solid rgba(103,232,249,.56);
            background: linear-gradient(145deg, transparent 0 42%, rgba(255,255,255,.09) 43% 57%, transparent 58%);
            transform: translateX(-50%);
        }}

        /* Evolution stages */
        .wb-pet-stage-sprout .wb-pet__character {{ transform: scale(.74); }}
        .wb-pet-stage-sprout .wb-pet__aura {{ opacity: .35; transform: scale(.76); }}
        .wb-pet-stage-sprout .wb-pet__fin,
        .wb-pet-stage-sprout .wb-pet__crest {{ display: none; }}
        .wb-pet-stage-sprout .wb-pet__body {{ filter: saturate(.84) brightness(1.08); }}

        .wb-pet-stage-ripple .wb-pet__character {{ transform: scale(.88); }}
        .wb-pet-stage-ripple .wb-pet__crest {{ display: none; }}
        .wb-pet-stage-ripple .wb-pet__fin {{ transform: scale(.72) rotate(-24deg); }}
        .wb-pet-stage-ripple .wb-pet__fin--right {{ transform: scale(.72) rotate(24deg); }}

        .wb-pet-stage-wave .wb-pet__character {{ transform: scale(1); }}
        .wb-pet-stage-wave .wb-pet__crest {{ opacity: .54; }}

        .wb-pet-stage-guardian {{ --wb-pet-glow: #A78BFA; }}
        .wb-pet-stage-guardian .wb-pet__character {{ transform: scale(1.06); }}
        .wb-pet-stage-guardian .wb-pet__crest {{ opacity: .92; filter: drop-shadow(0 0 .8rem rgba(167,139,250,.44)); }}
        .wb-pet-stage-guardian .wb-pet__fin {{ width: 3.8rem; filter: drop-shadow(0 0 .55rem rgba(45,212,191,.3)); }}
        .wb-pet-stage-guardian .wb-pet__aura {{ border-style: dashed; animation-duration: 2.5s; }}

        /* Pet moods */
        .wb-pet-mood-thirsty .wb-pet__character {{ filter: saturate(.55); animation-name: wb-pet-tired; }}
        .wb-pet-mood-thirsty .wb-pet__eye {{ height: .48rem; top: 5rem; box-shadow: none; border-radius: 99px; }}
        .wb-pet-mood-thirsty .wb-pet__mouth {{ width: 1.25rem; height: .58rem; top: 6.55rem; border: .18rem solid #061E52; border-bottom: 0; border-radius: 1rem 1rem 0 0; }}

        .wb-pet-mood-sleepy .wb-pet__character {{ animation: wb-pet-sleepy 4.7s ease-in-out infinite; }}
        .wb-pet-mood-sleepy .wb-pet__eye {{ height: .22rem; top: 5rem; border-radius: 99px; box-shadow: none; animation: none; }}
        .wb-pet-mood-sleepy .wb-pet__mouth {{ width: .72rem; height: .72rem; border: .17rem solid #061E52; border-radius: 50%; }}

        .wb-pet-mood-excited .wb-pet__character {{ animation: wb-pet-excited 1.8s ease-in-out infinite; }}
        .wb-pet-mood-excited .wb-pet__fin--left {{ animation: wb-pet-fin-left 1.25s ease-in-out infinite; }}
        .wb-pet-mood-excited .wb-pet__fin--right {{ animation: wb-pet-fin-right 1.25s ease-in-out infinite; }}
        .wb-pet-mood-excited .wb-pet__mouth {{ width: 1.8rem; height: 1rem; }}

        .wb-pet-mood-curious .wb-pet__character {{ animation: wb-pet-curious 3.8s ease-in-out infinite; }}
        .wb-pet-mood-curious .wb-pet__mouth {{ width: .7rem; height: .7rem; border: .17rem solid #061E52; border-radius: 50%; }}

        .wb-pet__panel {{
            position: relative;
            z-index: 4;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-width: 0;
            padding: clamp(1.5rem, 3vw, 2.55rem);
            border-left: 1px solid var(--wb-soft-line);
            background:
                radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--wb-pet-glow) 12%, transparent), transparent 13rem),
                color-mix(in srgb, var(--wb-surface) 86%, transparent);
        }}

        .wb-pet__kicker {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .7rem;
        }}

        .wb-pet__stage {{
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            padding: .42rem .62rem;
            border: 1px solid color-mix(in srgb, var(--wb-pet-glow) 28%, var(--wb-line));
            border-radius: 999px;
            background: color-mix(in srgb, var(--wb-pet-glow) 9%, var(--wb-surface));
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 820;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}

        .wb-pet__stage::before {{
            content: "";
            width: .45rem;
            height: .45rem;
            border-radius: 50%;
            background: var(--wb-pet-glow);
            box-shadow: 0 0 .75rem var(--wb-pet-glow);
        }}

        .wb-pet__mood {{
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 720;
        }}

        .wb-pet__name {{
            margin: 1rem 0 .25rem;
            overflow-wrap: anywhere;
            font-size: clamp(2rem, 4vw, 3.5rem);
            font-weight: 900;
            letter-spacing: -.065em;
            line-height: .94;
        }}

        .wb-pet__level {{
            margin: 0 0 1.4rem;
            color: var(--wb-muted);
            font-size: .8rem;
            font-weight: 650;
        }}

        .wb-pet__stat {{ margin-top: .82rem; }}

        .wb-pet__stat-label {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .8rem;
            margin-bottom: .38rem;
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 720;
        }}

        .wb-pet__stat-label strong {{ color: var(--wb-ink); }}

        .wb-pet__track {{
            height: .52rem;
            overflow: hidden;
            border: 1px solid var(--wb-soft-line);
            border-radius: 99px;
            background: color-mix(in srgb, var(--wb-bg) 48%, transparent);
        }}

        .wb-pet__fill {{
            width: var(--wb-pet-value);
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, var(--wb-blue), var(--wb-cyan));
            box-shadow: 0 0 1rem color-mix(in srgb, var(--wb-cyan) 36%, transparent);
            transition: width 650ms cubic-bezier(.2,.8,.2,1);
        }}

        .wb-pet__fill--energy {{ background: linear-gradient(90deg, #F59E0B, #FACC15); }}
        .wb-pet__fill--happy {{ background: linear-gradient(90deg, #EC4899, #A78BFA); }}
        .wb-pet__fill--xp {{ background: linear-gradient(90deg, #3157F6, #22D3EE, #2DD4BF); }}

        .wb-pet__hint {{
            margin: 1.35rem 0 0;
            padding: .8rem .9rem;
            border: 1px solid var(--wb-soft-line);
            border-radius: 1rem;
            background: color-mix(in srgb, var(--wb-bg) 34%, transparent);
            color: var(--wb-muted);
            font-size: .72rem;
            line-height: 1.5;
        }}

        .wb-pet--compact {{
            display: block;
            min-height: 14rem;
            border-radius: 1.55rem;
        }}

        .wb-pet--compact .wb-pet__room {{ min-height: 14rem; }}
        .wb-pet--compact .wb-pet__window {{ top: 1rem; right: 1rem; width: 4.8rem; height: 4.8rem; }}
        .wb-pet--compact .wb-pet__shelf {{ display: none; }}
        .wb-pet--compact .wb-pet__rug {{ bottom: .45rem; height: 3.8rem; }}
        .wb-pet--compact .wb-pet__speech {{ top: .8rem; left: .8rem; max-width: 56%; padding: .55rem .68rem; font-size: .75rem; }}
        .wb-pet--compact .wb-pet__character-wrap {{ bottom: -.55rem; transform: translateX(-50%) scale(.54); }}
        .wb-pet--compact .wb-pet__panel {{
            position: absolute;
            right: .85rem;
            bottom: .85rem;
            left: .85rem;
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, max-content);
            align-items: end;
            padding: .75rem .82rem;
            border: 1px solid var(--wb-line);
            border-radius: 1rem;
            background: color-mix(in srgb, var(--wb-surface) 80%, transparent);
            box-shadow: 0 .7rem 1.7rem rgba(1,8,24,.18);
            backdrop-filter: blur(12px);
        }}
        .wb-pet--compact .wb-pet__kicker,
        .wb-pet--compact .wb-pet__level,
        .wb-pet--compact .wb-pet__stat,
        .wb-pet--compact .wb-pet__hint {{ display: none; }}
        .wb-pet--compact .wb-pet__name {{ margin: 0; font-size: 1.45rem; }}
        .wb-pet--compact .wb-pet__panel::after {{
            min-width: 0;
            max-width: 100%;
            content: attr(data-compact-meta);
            overflow-wrap: anywhere;
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 720;
            text-align: right;
        }}

        /* ---------- Bottle progress ---------- */
        .wb-bottle-card {{
            display: grid;
            grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr);
            align-items: center;
            min-height: 20rem;
            padding: clamp(1.2rem, 3vw, 2rem);
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--wb-route-primary) 24%, var(--wb-line));
            border-radius: 2rem;
            background:
                radial-gradient(circle at 25% 52%, color-mix(in srgb, var(--wb-cyan) 13%, transparent), transparent 32%),
                linear-gradient(145deg, color-mix(in srgb, var(--wb-surface) 92%, transparent), color-mix(in srgb, var(--wb-blue) 7%, var(--wb-surface)));
            box-shadow: var(--wb-shadow);
        }}

        .wb-bottle__visual {{
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 16rem;
        }}

        .wb-bottle__cap {{
            z-index: 3;
            width: 3.7rem;
            height: 1rem;
            border: 1px solid rgba(255,255,255,.3);
            border-radius: .55rem .55rem .28rem .28rem;
            background: linear-gradient(90deg, #1E40AF, #2563EB 45%, #1D4ED8);
            box-shadow: 0 5px 15px rgba(15,50,160,.25), inset 0 1px 0 rgba(255,255,255,.3);
        }}

        .wb-bottle__neck {{
            width: 3.15rem;
            height: 1.05rem;
            border-inline: 2px solid color-mix(in srgb, var(--wb-cyan) 55%, var(--wb-line));
            background: color-mix(in srgb, var(--wb-surface) 48%, transparent);
        }}

        .wb-bottle__shell {{
            position: relative;
            width: 7.35rem;
            height: 12.3rem;
            overflow: hidden;
            border: 2px solid color-mix(in srgb, var(--wb-cyan) 45%, var(--wb-line));
            border-radius: 1.8rem 1.8rem 2.4rem 2.4rem;
            background: linear-gradient(100deg,
                rgba(255,255,255,.09),
                color-mix(in srgb, var(--wb-surface) 42%, transparent) 38%,
                rgba(255,255,255,.03));
            box-shadow: inset .65rem 0 1rem rgba(255,255,255,.07),
                inset -.6rem 0 1.1rem rgba(14,50,120,.09),
                0 1.15rem 2.4rem color-mix(in srgb, var(--wb-blue) 18%, transparent);
        }}

        .wb-bottle__shine {{
            position: absolute;
            z-index: 4;
            top: 1.3rem;
            bottom: 2.1rem;
            left: .8rem;
            width: .34rem;
            border-radius: 99px;
            background: linear-gradient(180deg, rgba(255,255,255,.65), rgba(255,255,255,.04));
            opacity: .62;
        }}

        .wb-bottle__liquid {{
            position: absolute;
            z-index: 1;
            right: 0;
            bottom: 0;
            left: 0;
            height: var(--wb-level);
            background: linear-gradient(180deg, #24D9F0, #1E91F0 48%, #274DDB);
            box-shadow: inset 0 1rem 1.7rem rgba(255,255,255,.12), 0 -10px 30px rgba(34,211,238,.2);
            transition: height 700ms cubic-bezier(.2,.8,.2,1);
        }}

        .wb-bottle__liquid::before,
        .wb-bottle__liquid::after {{
            content: "";
            position: absolute;
            left: -18%;
            top: -.42rem;
            width: 140%;
            height: 1.15rem;
            border-radius: 45%;
            background: #53E5F4;
            animation: wb-wave-liquid 4s ease-in-out infinite;
        }}

        .wb-bottle__liquid::after {{
            top: -.2rem;
            background: rgba(255,255,255,.2);
            animation-delay: -2s;
            animation-direction: reverse;
        }}

        .wb-bottle__mark {{
            position: absolute;
            z-index: 3;
            right: .55rem;
            width: .78rem;
            height: 1px;
            background: color-mix(in srgb, var(--wb-ink) 27%, transparent);
        }}

        .wb-bottle__mark--25 {{ bottom: 25%; }}
        .wb-bottle__mark--50 {{ bottom: 50%; }}
        .wb-bottle__mark--75 {{ bottom: 75%; }}

        .wb-bottle__copy {{
            min-width: 0;
            padding-left: clamp(.4rem, 2vw, 1.1rem);
        }}

        .wb-bottle__eyebrow {{
            margin: 0 0 .45rem;
            color: color-mix(in srgb, var(--wb-cyan) 72%, var(--wb-ink));
            font-size: .69rem;
            font-weight: 850;
            letter-spacing: .13em;
            text-transform: uppercase;
        }}

        .wb-bottle__value {{
            margin: 0;
            font-size: clamp(2.25rem, 5vw, 3.6rem);
            font-weight: 900;
            letter-spacing: -.065em;
            line-height: .95;
        }}

        .wb-bottle__value span {{
            display: block;
            margin-top: .65rem;
            color: var(--wb-muted);
            font-size: .82rem;
            font-weight: 650;
            letter-spacing: 0;
        }}

        .wb-bottle__percent {{
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            margin-top: 1.25rem;
            padding: .5rem .68rem;
            border: 1px solid color-mix(in srgb, var(--wb-cyan) 28%, var(--wb-line));
            border-radius: .8rem;
            background: color-mix(in srgb, var(--wb-cyan) 9%, var(--wb-surface));
            color: var(--wb-muted);
            font-size: .76rem;
            font-weight: 730;
        }}

        .wb-bottle__percent strong {{ color: var(--wb-ink); }}

        .wb-bottle__goal-seal {{
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            margin-top: .8rem;
            padding: .48rem .7rem;
            border: 1px solid color-mix(in srgb, var(--wb-aqua) 42%, var(--wb-line));
            border-radius: 999px;
            background: color-mix(in srgb, var(--wb-aqua) 12%, var(--wb-surface));
            color: var(--wb-ink);
            font-size: .72rem;
            font-weight: 820;
        }}

        .wb-bottle-card--complete {{
            border-color: color-mix(in srgb, var(--wb-aqua) 55%, var(--wb-line));
            box-shadow: var(--wb-shadow), 0 0 2.8rem color-mix(in srgb, var(--wb-aqua) 15%, transparent);
        }}

        .wb-bottle-card--complete .wb-bottle__liquid {{
            height: 100% !important;
            transition: none;
        }}

        .wb-bottle-card--complete .wb-bottle__shell {{
            animation: wb-bottle-complete-pulse 2.8s ease-in-out infinite;
        }}

        /* ---------- Achievement badge ---------- */
        .wb-badge-card {{
            --wb-badge-accent: #2DD4BF;
            position: relative;
            min-height: 10.5rem;
            padding: 1.35rem;
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--wb-badge-accent) 25%, var(--wb-line));
            border-radius: 1.55rem;
            background:
                radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--wb-badge-accent) 16%, transparent), transparent 9rem),
                color-mix(in srgb, var(--wb-surface) 82%, transparent);
            box-shadow: 0 16px 42px color-mix(in srgb, #020617 10%, transparent);
            transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
        }}

        .wb-badge-card:hover {{
            transform: translateY(-3px);
            border-color: color-mix(in srgb, var(--wb-badge-accent) 52%, var(--wb-line));
            box-shadow: 0 22px 52px color-mix(in srgb, var(--wb-badge-accent) 14%, transparent);
        }}

        .wb-badge-card__top {{
            display: flex;
            align-items: flex-start;
            justify-content: flex-end;
            gap: 1rem;
        }}

        .wb-badge-card__state {{
            display: inline-flex;
            align-items: center;
            gap: .34rem;
            padding: .38rem .55rem;
            border: 1px solid var(--wb-line);
            border-radius: 99px;
            color: var(--wb-muted);
            font-size: .75rem;
            font-weight: 840;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}

        .wb-badge-card__title {{
            margin: 1.05rem 0 .38rem;
            font-size: 1.05rem;
            font-weight: 830;
            letter-spacing: -.025em;
        }}

        .wb-badge-card__description {{
            margin: 0;
            color: var(--wb-muted);
            font-size: .8rem;
            line-height: 1.55;
            text-wrap: pretty;
        }}

        .wb-badge-card--locked {{
            border-color: var(--wb-line);
            background: color-mix(in srgb, var(--wb-surface) 66%, transparent);
        }}

        .wb-badge-card--locked .wb-badge-card__title,
        .wb-badge-card--locked .wb-badge-card__description {{ color: var(--wb-muted); }}

        /* ---------- Empty state ---------- */
        .wb-empty-state {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 17rem;
            padding: 2.2rem 1.5rem;
            border: 1px dashed color-mix(in srgb, var(--wb-route-primary) 28%, var(--wb-line));
            border-radius: 1.7rem;
            background:
                radial-gradient(circle at 50% 45%, color-mix(in srgb, var(--wb-cyan) 8%, transparent), transparent 10rem),
                color-mix(in srgb, var(--wb-surface) 56%, transparent);
            text-align: center;
        }}

        .wb-empty-state__icon {{
            flex: 0 0 auto;
            display: grid;
            place-items: center;
            width: 4rem;
            height: 4rem;
            margin-bottom: 1rem;
            border: 1px solid color-mix(in srgb, var(--wb-cyan) 31%, var(--wb-line));
            border-radius: 1.35rem;
            background: color-mix(in srgb, var(--wb-cyan) 10%, var(--wb-surface));
            color: var(--wb-cyan);
            font-size: 2rem;
            box-shadow: 0 14px 36px color-mix(in srgb, var(--wb-cyan) 12%, transparent);
            animation: wb-icon-float 3.4s ease-in-out infinite;
            overflow: hidden;
        }}

        .wb-empty-state__title {{
            margin: 0;
            font-size: 1.18rem;
            font-weight: 820;
            letter-spacing: -.025em;
        }}

        .wb-empty-state__description {{
            max-width: 42ch;
            margin: .48rem 0 0;
            color: var(--wb-muted);
            font-size: .86rem;
            line-height: 1.58;
            text-wrap: pretty;
        }}

        /* ---------- Celebration confetti ---------- */
        .wb-confetti {{
            position: fixed;
            z-index: 99999;
            inset: 0;
            overflow: hidden;
            pointer-events: none;
        }}

        .wb-confetti__piece {{
            position: absolute;
            top: -8vh;
            left: 50%;
            width: .55rem;
            height: .9rem;
            border-radius: .16rem;
            background: var(--wb-cyan);
            opacity: 0;
            animation: wb-confetti-fall 2.85s cubic-bezier(.16,.7,.32,1) forwards;
        }}

        .wb-confetti__piece:nth-child(3n) {{ width: .72rem; height: .72rem; border-radius: 50%; background: var(--wb-aqua); }}
        .wb-confetti__piece:nth-child(4n) {{ background: #8B5CF6; }}
        .wb-confetti__piece:nth-child(5n) {{ background: #FBBF24; }}
        .wb-confetti__piece:nth-child(6n) {{ background: #FB7185; }}
        .wb-confetti__piece:nth-child(1) {{ --wb-x: -45vw; --wb-r: 520deg; animation-delay: 0s; }}
        .wb-confetti__piece:nth-child(2) {{ --wb-x: -38vw; --wb-r: -610deg; animation-delay: .08s; }}
        .wb-confetti__piece:nth-child(3) {{ --wb-x: -31vw; --wb-r: 430deg; animation-delay: .18s; }}
        .wb-confetti__piece:nth-child(4) {{ --wb-x: -24vw; --wb-r: -540deg; animation-delay: .04s; }}
        .wb-confetti__piece:nth-child(5) {{ --wb-x: -17vw; --wb-r: 690deg; animation-delay: .24s; }}
        .wb-confetti__piece:nth-child(6) {{ --wb-x: -10vw; --wb-r: -460deg; animation-delay: .12s; }}
        .wb-confetti__piece:nth-child(7) {{ --wb-x: -4vw; --wb-r: 570deg; animation-delay: .29s; }}
        .wb-confetti__piece:nth-child(8) {{ --wb-x: 3vw; --wb-r: -650deg; animation-delay: .02s; }}
        .wb-confetti__piece:nth-child(9) {{ --wb-x: 9vw; --wb-r: 500deg; animation-delay: .2s; }}
        .wb-confetti__piece:nth-child(10) {{ --wb-x: 15vw; --wb-r: -390deg; animation-delay: .09s; }}
        .wb-confetti__piece:nth-child(11) {{ --wb-x: 21vw; --wb-r: 630deg; animation-delay: .32s; }}
        .wb-confetti__piece:nth-child(12) {{ --wb-x: 27vw; --wb-r: -580deg; animation-delay: .15s; }}
        .wb-confetti__piece:nth-child(13) {{ --wb-x: 33vw; --wb-r: 450deg; animation-delay: .05s; }}
        .wb-confetti__piece:nth-child(14) {{ --wb-x: 39vw; --wb-r: -700deg; animation-delay: .26s; }}
        .wb-confetti__piece:nth-child(15) {{ --wb-x: 45vw; --wb-r: 560deg; animation-delay: .11s; }}
        .wb-confetti__piece:nth-child(16) {{ --wb-x: -34vw; --wb-r: -480deg; animation-delay: .38s; }}
        .wb-confetti__piece:nth-child(17) {{ --wb-x: -19vw; --wb-r: 720deg; animation-delay: .34s; }}
        .wb-confetti__piece:nth-child(18) {{ --wb-x: -1vw; --wb-r: -530deg; animation-delay: .42s; }}
        .wb-confetti__piece:nth-child(19) {{ --wb-x: 18vw; --wb-r: 620deg; animation-delay: .36s; }}
        .wb-confetti__piece:nth-child(20) {{ --wb-x: 36vw; --wb-r: -670deg; animation-delay: .4s; }}

        /* ---------- Motion ---------- */
        @keyframes wb-aurora-drift {{
            0% {{ transform: translate3d(-2%, -1%, 0) rotate(-2deg) scale(1); opacity: .48; }}
            45% {{ transform: translate3d(4%, 3%, 0) rotate(2deg) scale(1.08); opacity: .66; }}
            100% {{ transform: translate3d(-1%, 5%, 0) rotate(-1deg) scale(1.03); opacity: .54; }}
        }}
        @keyframes wb-background-bubbles {{
            0% {{ transform: translate3d(0, 2.5rem, 0); background-position: 7% 15%, 58% 62%, 88% 28%; }}
            50% {{ transform: translate3d(1.2rem, -1.5rem, 0); background-position: 10% 3%, 55% 46%, 91% 13%; }}
            100% {{ transform: translate3d(0, -5.5rem, 0); background-position: 7% -9%, 58% 30%, 88% -2%; }}
        }}
        @keyframes wb-ambience-welcome-rain {{
            0% {{ transform: translate3d(-1.8rem, -11rem, 0); }}
            100% {{ transform: translate3d(1.8rem, 11rem, 0); }}
        }}
        @keyframes wb-ambience-welcome-ripples {{
            0% {{ transform: scale(.86); opacity: .06; }}
            42% {{ opacity: .24; }}
            100% {{ transform: scale(1.13); opacity: .04; }}
        }}
        @keyframes wb-ambience-home-current {{
            0% {{ transform: translate3d(-2.5%, -1%, 0) rotate(-1.5deg) scale(1); }}
            100% {{ transform: translate3d(3.5%, 2.5%, 0) rotate(1.5deg) scale(1.06); }}
        }}
        @keyframes wb-ambience-home-tide {{
            0%, 100% {{ transform: translate3d(-1.5%, 1.2rem, 0) scaleX(.98); opacity: .18; }}
            50% {{ transform: translate3d(1.5%, -1rem, 0) scaleX(1.035); opacity: .3; }}
        }}
        @keyframes wb-ambience-log-bubbles {{
            0% {{ transform: translate3d(0, 11rem, 0); }}
            100% {{ transform: translate3d(1.4rem, -13rem, 0); }}
        }}
        @keyframes wb-ambience-log-stream {{
            0% {{ transform: translate3d(-.8rem, 8rem, 0); opacity: .12; }}
            50% {{ transform: translate3d(.8rem, -3rem, 0); opacity: .22; }}
            100% {{ transform: translate3d(-.8rem, -14rem, 0); opacity: .1; }}
        }}
        @keyframes wb-ambience-pet-orbit {{
            to {{ transform: rotate(360deg); }}
        }}
        @keyframes wb-ambience-pet-sparkles {{
            0%, 100% {{ transform: translate3d(0, .6rem, 0); opacity: .17; }}
            35% {{ transform: translate3d(.4rem, -.3rem, 0); opacity: .34; }}
            68% {{ transform: translate3d(-.35rem, -.7rem, 0); opacity: .23; }}
        }}
        @keyframes wb-ambience-insights-grid {{
            0% {{ transform: perspective(48rem) rotateX(58deg) translate3d(0, 0, 0); }}
            100% {{ transform: perspective(48rem) rotateX(58deg) translate3d(0, 4rem, 0); }}
        }}
        @keyframes wb-ambience-insights-pulse {{
            0% {{ background-position: -70vw 0, center, center; opacity: .08; }}
            42% {{ opacity: .24; }}
            100% {{ background-position: 138vw 0, center, center; opacity: .08; }}
        }}
        @keyframes wb-ambience-achievements-stars {{
            0% {{ transform: translate3d(-1.2rem, .6rem, 0) scale(1); opacity: .21; }}
            100% {{ transform: translate3d(1.5rem, -1.1rem, 0) scale(1.025); opacity: .31; }}
        }}
        @keyframes wb-ambience-achievements-glint {{
            0%, 72%, 100% {{ transform: translate3d(-1rem, .5rem, 0); opacity: .08; }}
            80% {{ transform: translate3d(.4rem, -.25rem, 0); opacity: .28; }}
            88% {{ transform: translate3d(1rem, -.55rem, 0); opacity: .12; }}
        }}
        @keyframes wb-ambience-reminders-clock {{
            to {{ transform: rotate(360deg); }}
        }}
        @keyframes wb-ambience-reminders-ripple {{
            0% {{ transform: scale(.82); opacity: .04; }}
            38% {{ opacity: .22; }}
            100% {{ transform: scale(1.12); opacity: .03; }}
        }}
        @keyframes wb-ambience-coach-currents {{
            0% {{ transform: translate3d(-2.2rem, -.5rem, 0) skewY(-1deg); }}
            100% {{ transform: translate3d(2.2rem, .8rem, 0) skewY(1deg); }}
        }}
        @keyframes wb-ambience-coach-nodes {{
            0%, 100% {{ transform: scale(.985); opacity: .16; }}
            45% {{ transform: scale(1.015); opacity: .3; }}
            68% {{ transform: scale(1); opacity: .21; }}
        }}
        @keyframes wb-ambience-profile-aurora {{
            0% {{ transform: translate3d(-3%, -1%, 0) rotate(-2deg) scale(1); opacity: .4; }}
            100% {{ transform: translate3d(4%, 3%, 0) rotate(2deg) scale(1.08); opacity: .54; }}
        }}
        @keyframes wb-ambience-profile-ribbons {{
            0% {{ transform: translate3d(-2.5%, 1%, 0) skewX(-2deg); opacity: .08; }}
            100% {{ transform: translate3d(3%, -1.5%, 0) skewX(2deg); opacity: .16; }}
        }}
        @keyframes wb-halo-pulse {{
            0%, 100% {{ transform: scale(.96); opacity: .68; }}
            50% {{ transform: scale(1.04); opacity: 1; }}
        }}
        @keyframes wb-orbit {{ to {{ transform: rotate(360deg); }} }}
        @keyframes wb-float {{
            0%, 100% {{ transform: translateY(.15rem) rotate(-1deg); }}
            50% {{ transform: translateY(-.65rem) rotate(1deg); }}
        }}
        @keyframes wb-shadow-breathe {{
            0%, 100% {{ transform: scale(.88); opacity: .38; }}
            50% {{ transform: scale(1.05); opacity: .22; }}
        }}
        @keyframes wb-blink {{
            0%, 43%, 47%, 100% {{ transform: scaleY(1); }}
            45% {{ transform: scaleY(.08); }}
        }}
        @keyframes wb-bubble-rise {{
            0% {{ transform: translateY(0) scale(.72); opacity: 0; }}
            18% {{ opacity: .72; }}
            82% {{ opacity: .44; }}
            100% {{ transform: translateY(-14rem) translateX(1rem) scale(1.14); opacity: 0; }}
        }}
        @keyframes wb-thirsty {{
            0%, 100% {{ transform: translateY(.35rem) scaleY(.94) rotate(-2deg); }}
            50% {{ transform: translateY(.05rem) scaleY(.97) rotate(2deg); }}
        }}
        @keyframes wb-waking {{
            0%, 100% {{ transform: translateY(.15rem) rotate(-1.5deg); }}
            50% {{ transform: translateY(-.4rem) rotate(1.5deg); }}
        }}
        @keyframes wb-small-wave {{
            0%, 100% {{ transform: rotate(-17deg); }}
            50% {{ transform: rotate(-42deg); }}
        }}
        @keyframes wb-wave {{
            0%, 100% {{ transform: rotate(-18deg); }}
            50% {{ transform: rotate(-67deg); }}
        }}
        @keyframes wb-wave-left {{
            0%, 100% {{ transform: rotate(18deg); }}
            50% {{ transform: rotate(67deg); }}
        }}
        @keyframes wb-happy-bounce {{
            0%, 100% {{ transform: translateY(.15rem) scale(1); }}
            45% {{ transform: translateY(-.75rem) scale(1.025,.98); }}
            68% {{ transform: translateY(-.4rem) scale(.985,1.015); }}
        }}
        @keyframes wb-celebrate {{
            0%, 100% {{ transform: translateY(.1rem) rotate(-3deg) scale(1); }}
            25% {{ transform: translateY(-.72rem) rotate(2deg) scale(1.025); }}
            55% {{ transform: translateY(-.2rem) rotate(-2deg) scale(.985,1.02); }}
            76% {{ transform: translateY(-.64rem) rotate(3deg) scale(1.015); }}
        }}
        @keyframes wb-pet-idle {{
            0%, 100% {{ translate: 0 .15rem; rotate: -1.2deg; }}
            50% {{ translate: 0 -.55rem; rotate: 1.2deg; }}
        }}
        @keyframes wb-pet-boop {{
            0%, 100% {{ translate: 0 .1rem; rotate: 0; scale: 1; }}
            24% {{ translate: 0 -.75rem; rotate: -5deg; scale: 1.04 .96; }}
            48% {{ translate: 0 -.2rem; rotate: 5deg; scale: .97 1.04; }}
            72% {{ translate: 0 -.6rem; rotate: -2deg; scale: 1.02 .98; }}
        }}
        @keyframes wb-pet-blink {{
            0%, 42%, 46%, 76%, 80%, 100% {{ transform: scaleY(1); }}
            44%, 78% {{ transform: scaleY(.07); }}
        }}
        @keyframes wb-pet-aura {{
            0%, 100% {{ transform: scale(.94) rotate(0); opacity: .55; }}
            50% {{ transform: scale(1.04) rotate(4deg); opacity: .95; }}
        }}
        @keyframes wb-pet-bubble {{
            0% {{ translate: 0 0; scale: .65; opacity: 0; }}
            17% {{ opacity: .7; }}
            82% {{ opacity: .42; }}
            100% {{ translate: 1rem -24rem; scale: 1.2; opacity: 0; }}
        }}
        @keyframes wb-pet-speech {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-.25rem); }}
        }}
        @keyframes wb-pet-tired {{
            0%, 100% {{ translate: 0 .45rem; rotate: -2deg; scale: 1 .95; }}
            50% {{ translate: 0 .12rem; rotate: 2deg; scale: 1 .97; }}
        }}
        @keyframes wb-pet-sleepy {{
            0%, 100% {{ translate: 0 .28rem; rotate: -1deg; }}
            50% {{ translate: 0 -.16rem; rotate: 1deg; }}
        }}
        @keyframes wb-pet-excited {{
            0%, 100% {{ translate: 0 .12rem; rotate: -2deg; scale: 1; }}
            40% {{ translate: 0 -.9rem; rotate: 2deg; scale: 1.025 .98; }}
            68% {{ translate: 0 -.28rem; rotate: -1deg; scale: .985 1.02; }}
        }}
        @keyframes wb-pet-curious {{
            0%, 100% {{ translate: -.1rem .1rem; rotate: -3deg; }}
            50% {{ translate: .18rem -.4rem; rotate: 4deg; }}
        }}
        @keyframes wb-pet-fin-left {{
            0%, 100% {{ transform: rotate(-24deg); }}
            50% {{ transform: rotate(-52deg); }}
        }}
        @keyframes wb-pet-fin-right {{
            0%, 100% {{ transform: rotate(24deg); }}
            50% {{ transform: rotate(52deg); }}
        }}
        @keyframes wb-pet-star {{
            0%, 100% {{ transform: translateX(-50%) rotate(-8deg) scale(.94); }}
            50% {{ transform: translateX(-50%) rotate(8deg) scale(1.08); }}
        }}
        @keyframes wb-bottle-complete-pulse {{
            0%, 100% {{ filter: saturate(1); transform: translateY(0); }}
            50% {{ filter: saturate(1.16) brightness(1.05); transform: translateY(-.18rem); }}
        }}
        @keyframes wb-samurai-glint {{
            0%, 64%, 100% {{ filter: brightness(1); opacity: .82; }}
            72% {{ filter: brightness(1.45) drop-shadow(0 0 .35rem rgba(251,191,36,.65)); opacity: 1; }}
        }}
        @keyframes wb-cyborg-scan {{
            0%, 12% {{ transform: translateX(0); opacity: 0; }}
            32% {{ opacity: .92; }}
            72% {{ opacity: .72; }}
            88%, 100% {{ transform: translateX(490%); opacity: 0; }}
        }}
        @keyframes wb-cyborg-core {{
            0%, 100% {{ scale: .94; filter: brightness(.9); }}
            50% {{ scale: 1.06; filter: brightness(1.24); }}
        }}
        @keyframes wb-cool-lens {{
            0%, 62%, 100% {{ opacity: .38; transform: translateX(-.2rem) rotate(-9deg); }}
            72% {{ opacity: .92; transform: translateX(.32rem) rotate(-9deg); }}
        }}
        @keyframes wb-wave-liquid {{
            0%, 100% {{ transform: translateX(-3%) rotate(-1deg); }}
            50% {{ transform: translateX(3%) rotate(1deg); }}
        }}
        @keyframes wb-icon-float {{
            0%, 100% {{ transform: translateY(0) rotate(-2deg); }}
            50% {{ transform: translateY(-.35rem) rotate(2deg); }}
        }}
        @keyframes wb-confetti-fall {{
            0% {{ transform: translate3d(0, -4vh, 0) rotate(0); opacity: 0; }}
            8% {{ opacity: 1; }}
            100% {{ transform: translate3d(var(--wb-x), 112vh, 0) rotate(var(--wb-r)); opacity: .95; }}
        }}

        /* Component-width breakpoints also work inside narrow desktop columns. */
        @container (max-width: 44rem) {{
            .wb-pet:not(.wb-pet--compact) {{
                grid-template-columns: minmax(0, 1fr);
            }}
            .wb-pet:not(.wb-pet--compact) .wb-pet__room {{ min-height: 27rem; }}
            .wb-pet:not(.wb-pet--compact) .wb-pet__panel {{
                border-top: 1px solid var(--wb-soft-line);
                border-left: 0;
            }}
        }}

        @container (max-width: 36rem) {{
            .wb-page-intro {{
                align-items: flex-start;
                flex-direction: column;
            }}
            .wb-page-intro__title {{ font-size: clamp(1.85rem, 10cqi, 3rem); }}
            .wb-page-intro__badge {{ margin-top: 0; }}

            .wb-mascot:not(.wb-mascot--compact) {{
                grid-template-columns: minmax(0, 1fr);
            }}
            .wb-mascot:not(.wb-mascot--compact) .wb-mascot__scene {{
                min-height: 19rem;
            }}
            .wb-mascot:not(.wb-mascot--compact) .wb-mascot__copy {{
                align-items: center;
                padding: 0 1.4rem 1.7rem;
                text-align: center;
            }}
            .wb-mascot:not(.wb-mascot--compact) .wb-mascot__message {{
                max-width: 38ch;
            }}
            .wb-mascot:not(.wb-mascot--compact) .wb-mascot__meter-label,
            .wb-mascot:not(.wb-mascot--compact) .wb-mascot__meter {{
                align-self: stretch;
            }}

            .wb-pet__name,
            .wb-mascot__name,
            .wb-bottle__value {{
                font-size: clamp(1.8rem, 10cqi, 3rem);
            }}

            .wb-bottle-card {{
                grid-template-columns: minmax(0, 1fr);
                text-align: center;
            }}
            .wb-bottle__copy {{ padding: .5rem 0 0; }}
            .wb-bottle__percent {{ justify-content: center; }}
        }}

        @container (max-width: 24rem) {{
            .wb-page-intro {{
                gap: 1rem;
                padding: 1.15rem;
            }}
            .wb-page-intro__badge {{
                width: 100%;
                justify-content: flex-start;
            }}
            .wb-mascot--compact {{
                grid-template-columns: minmax(5rem, 6.5rem) minmax(0, 1fr);
            }}
            .wb-mascot--compact .wb-mascot__scene {{ transform: scale(.5); }}
            .wb-mascot--compact .wb-mascot__copy {{
                padding-right: .8rem;
            }}
            .wb-pet__speech {{
                left: 1rem;
                max-width: calc(100% - 2rem);
            }}
            .wb-pet--compact .wb-pet__panel {{
                grid-template-columns: minmax(0, 1fr);
            }}
            .wb-pet--compact .wb-pet__panel::after {{ text-align: left; }}
            .wb-badge-card__top {{ align-items: flex-start; }}
            .wb-bottle__percent {{ width: 100%; }}
        }}

        @media (max-width: 760px) {{
            .stApp::before, .stApp::after {{ display: none; }}
            [data-testid="stMainBlockContainer"] {{ padding-inline: 1rem; }}
            .wb-page-intro {{ align-items: flex-start; flex-direction: column; }}
            .wb-page-intro__badge {{ margin-top: 0; }}
            .wb-mascot {{ grid-template-columns: 1fr; }}
            .wb-mascot__scene {{ min-height: 19rem; }}
            .wb-mascot__copy {{ padding: 0 1.4rem 1.7rem; text-align: center; align-items: center; }}
            .wb-mascot__message {{ max-width: 38ch; }}
            .wb-mascot__meter-label, .wb-mascot__meter {{ align-self: stretch; }}
            .wb-mascot--compact {{ grid-template-columns: 7rem 1fr; min-height: 10rem; }}
            .wb-mascot--compact .wb-mascot__scene {{ min-height: 10rem; }}
            .wb-mascot--compact .wb-mascot__copy {{ align-items: flex-start; padding: 1rem 1rem 1rem .1rem; text-align: left; }}
            .wb-pet {{ grid-template-columns: 1fr; }}
            .wb-pet__room {{ min-height: 27rem; }}
            .wb-pet__panel {{ border-top: 1px solid var(--wb-soft-line); border-left: 0; }}
            .wb-pet__speech {{ max-width: 60%; }}
            .wb-pet--compact .wb-pet__room {{ min-height: 14rem; }}
            .wb-pet--compact .wb-pet__panel {{ border: 1px solid var(--wb-line); }}
            .wb-bottle-card {{ grid-template-columns: 1fr; text-align: center; }}
            .wb-bottle__copy {{ padding: .5rem 0 0; }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            .stApp::before,
            .stApp::after,
            .stApp *,
            [data-baseweb="popover"] *,
            [data-testid="stPopoverBody"] *,
            .wb-mascot *,
            .wb-pet *,
            .wb-bottle-card *,
            .wb-empty-state *,
            .wb-confetti * {{
                animation: none !important;
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }}
            .stApp::before,
            .stApp::after {{
                will-change: auto !important;
            }}
            .wb-confetti {{ display: none; }}
        }}
        {motion_override}
        </style>
        """,
        width="stretch",
    )


def render_brand(compact: bool = False) -> None:
    """Render the Water Buddy brand lockup."""

    compact_class = " wb-brand--compact" if compact else ""
    st.html(
        f"""
        <div class="wb-brand{compact_class}" aria-label="Water Buddy, mindful hydration">
            <span class="wb-brand__mark" aria-hidden="true"></span>
            <span class="wb-brand__copy">
                <span class="wb-brand__name">Water Buddy</span>
                <span class="wb-brand__tagline">Mindful hydration</span>
            </span>
        </div>
        """,
        width="content",
    )


def page_intro(
    eyebrow: str,
    title: str,
    description: str,
    action_badge: str | None = None,
) -> None:
    """Render a responsive, high-emphasis page introduction."""

    safe_eyebrow = _escape(eyebrow)
    safe_title = _escape(title)
    safe_description = _escape(description)
    badge = ""
    if action_badge:
        badge = f'<span class="wb-page-intro__badge">{_escape(action_badge)}</span>'

    st.html(
        f"""
        <section class="wb-page-intro" aria-labelledby="wb-page-title">
            <div class="wb-page-intro__copy">
                <p class="wb-eyebrow">{safe_eyebrow}</p>
                <h1 class="wb-page-intro__title" id="wb-page-title">{safe_title}</h1>
                <p class="wb-page-intro__description">{safe_description}</p>
            </div>
            {badge}
        </section>
        """
    )


def render_mascot(
    progress: float,
    name: str = "FLOW",
    message: str | None = None,
    compact: bool = False,
) -> None:
    """Render FLOW, an original CSS droplet whose mood follows progress.

    ``progress`` can be a ratio or percentage. The five reactions are thirsty
    (0–24%), waking (25–49%), flowing (50–74%), thriving (75–99%), and goal
    (100%).
    """

    percent = _percent(progress, ratio_hint=True)
    if percent < 25:
        state = "thirsty"
        status = "Needs a little water"
        default_message = "A few steady sips will get us flowing again."
    elif percent < 50:
        state = "waking"
        status = "Warming up"
        default_message = "Nice start — your hydration rhythm is waking up."
    elif percent < 75:
        state = "flowing"
        status = "In the flow"
        default_message = "You’re building a beautifully steady hydration day."
    elif percent < 100:
        state = "thriving"
        status = "Almost there"
        default_message = "So close! One more mindful refill could do it."
    else:
        state = "goal"
        status = "Daily goal complete"
        default_message = "Goal reached — your future self is cheering with me!"

    safe_name = _escape(name)
    safe_message = _escape(message if message is not None else default_message)
    safe_status = _escape(status)
    safe_percent = _escape(f"{percent:.0f}")
    compact_class = " wb-mascot--compact" if compact else ""

    st.html(
        f"""
        <section class="wb-mascot wb-state-{state}{compact_class}"
            aria-label="{safe_name}, hydration mascot. {safe_status}. {safe_percent} percent complete.">
            <div class="wb-mascot__scene" aria-hidden="true">
                <span class="wb-mascot__halo"></span>
                <span class="wb-mascot__orbit"></span>
                <span class="wb-bubble wb-bubble--one"></span>
                <span class="wb-bubble wb-bubble--two"></span>
                <span class="wb-bubble wb-bubble--three"></span>
                <span class="wb-bubble wb-bubble--four"></span>
                <div class="wb-drop-character">
                    <span class="wb-drop__tip"></span>
                    <span class="wb-arm wb-arm--left"></span>
                    <span class="wb-arm wb-arm--right"></span>
                    <div class="wb-drop__body">
                        <div class="wb-drop__face">
                            <span class="wb-eye wb-eye--left"></span>
                            <span class="wb-eye wb-eye--right"></span>
                            <span class="wb-cheek wb-cheek--left"></span>
                            <span class="wb-cheek wb-cheek--right"></span>
                            <span class="wb-mouth"></span>
                        </div>
                    </div>
                </div>
                <span class="wb-mascot__shadow"></span>
            </div>
            <div class="wb-mascot__copy">
                <span class="wb-mascot__status">
                    <span class="wb-mascot__status-dot" aria-hidden="true"></span>
                    {safe_status}
                </span>
                <h3 class="wb-mascot__name">{safe_name}</h3>
                <p class="wb-mascot__message">{safe_message}</p>
                <div class="wb-mascot__meter-label">
                    <span>Hydration energy</span>
                    <strong>{safe_percent}%</strong>
                </div>
                <div class="wb-mascot__meter" role="progressbar" aria-label="Hydration energy"
                    aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_percent}">
                    <div class="wb-mascot__meter-fill" style="--wb-progress: {percent:.2f}%"></div>
                </div>
            </div>
        </section>
        """
    )


def render_pet(
    pet: Mapping[str, object],
    hydration_progress: float,
    compact: bool = False,
) -> None:
    """Render the evolving hydration pet in its CSS-illustrated room.

    The renderer deliberately accepts a tolerant mapping contract so older
    locally persisted pet snapshots continue to display as the pet model
    evolves. Ratios and percentages are both supported for every meter.
    """

    pet_data: Mapping[str, object] = pet if isinstance(pet, Mapping) else {}

    def first_value(*keys: str, default: object = "") -> object:
        for key in keys:
            value = pet_data.get(key)
            if value not in (None, ""):
                return value
        return default

    def integer_value(*keys: str, default: int = 0, minimum: int = 0) -> int:
        raw = first_value(*keys, default=default)
        try:
            value = int(float(raw))
        except (TypeError, ValueError, OverflowError):
            value = default
        return max(minimum, value)

    name = str(first_value("name", "pet_name", default="Aqua"))
    level = integer_value("level", default=1, minimum=1)
    total_xp = integer_value("xp", "experience", default=0)
    xp = integer_value("xp_into_level", "level_xp", default=total_xp)
    xp_goal = integer_value(
        "xp_for_next_level",
        "xp_goal",
        "next_level_xp",
        default=max(100, xp + 1),
        minimum=1,
    )
    if "xp_for_next_level" not in pet_data and "xp_to_next_level" in pet_data:
        xp_goal = max(1, xp + integer_value("xp_to_next_level", default=0))
    raw_xp_progress = first_value("xp_progress", "level_progress", default=None)
    xp_percent = (
        _percent(raw_xp_progress, ratio_hint=True)
        if raw_xp_progress is not None
        else min(100.0, max(0.0, xp / xp_goal * 100.0))
    )
    energy = _percent(first_value("energy", "energy_percent", default=70))
    happiness = _percent(
        first_value("happiness", "happy", "happiness_percent", default=75)
    )
    hydration = _percent(hydration_progress, ratio_hint=True)

    raw_stage = first_value(
        "stage",
        "evolution_name",
        "evolution_stage",
        "form",
        default="Sprout",
    )
    if isinstance(raw_stage, Mapping):
        raw_stage = raw_stage.get("name", raw_stage.get("label", "Sprout"))
    stage_text = str(raw_stage).strip() or "Sprout"
    stage_index = integer_value("stage_index", "evolution", default=0)
    stage_token = stage_text.casefold()
    if stage_index >= 4 or any(
        word in stage_token
        for word in ("guardian", "legend", "myth", "aurora", "aqualume")
    ):
        stage_class, default_stage_label = "guardian", "Tide guardian"
    elif stage_index == 3 or any(
        word in stage_token for word in ("wave", "tide", "current", "crest")
    ):
        stage_class, default_stage_label = "wave", "Wave rider"
    elif stage_index == 2 or any(
        word in stage_token for word in ("ripple", "splash", "stream", "growing")
    ):
        stage_class, default_stage_label = "ripple", "Little ripple"
    else:
        stage_class, default_stage_label = "sprout", "Dew sprout"
    stage_label = str(
        first_value(
            "stage_label",
            "evolution_name",
            "evolution_label",
            default=default_stage_label,
        )
    )

    raw_mood = str(first_value("mood", "emotion", default="happy")).strip()
    mood_token = raw_mood.casefold()
    if hydration < 25 or any(word in mood_token for word in ("thirst", "low", "sad")):
        mood_class, mood_label = "thirsty", "Thirsty"
    elif any(word in mood_token for word in ("sleep", "tired", "rest")):
        mood_class, mood_label = "sleepy", "Sleepy"
    elif any(
        word in mood_token for word in ("excite", "radiant", "joy", "celebrat", "spark")
    ):
        mood_class, mood_label = "excited", "Radiant"
    elif any(word in mood_token for word in ("curious", "play", "alert")):
        mood_class, mood_label = "curious", "Curious"
    else:
        mood_class, mood_label = "happy", "Content"

    speech_value = first_value("speech", "message", "bubble", "status_message")
    if not speech_value:
        speech_value = {
            "thirsty": "Could we share a little water? Every sip helps me glow.",
            "sleepy": "A quiet rest now will refill my sparkle.",
            "excited": "We’re making waves together — look at that glow!",
            "curious": "What tiny hydration quest should we try next?",
            "happy": "I feel wonderful when your hydration rhythm stays steady.",
        }[mood_class]

    raw_accessory = str(
        first_value("equipped_accessory", "accessory", "wearing", default="none")
    ).strip()
    accessory_token = raw_accessory.casefold()
    normalized_accessory = (
        accessory_token.replace("-", "_").replace(" ", "_")
    )
    if normalized_accessory == "samurai_fit" or "samurai" in accessory_token:
        accessory_class = "samurai"
    elif normalized_accessory == "cyborg_fit" or "cyborg" in accessory_token:
        accessory_class = "cyborg"
    elif normalized_accessory == "cool_guy_fit" or "cool_guy" in normalized_accessory:
        accessory_class = "cool-guy"
    elif "crown" in accessory_token:
        accessory_class = "crown"
    elif any(word in accessory_token for word in ("glass", "goggle", "visor")):
        accessory_class = "glasses"
    elif any(word in accessory_token for word in ("leaf", "sprout")):
        accessory_class = "leaf"
    elif "bow" in accessory_token:
        accessory_class = "bow"
    elif "scarf" in accessory_token:
        accessory_class = "scarf"
    elif "star" in accessory_token:
        accessory_class = "star"
    else:
        accessory_class = "none"

    hydration_hint = (
        "Hydrate to lift your pet’s energy and unlock faster growth."
        if hydration < 50
        else "Your steady hydration is powering this room’s glow."
        if hydration < 100
        else "Goal complete — your pet is soaking up a full-power day."
    )

    safe_name = _escape(name)
    safe_level = _escape(level)
    is_max_level = bool(pet_data.get("is_max_level", False))
    safe_xp = _escape("MAX" if is_max_level else xp)
    safe_xp_goal = _escape("LEVEL" if is_max_level else xp_goal)
    safe_stage = _escape(stage_label)
    safe_mood = _escape(mood_label)
    safe_speech = _escape(speech_value)
    safe_hint = _escape(hydration_hint)
    safe_hydration = _escape(f"{hydration:.0f}")
    safe_energy = _escape(f"{energy:.0f}")
    safe_happiness = _escape(f"{happiness:.0f}")
    safe_xp_percent = _escape(f"{xp_percent:.0f}")
    hydration_css = _escape(f"{hydration:.2f}%")
    energy_css = _escape(f"{energy:.2f}%")
    happiness_css = _escape(f"{happiness:.2f}%")
    xp_css = _escape(f"{xp_percent:.2f}%")
    compact_class = " wb-pet--compact" if compact else ""
    compact_meta = _escape(f"Level {level} · {mood_label}")

    st.html(
        f"""
        <section class="wb-pet wb-pet-stage-{stage_class} wb-pet-mood-{mood_class}
            wb-accessory-{accessory_class}{compact_class}"
            aria-label="{safe_name}, level {safe_level} {safe_stage} hydration pet, feeling {safe_mood}">
            <div class="wb-pet__room">
                <span class="wb-pet__window" aria-hidden="true"></span>
                <span class="wb-pet__shelf" aria-hidden="true"></span>
                <span class="wb-pet__rug" aria-hidden="true"></span>
                <span class="wb-pet__bubble wb-pet__bubble--one" aria-hidden="true"></span>
                <span class="wb-pet__bubble wb-pet__bubble--two" aria-hidden="true"></span>
                <span class="wb-pet__bubble wb-pet__bubble--three" aria-hidden="true"></span>
                <span class="wb-pet__speech wb-pet__speech--default">{safe_speech}</span>
                <span class="wb-pet__speech wb-pet__speech--tap">Boop! You found my happy dance.</span>
                <div class="wb-pet__character-wrap">
                    <span class="wb-pet__aura"></span>
                    <button class="wb-pet__tap-target" type="button"
                        aria-label="Pet {safe_name} for a happy reaction">
                    <div class="wb-pet__character" aria-hidden="true">
                        <span class="wb-pet__crest"></span>
                        <span class="wb-pet__tip"></span>
                        <div class="wb-pet__body">
                            <span class="wb-pet__fin wb-pet__fin--left"></span>
                            <span class="wb-pet__fin wb-pet__fin--right"></span>
                            <span class="wb-pet__belly"></span>
                            <span class="wb-pet__eye wb-pet__eye--left"></span>
                            <span class="wb-pet__eye wb-pet__eye--right"></span>
                            <span class="wb-pet__cheek wb-pet__cheek--left"></span>
                            <span class="wb-pet__cheek wb-pet__cheek--right"></span>
                            <span class="wb-pet__mouth"></span>
                            <span class="wb-pet__accessory">
                                <span class="wb-pet__gear wb-pet__gear--head"></span>
                                <span class="wb-pet__gear wb-pet__gear--face"></span>
                                <span class="wb-pet__gear wb-pet__gear--body"></span>
                            </span>
                        </div>
                    </div>
                    </button>
                </div>
            </div>
            <aside class="wb-pet__panel" data-compact-meta="{compact_meta}">
                <div class="wb-pet__kicker">
                    <span class="wb-pet__stage">{safe_stage}</span>
                    <span class="wb-pet__mood">{safe_mood} mood</span>
                </div>
                <h3 class="wb-pet__name">{safe_name}</h3>
                <p class="wb-pet__level">Level {safe_level} hydration companion</p>
                <div class="wb-pet__stat">
                    <div class="wb-pet__stat-label"><span>Hydration bond</span><strong>{safe_hydration}%</strong></div>
                    <div class="wb-pet__track" role="progressbar" aria-label="Hydration bond"
                        aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_hydration}">
                        <div class="wb-pet__fill" style="--wb-pet-value: {hydration_css}"></div>
                    </div>
                </div>
                <div class="wb-pet__stat">
                    <div class="wb-pet__stat-label"><span>Energy</span><strong>{safe_energy}%</strong></div>
                    <div class="wb-pet__track" role="progressbar" aria-label="Pet energy"
                        aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_energy}">
                        <div class="wb-pet__fill wb-pet__fill--energy" style="--wb-pet-value: {energy_css}"></div>
                    </div>
                </div>
                <div class="wb-pet__stat">
                    <div class="wb-pet__stat-label"><span>Happiness</span><strong>{safe_happiness}%</strong></div>
                    <div class="wb-pet__track" role="progressbar" aria-label="Pet happiness"
                        aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_happiness}">
                        <div class="wb-pet__fill wb-pet__fill--happy" style="--wb-pet-value: {happiness_css}"></div>
                    </div>
                </div>
                <div class="wb-pet__stat">
                    <div class="wb-pet__stat-label"><span>Level XP</span><strong>{safe_xp} / {safe_xp_goal}</strong></div>
                    <div class="wb-pet__track" role="progressbar" aria-label="Pet level experience"
                        aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_xp_percent}">
                        <div class="wb-pet__fill wb-pet__fill--xp" style="--wb-pet-value: {xp_css}"></div>
                    </div>
                </div>
                <p class="wb-pet__hint">{safe_hint}</p>
            </aside>
        </section>
        """
    )


@st.fragment(run_every="1h")
def render_hourly_pet(
    pet: Mapping[str, object],
    hydration_progress: float,
    compact: bool = False,
) -> None:
    """Render a pet whose quote, tip, or fact advances once per hour."""

    hourly = hourly_pet_message()
    hourly_pet = dict(pet) if isinstance(pet, Mapping) else {}
    hourly_pet["speech"] = f"{hourly['kind']}: {hourly['text']}"
    render_pet(hourly_pet, hydration_progress, compact=compact)
    st.caption(
        f":material/schedule: Hourly {hourly['kind'].lower()} from "
        f"{hourly_pet.get('name', 'your buddy')} · changes every hour."
    )


def render_bottle(
    progress: float,
    intake_ml: int,
    goal_ml: int,
    units: object = "ml",
) -> None:
    """Render an animated bottle with current intake and goal details."""

    percent = _percent(progress, ratio_hint=True)
    try:
        intake = max(0, int(intake_ml))
    except (TypeError, ValueError):
        intake = 0
    try:
        goal = max(0, int(goal_ml))
    except (TypeError, ValueError):
        goal = 0

    remaining = max(0, goal - intake)
    is_complete = bool(goal and intake >= goal)
    safe_intake = _escape(format_volume(intake, units))
    safe_goal = _escape(format_volume(goal, units))
    safe_percent = _escape(f"{percent:.0f}")
    if goal and remaining:
        detail = f"{format_volume(remaining, units)} left to reach today’s goal"
    elif goal:
        detail = "Daily hydration goal complete"
    else:
        detail = "Set a daily goal to personalize this bottle"
    safe_detail = _escape(detail)
    completion_class = " wb-bottle-card--complete" if is_complete else ""
    completion_badge = (
        '<span class="wb-bottle__goal-seal" aria-label="Daily goal is saved as complete">'
        '&#10003; Goal locked in</span>'
        if is_complete
        else ""
    )

    st.html(
        f"""
        <section class="wb-bottle-card{completion_class}" aria-label="Daily water progress">
            <div class="wb-bottle__visual" aria-hidden="true">
                <span class="wb-bottle__cap"></span>
                <span class="wb-bottle__neck"></span>
                <div class="wb-bottle__shell">
                    <span class="wb-bottle__shine"></span>
                    <span class="wb-bottle__mark wb-bottle__mark--25"></span>
                    <span class="wb-bottle__mark wb-bottle__mark--50"></span>
                    <span class="wb-bottle__mark wb-bottle__mark--75"></span>
                    <span class="wb-bottle__liquid" style="--wb-level: {percent:.2f}%"></span>
                </div>
                {completion_badge}
            </div>
            <div class="wb-bottle__copy">
                <p class="wb-bottle__eyebrow">Today’s water</p>
                <h3 class="wb-bottle__value">
                    {safe_intake}
                    <span>of {safe_goal} daily goal</span>
                </h3>
                <div class="wb-bottle__percent" role="progressbar" aria-label="Daily water progress"
                    aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_percent}">
                    <strong>{safe_percent}%</strong> · {safe_detail}
                </div>
            </div>
        </section>
        """
    )


def render_badge_card(
    title: str,
    description: str,
    unlocked: bool,
    accent: str = "#2DD4BF",
) -> None:
    """Render a locked or unlocked achievement badge."""

    safe_title = _escape(title)
    safe_description = _escape(description)
    safe_accent = _safe_color(accent)
    modifier = "" if unlocked else " wb-badge-card--locked"
    state_icon = "verified" if unlocked else "lock"
    state_label = "Unlocked" if unlocked else "Locked"
    safe_state_icon = _escape(state_icon)
    safe_state_label = _escape(state_label)

    st.html(
        f"""
        <article class="wb-badge-card{modifier}" style="--wb-badge-accent: {safe_accent}"
            aria-label="{safe_title}, {safe_state_label}">
            <div class="wb-badge-card__top">
                <span class="wb-badge-card__state">
                    <span class="material-symbols-rounded" aria-hidden="true">{safe_state_icon}</span>
                    {safe_state_label}
                </span>
            </div>
            <h3 class="wb-badge-card__title">{safe_title}</h3>
            <p class="wb-badge-card__description">{safe_description}</p>
        </article>
        """
    )


def render_empty_state(
    title: str,
    description: str,
    icon: str = "water_drop",
) -> None:
    """Render a polished empty-state placeholder."""

    safe_title = _escape(title)
    safe_description = _escape(description)
    safe_icon = _escape(icon)
    st.html(
        f"""
        <section class="wb-empty-state" aria-label="{safe_title}">
            <span class="wb-empty-state__icon material-symbols-rounded" aria-hidden="true">{safe_icon}</span>
            <h3 class="wb-empty-state__title">{safe_title}</h3>
            <p class="wb-empty-state__description">{safe_description}</p>
        </section>
        """
    )


def celebration_confetti() -> None:
    """Render a short, pointer-safe CSS confetti celebration."""

    pieces = "".join('<span class="wb-confetti__piece"></span>' for _ in range(20))
    st.html(
        f'<div class="wb-confetti" aria-hidden="true">{pieces}</div>',
        width="stretch",
    )
