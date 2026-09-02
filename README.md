<div align="center">

# 💧 Water Buddy
streamlit app link: https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/

### A playful, private hydration companion that makes every sip count.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.60-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-120%20passing-22C55E)](#testing)
[![Local First](https://img.shields.io/badge/data-local--first-06B6D4)](#privacy-by-design)

**Track water. Build streaks. Raise FLOW. Feel better.**

</div>

Water Buddy turns general age and occupation guidance into a practical daily goal, then keeps hydration engaging with instant logging, progress insights, achievements, reminders, and a growing virtual companion. It runs locally with no API key and keeps account and hydration data on your device.

> FLOW uses a transparent offline coaching engine. The complete app works without an AI service or network connection.

## ✨ What makes it special

| | Experience |
|---|---|
| 🫊3 **Effortless tracking** | Customizable one-tap amounts, correction and deletion, undo, safe reset, and a 30-second Sip Guard against accidental duplicates |
| 🎯 **Personal goals** | Age- and occupation-aware guidance with custom adjustments and manual overrides |
| 💙 **FLOW hydration pet** | Moods, care actions, quests, evolution, 20 XP levels, and Samurai, Cyborg, and Cool Guy milestone outfits |
| 📊 **Useful insights** | Consistent 7/14/30-day trends, adherence, streaks, calendar-week challenges, and fair scoring for new users |
| 🏆 **Motivation** | Eight canonical achievement badges, daily tips, live pace feedback, and goal celebrations |
| 🔔 **Gentle reminders** | Configurable intervals, quiet hours, snooze/dismiss actions, and automatic rest after reaching the goal |
| 🎨 **Made for you** | Responsive layout, dark/light themes, animated page ambience, interface sounds, and metric or US fl oz display |
| 🛡️ **Resilient storage** | Atomic JSON writes, last-known-good backups, corruption recovery, validated imports, and local export |

## 🚀 Quick start

Water Buddy requires **Python 3.12 or newer**.

```powershell
git clone https://github.com/kavin-beep/WaterBuddy.app.git
cd WaterBuddy.app

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501), choose **Create account**, and start logging water. Later launches can use **Sign in**.

<details>
<summary><strong>macOS / Linux commands</strong></summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

</details>

## 🧭 App map

```text
Welcome → Home → Log Water → Insights → Achievements
                 ├─→ FLOW Pet
                 ├─→ Coach
                 ├─→ Reminders
                 └─→ Profile & Preferences
```

## 🏗️ Architecture

```text
streamlit_app.py                 App shell, authentication gate, navigation, reminders
app_pages/                       Streamlit page modules
water_buddy/auth.py              Account validation and salted password hashing
water_buddy/domain.py            Goals, water entries, streaks, badges, and reminders
water_buddy/pet.py               Pet progression, care, customization, and quests
water_buddy/storage.py           Thread-safe atomic JSON persistence and recovery
water_buddy/units.py             Canonical volume conversion and formatting
water_buddy/ui.py                Shared design system and animated pet rendering
water_buddy/audio.py             Dependency-free hydration feedback sounds
water_buddy/interaction_audio.py Browser-native interface feedback sounds
tests/                           Domain, storage, auth, UI, and page-level test suite
```

The `lib/` directory and `pubspec.yaml` are retained as references from the original Flutter prototype. The production app is the Streamlit implementation launched by `streamlit_app.py`.

## 🧪 Testing

```powershell
python -m unittest discover -s tests -v
```

The current suite contains **120 passing tests** covering authentication, per-user routing, logging and reward integrity, unit conversion, pet care, storage recovery, accessibility contracts, and every Streamlit page.

## 🔐 Privacy by design

- Account records live in `data/accounts.json`; hydration profiles live in `data/users/`. Both are ignored by Git.
- Passwords are stored as salted PBKDF2 hashes, never as plaintext.
- Profile writes are atomic and maintain a matching `.bak` safety copy.
- Damaged documents are preserved as recovery evidence before a valid backup or safe default is restored.
- Imported backups are schema-checked and previewed before confirmation.
- No API key, cloud account, analytics service, or external AI provider is required.

This local account model is intended for private use on your own machine. Use managed identity and database services before deploying Water Buddy as a public multi-user application.

## ℹ️ Good to know

- Reminders operate while the Water Buddy browser tab and local server are running.
- Sip Guard prevents duplicate entries for 30 seconds without changing intake, XP, achievements, sounds, or saved data.
- Water Buddy offers general wellness guidance, not medical advice. Personal needs can vary with health conditions, pregnancy, medications, weather, and clinician guidance.

---

<div align="center">

Made with 💧, Python, and Streamlit.

</div>
