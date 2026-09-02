<div align="center">

![Water Buddy animated header](https://capsule-render.vercel.app/api?type=waving&color=0:0EA5E9,45:2563EB,100:7C3AED&height=230&section=header&text=Water%20Buddy&fontSize=64&fontColor=FFFFFF&animation=fadeIn&fontAlignY=36&desc=Every%20sip%20counts&descSize=22&descAlignY=58)

[![Launch Water Buddy](https://img.shields.io/badge/Launch_Water_Buddy-Live_App-0EA5E9?style=for-the-badge&logo=streamlit&logoColor=white)](https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/)

[![Animated introduction](https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=22&duration=2800&pause=900&color=2563EB&center=true&vCenter=true&width=760&lines=Track+water.+Build+streaks.+Raise+FLOW.;A+playful%2C+private+hydration+companion.;No+API+key.+No+cloud+account.+Just+better+habits.)](https://git.io/typing-svg)

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit 1.60](https://img.shields.io/badge/Streamlit-1.60-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-130%20passing-22C55E?style=for-the-badge&logo=checkmarx&logoColor=white)](#testing)
[![Local first](https://img.shields.io/badge/data-local--first-06B6D4?style=for-the-badge&logo=shield&logoColor=white)](#privacy-by-design)

**Water Buddy turns hydration into a small daily adventure—with quick logging, useful insights, gentle reminders, achievements, and a virtual companion named FLOW.**

</div>

> [!NOTE]
> FLOW uses a transparent offline coaching engine. The complete app works without an AI service, API key, or network connection.

## ✨ Why Water Buddy?

| Experience | What you get |
|:--|:--|
| 🫗 **Effortless tracking** | Four customizable one-tap amounts, custom entries, editing, deletion, undo, and safe reset |
| 🎯 **Personal goals** | Age- and occupation-aware guidance, custom adjustments, and manual goal overrides |
| 💙 **FLOW hydration pet** | Moods, care actions, daily quests, hourly messages, 20 XP levels, evolution, and milestone outfits |
| 📊 **Useful insights** | 7/14/30-day trends, adherence, streaks, calendar-week challenges, and fair scoring for new users |
| 🏆 **Motivation** | Eight canonical achievement badges, daily tips, live pace feedback, and goal celebrations |
| 🔔 **Gentle reminders** | Configurable intervals, quiet hours, snooze/dismiss actions, and automatic rest after reaching your goal |
| 🎨 **Made for you** | Dark, Light, Japanese, and Cyber themes, responsive layouts, ambience, sounds, and metric or US fl oz display |
| 🛡️ **Resilient storage** | Atomic JSON writes, last-known-good backups, corruption recovery, validated imports, and local export |

## 🚀 Run locally

Water Buddy requires **Python 3.12 or newer**.

```powershell
git clone https://github.com/kavin-beep/WaterBuddy.app.git
cd WaterBuddy.app

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the streamlit link given above, choose **Create account**, and start logging water. Later launches can use **Sign in**.

<details>
<summary><strong>macOS / Linux commands</strong></summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

</details>

## ☁️ Deploy on Streamlit Community Cloud

The repository is deployment-ready: `streamlit_app.py`, `requirements.txt`, and `.streamlit/config.toml` are all in the expected locations.

1. Push this repository to GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Select **Create app**, then choose this repository and branch.
4. Set the main file path to `streamlit_app.py`.
5. Open **Advanced settings**, select a supported Python version (3.12+), and deploy.

No secrets are required. For public multi-user use, replace local JSON authentication/storage with managed identity and database services first.

## 🧭 App map

```text
Welcome → Home → Log Water → Insights → Achievements
                 ├── FLOW Pet
                 ├── Coach
                 ├── Reminders
                 └── Profile & Preferences
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

The suite contains **130 passing tests** covering authentication, per-user routing, logging and reward integrity, unit conversion, pet care, storage recovery, accessibility contracts, and every Streamlit page.

## 🔐 Privacy by design

- Account records live in `data/accounts.json`; hydration profiles live in `data/users/`. Both are ignored by Git.
- Passwords are stored as salted PBKDF2 hashes, never as plaintext.
- Profile writes are atomic and maintain a matching `.bak` safety copy.
- Damaged documents are preserved as recovery evidence before a valid backup or safe default is restored.
- Imported backups are schema-checked and previewed before confirmation.
- No API key, cloud account, analytics service, or external AI provider is required.

> [!IMPORTANT]
> This local account model is intended for private use on your own machine. Use managed identity and database services before deploying Water Buddy as a public multi-user application.

## ℹ️ Good to know

- Reminders operate while the Water Buddy browser tab and server are running.
- Sip Guard prevents duplicate entries for 30 seconds without changing intake, XP, achievements, sounds, or saved data.
- Water Buddy offers general wellness guidance, not medical advice. Personal needs can vary with health conditions, pregnancy, medications, weather, and clinician guidance.

<div align="center">

Made with 💧, Python, and Streamlit.

![Water Buddy animated footer](https://capsule-render.vercel.app/api?type=waving&color=0:7C3AED,50:2563EB,100:0EA5E9&height=120&section=footer&animation=fadeIn)

</div>
