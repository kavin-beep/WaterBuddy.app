## 🚀 [Open Water Buddy — Live App](https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/)

**Deployment:** [https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/](https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/)

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&amp;color=0:06B6D4,50:2563EB,100:7C3AED&amp;height=240&amp;section=header&amp;text=Water%20Buddy&amp;fontSize=66&amp;fontColor=FFFFFF&amp;animation=fadeIn&amp;desc=Small%20sips.%20Stronger%20habits.&amp;descSize=19&amp;descAlignY=73" width="100%" alt="Water Buddy — Small sips. Stronger habits." />

<a href="https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/">
<img src="https://readme-typing-svg.demolab.com?font=Inter&amp;weight=600&amp;size=23&amp;duration=3000&amp;pause=1400&amp;color=38BDF8&amp;center=true&amp;vCenter=true&amp;width=700&amp;height=55&amp;lines=Track+your+water.+Find+your+rhythm.;Care+for+your+pet.+Build+your+streak.;Meet+FLOW%2C+your+AI+hydration+coach." alt="Track your water. Care for your pet. Meet FLOW, your AI hydration coach." />
</a>

**Your daily hydration companion, with a little personality.**

Track water · Build habits · Care for your pet · Chat with FLOW

[![Open Water Buddy](https://img.shields.io/badge/OPEN_WATER_BUDDY-2563EB?style=for-the-badge&logo=streamlit&logoColor=white)](https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/)
[![Meet FLOW](https://img.shields.io/badge/MEET_FLOW-7C3AED?style=for-the-badge)](#-meet-flow)
[![Quick start](https://img.shields.io/badge/RUN_LOCALLY-0891B2?style=for-the-badge&logo=python&logoColor=white)](#-run-locally)

![Python](https://img.shields.io/badge/Python-3.12%2B-0F172A?style=flat-square&logo=python&logoColor=38BDF8)
![Streamlit](https://img.shields.io/badge/Streamlit-1.60-0F172A?style=flat-square&logo=streamlit&logoColor=FB7185)
![Groq](https://img.shields.io/badge/AI-Groq-0F172A?style=flat-square)
[![Test snapshot](https://img.shields.io/badge/150_tests-passed_29_Oct_2026-0F172A?style=flat-square&labelColor=166534)](#-testing)

[Explore](#-the-water-buddy-experience) · [Meet FLOW](#-meet-flow) · [Setup](#-run-locally) · [Deploy](#deployment) · [Privacy](#-data-and-privacy) · [Troubleshooting](#troubleshooting)

</div>

---

> **A small daily ritual.** Log a drink, watch your progress grow, and give your companion a reason to smile.

Water Buddy is a Python and Streamlit hydration app with personal dashboards, water logging, insights, achievements, reminders, and a virtual companion. FLOW answers questions through Groq using your current hydration context. Without a key—or when Groq cannot respond—the coach uses built-in offline rules.

## ✨ The Water Buddy experience

| Area | What it does |
| --- | --- |
| Home | Daily intake, goal progress, pace, and your companion. |
| Log water | Quick amounts, custom entries, editing, deletion, undo, and duplicate-entry protection. |
| Pet room | Care, moods, customization, quests, XP, levels, and evolution. |
| Insights | Hydration trends, adherence, streaks, and weekly challenges. |
| Achievements | Badges and milestone celebrations. |
| Reminders | Configurable intervals, quiet hours, snooze, and dismiss controls. |
| FLOW coach | Groq answers with recent conversation history and offline fallback. |
| Profile | Goals, preferences, units, themes, and backup import/export. |
| Accounts | Sign-in, per-account data, and remembered-device login. |
| Download app | Windows shortcut installer for the hosted website. |

Preferences include Dark, Light, Japanese, and Cyber themes, metric or US fluid-ounce units, ambience, and sound controls.

## 🚀 Run locally

Use **Python 3.12 or newer**, Git, and an internet connection to install dependencies. Run commands from the repository root.

### Windows (PowerShell)

```powershell
git clone https://github.com/kavin-beep/WaterBuddy.app.git
cd WaterBuddy.app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

These commands use the virtual environment directly; PowerShell activation is not required.

### macOS / Linux

```bash
git clone https://github.com/kavin-beep/WaterBuddy.app.git
cd WaterBuddy.app
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_app.py
```

Open the URL printed by Streamlit, then create an account or sign in. **Remember this device** uses a revocable browser token rather than your password. Explicitly signing out removes Quick Login from that browser.

## 💬 Meet FLOW

<table>
<tr>
<td width="50%" valign="top">

### ✦ When Groq is connected

Ask a question in your own words, get an answer grounded in your hydration context, and follow up naturally.

**Try:** “Make a gentle plan for the rest of my day.”

</td>
<td width="50%" valign="top">

### ◇ When you're offline

Built-in coaching rules provide practical hydration tips when no key is configured or the API cannot respond.

**Always clear:** a failed API request is identified before the fallback answer.

</td>
</tr>
</table>

### Connect FLOW to Groq

The API request runs on the Streamlit server. Keep the key in server-side configuration, never in source code, a chat message, or a public GitHub file.

### Local app

1. Create a key in the [Groq console](https://console.groq.com/keys).
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
3. Set the key in that file:

   ```toml
   GROQ_API_KEY = "paste-your-real-key-here"
   ```

4. Save and restart Streamlit.
5. Open **FLOW coach** and check for **Powered by Groq**.

The secrets file is ignored by Git. Alternatively, set a `GROQ_API_KEY` environment variable on the server. A nonempty environment variable takes precedence over Streamlit Secrets.

### Hosted Streamlit app

1. Open **Manage app → Settings → Secrets** in the deployed app.
2. Add the `GROQ_API_KEY` setting shown above, preserving other existing secrets.
3. Select **Save changes** and allow it to propagate. Reboot from the management menu if needed.
4. Return to FLOW and check for **Powered by Groq**.

**Saving a key on your computer does not configure the hosted app.** Never upload the actual secrets file to GitHub.

### How FLOW works

- Uses Groq's chat-completions API with `openai/gpt-oss-120b`.
- Sends up to 20 recent chat messages, excluding the initial greeting, together with intake, goal, remaining amount, progress percentage, display units, streak, local hour, and reminder settings.
- Keeps at most 51 messages in the page session, including the greeting. **Clear chat** resets the conversation.
- Uses a 25-second request timeout. Authentication errors, quota limits, connection failures, and invalid responses show a warning and use an offline answer.
- Cannot change settings, log water, or send notifications on your behalf. Use the corresponding app page.
- Offers general habit support, not diagnosis or medical advice. AI answers can be inaccurate.

Try asking:

- “How much water is left today?”
- “Make a gentle plan for the rest of the day.”
- “Are my reminders enabled?”
- “How can I keep my streak going?”
- Follow up with “Explain that in one sentence.”

The offline coach recognizes hydration topics with local rules; it is not a general-purpose AI chatbot. Groq requires internet access, model access, and available quota. Usage is associated with the configured Groq key.

<a id="deployment"></a>

## ☁️ Deploy on Streamlit Community Cloud

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
2. Create an app using this repository and the `main` branch.
3. Set the entry file to `streamlit_app.py` and select a supported Python version of 3.12 or newer.
4. Add `GROQ_API_KEY` in the app's Secrets for AI responses.
5. Deploy and check the FLOW connection banner.

The app runs without Groq configuration using offline coaching. The hosted website still requires an internet connection to its server.

## 🔐 Data and privacy

JSON data lives on the **machine running the Streamlit server**: your computer for a local installation, or the hosting environment for a deployment. It is not automatically browser-only storage.

| Data | Location or handling |
| --- | --- |
| Accounts | `data/accounts.json` |
| Hydration profiles | `data/users/` |
| Password verification | Salted PBKDF2-HMAC-SHA256 hashes |
| Remembered login | Browser token; server stores its digest |
| Profile recovery | Atomic writes and `.bak` copies |
| Groq key | Server environment or Streamlit Secrets |
| Chat history | Streamlit session state; recent messages go to Groq when AI is enabled |

Set `WATER_BUDDY_DATA_DIR` to choose a different server-side data directory. Account files, user data, and local secrets are excluded by `.gitignore`.

With Groq enabled, chat content and the listed hydration context leave the app for processing by Groq. The request does not include account passwords or the complete account database. Anything typed in chat may be included in a request.

The file-based account system is intended for a prototype or private installation. Use managed identity and durable database storage before relying on a public multi-user deployment. Export important data: hosted files may not survive a hosting change, and a `.bak` file on the same host is not an independent backup.

## 🔔 Reminders and Windows shortcut

Reminders are in-app prompts. Keep the tab and Streamlit server running; there is no background Windows reminder service. Quiet hours, snooze, and reaching the daily goal affect when prompts appear.

The **Download app** page provides a Windows ZIP installer that creates a desktop shortcut. It opens the hosted website in Chrome app mode, or the default browser if Chrome is unavailable. It is not a standalone offline app and does not add a startup service.

## 🧩 Project structure

<details>
<summary><strong>Explore the codebase</strong></summary>

```text
streamlit_app.py                 App shell, authentication, navigation, reminders
app_pages/                      Streamlit pages, including coach.py
water_buddy/
  auth.py                       Accounts, password verification, device sessions
  device_login.py               Remembered-device browser integration
  clock.py                      Per-session timezone handling
  domain.py                     Goals, entries, streaks, badges, reminders
  groq_coach.py                  Groq requests and safe error handling
  pet.py                        Pet progression, care, customization, quests
  storage.py                    JSON persistence, validation, recovery
  units.py                      Volume conversion and formatting
  ui.py                         Shared interface and pet rendering
  streamlit_theme.py            Streamlit theme integration
  audio.py                      Hydration feedback sounds
  interaction_audio.py          Browser interface sounds
  windows_download.py           Windows shortcut package
.streamlit/
  config.toml                   Streamlit configuration
  secrets.toml.example          Key template without a real key
requirements.txt                Python dependencies
tests/                          Unit and Streamlit page tests
```

`lib/`, `pubspec.yaml`, and `pubspec.lock` are retained from the original Flutter prototype. The deployed app and Groq integration documented here are the Streamlit implementation.

</details>

## 🧪 Testing

Using the Python interpreter where dependencies are installed:

```bash
python -m unittest discover -s tests -v
```

On Windows with the virtual environment above:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For only the Groq integration tests:

```bash
python -m unittest discover -s tests -p test_groq_coach.py -v
```

**Verification on October 29, 2026:** all 150 automated tests passed on Windows with Python 3.13 and Streamlit 1.60.0. Coverage includes domain rules, accounts, device sessions, timezones, storage recovery, units, pets, themes, accessibility contracts, downloads, and page interactions.

Groq tests mock network responses to check history, error handling, chat, clearing messages, and fallback without consuming API quota. Separate live Groq tests confirmed question-specific answers and follow-up context. The hosted app's connection banner was also checked after configuring its secret.

Passing tests do not guarantee every browser, hosting environment, or future API response will work. Live API tests and deployed-browser checks are separate from the automated suite.

<a id="troubleshooting"></a>

## 🛠️ Troubleshooting

<details>
<summary><strong>Connection, configuration, reminders, and data help</strong></summary>

| Symptom | Check |
| --- | --- |
| FLOW says it runs entirely on this device | Configure a nonempty `GROQ_API_KEY` on the running server: local Secrets or hosted Secrets as appropriate. |
| Groq rejects the key | Check Secrets and any environment variable that overrides it. Never post the key in an issue. |
| Usage-limit warning | Check Groq quota and rate limits; wait before retrying. |
| Groq unavailable | Check connectivity, provider availability, and access to the configured model. The app falls back to offline coaching. |
| TOML error | Use `GROQ_API_KEY = "..."` with ordinary quotes and no Markdown fences in the Secrets editor. |
| Hosted app shows old behavior | Confirm this repository and `main` branch are selected, allow updates to propagate, then reboot if needed. |
| No reminders | Check enabled state, quiet hours, snooze, goal completion, and whether the tab and server are running. |
| Missing data after a hosting change | Restore an exported backup and use durable storage where persistence is required. |

For bug reports, include the page, reproduction steps, expected and actual behavior, and Python/Streamlit versions. Remove secrets and private account data from screenshots and logs.

</details>

## 💙 Credits

- **Student:** Kavin K
- **Registration number:** 1000527
- **Mentor:** Syed Ali Beema S
- **School:** Jain Vidyalaya

Built with Python and Streamlit. AI coaching is served through Groq.

---

<div align="center">

**One sip at a time. One habit at a time.**

[Open Water Buddy](https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/) · [Get a Groq key](https://console.groq.com/keys) · [Report an issue](https://github.com/kavin-beep/WaterBuddy.app/issues)

<sub>Made for mindful hydration · Built by Kavin K</sub>

<img src="https://capsule-render.vercel.app/api?type=waving&amp;color=0:7C3AED,50:2563EB,100:06B6D4&amp;height=120&amp;section=footer" width="100%" alt="Blue and violet decorative wave" />

</div>
