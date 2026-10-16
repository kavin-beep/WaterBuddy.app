1| <div align="center">
2| 
3| ![Water Buddy animated header](https://capsule-render.vercel.app/api?type=waving&color=0:0EA5E9,45:2563EB,100:7C3AED&height=230&section=header&text=Water%20Buddy&fontSize=64&fontColor=FFFFFF&animat[...]
4| 
5| [![Launch Water Buddy](https://img.shields.io/badge/Launch_Water_Buddy-Live_App-0EA5E9?style=for-the-badge&logo=streamlit&logoColor=white)](https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.ap[...]
6| 
7| [![Animated introduction](https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=22&duration=2800&pause=900&color=2563EB&center=true&vCenter=true&width=760&lines=Track+water.+Build+streak[...]
8| 
9| [![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
10| [![Streamlit 1.60](https://img.shields.io/badge/Streamlit-1.60-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
11| [![Tests](https://img.shields.io/badge/tests-142%20passing-22C55E?style=for-the-badge&logo=checkmarx&logoColor=white)](#testing)
12| [![Local first](https://img.shields.io/badge/data-local--first-06B6D4?style=for-the-badge&logo=shield&logoColor=white)](#privacy-by-design)
13| 
14| **Water Buddy turns hydration into a small daily adventure—with quick logging, useful insights, gentle reminders, achievements, and a virtual companion named FLOW.**
15| 
16| streamlit app deploy link: https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/
17| 
18| </div>
19| 
20| > [!NOTE]
21| > FLOW uses a transparent offline coaching engine. The complete app works without an AI service, API key, or network connection.
22| 
23| ## ✨ Why Water Buddy?
24| 
25| | Experience | What you get |
26| |:--|:--|
27| | 🫗 **Effortless tracking** | Four customizable one-tap amounts, custom entries, editing, deletion, undo, and safe reset |
28| | 🎯 **Personal goals** | Age- and occupation-aware guidance, custom adjustments, and manual goal overrides |
29| | 💙 **FLOW hydration pet** | Moods, care actions, daily quests, hourly messages, 20 XP levels, evolution, and milestone outfits |
30| | 📊 **Useful insights** | 7/14/30-day trends, adherence, streaks, calendar-week challenges, and fair scoring for new users |
31| | 🏆 **Motivation** | Eight canonical achievement badges, daily tips, live pace feedback, and goal celebrations |
32| | 🔔 **Gentle reminders** | Configurable intervals, quiet hours, snooze/dismiss actions, and automatic rest after reaching your goal |
33| | 🎨 **Made for you** | Dark, Light, Japanese, and Cyber themes, responsive layouts, ambience, sounds, and metric or US fl oz display |
34| | 🛡️ **Resilient storage** | Atomic JSON writes, last-known-good backups, corruption recovery, validated imports, and local export |
35| 
36| ## 🚀 Run locally
37| 
38| Water Buddy requires **Python 3.12 or newer**.
39| 
40| ```powershell
41| git clone https://github.com/kavin-beep/WaterBuddy.app.git
42| cd WaterBuddy.app
43| 
44| python -m venv .venv
45| .\.venv\Scripts\Activate.ps1
46| python -m pip install -r requirements.txt
47| python -m streamlit run streamlit_app.py
48| ```
49| 
50| Open the Streamlit link, use **Sign in / Quick Login** on the public Home page,
51| then create an account or sign in. Keep **Remember this device** selected to open
52| future visits directly on your private Home dashboard. Water Buddy stores a
53| revocable device token for this convenience—never the account password—and
54| explicit **Sign out** removes Quick Login from that browser.
55| 
56| The public **Download app** page provides a small Windows ZIP installer. It
57| adds a WaterBuddy icon to the Desktop and opens the hosted app in Chrome app
58| mode (or the default browser when Chrome is unavailable); it does not install
59| background software or add a Windows startup item.
60| 
61| <details>
62| <summary><strong>macOS / Linux commands</strong></summary>
63| 
64| ```bash
65| python3 -m venv .venv
66| source .venv/bin/activate
67| python -m pip install -r requirements.txt
68| python -m streamlit run streamlit_app.py
69| ```
70| 
71| </details>
72| 
73| ## ☁️ Deploy on Streamlit Community Cloud
74| 
75| The repository is deployment-ready: `streamlit_app.py`, `requirements.txt`, and `.streamlit/config.toml` are all in the expected locations.
76| 
77| 1. Push this repository to GitHub.
78| 2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
79| 3. Select **Create app**, then choose this repository and branch.
80| 4. Set the main file path to `streamlit_app.py`.
81| 5. Open **Advanced settings**, select a supported Python version (3.12+), and deploy.
82| 
83| No secrets are required. For public multi-user use, replace local JSON authentication/storage with managed identity and database services first.
84| 
85| ## 🧭 App map
86| 
87| ```text
88| Welcome → Home → Log Water → Insights → Achievements
89|                  ├── FLOW Pet
90|                  ├── Coach
91|                  ├── Reminders
92|                  └── Profile & Preferences
93| ```
94| 
95| ## 🏗️ Architecture
96| 
97| ```text
98| streamlit_app.py                 App shell, authentication gate, navigation, reminders
99| app_pages/                       Streamlit page modules
100| water_buddy/auth.py              Account validation and salted password hashing
101| water_buddy/domain.py            Goals, water entries, streaks, badges, and reminders
102| water_buddy/pet.py               Pet progression, care, customization, and quests
103| water_buddy/storage.py           Thread-safe atomic JSON persistence and recovery
104| water_buddy/units.py             Canonical volume conversion and formatting
105| water_buddy/ui.py                Shared design system and animated pet rendering
106| water_buddy/audio.py             Dependency-free hydration feedback sounds
107| water_buddy/interaction_audio.py Browser-native interface feedback sounds
108| tests/                           Domain, storage, auth, UI, and page-level test suite
109| ```
110| 
111| The `lib/` directory and `pubspec.yaml` are retained as references from the original Flutter prototype. The production app is the Streamlit implementation launched by `streamlit_app.py`.
112| 
113| ## 🧪 Testing
114| 
115| ```powershell
116| python -m unittest discover -s tests -v
117| ```
118| 
119| The suite contains **142 passing tests** covering authentication, remembered-device login, per-user routing, logging and reward integrity, unit conversion, pet care, storage recovery, accessibility checks, and more.
120| 
121| Beyond the automated tests, Water Buddy was also checked by the people around me—my parents, my peers, and my mentor. They used it in real everyday situations and gave honest feedback on how easy it was to understand, how motivating it felt, and whether it actually helped with staying hydrated. My parents liked how simple and encouraging the app felt, my peers found it fun and practical, and my mentor appreciated the thoughtful design and the way the app focused on real user habits instead of just looks. Their support and positive feedback were really encouraging and helped shape the final version into something more useful, friendly, and motivating.
122| 
123| ## 🔐 Privacy by design
124| 
125| - Account records live in `data/accounts.json`; hydration profiles live in `data/users/`. Both are ignored by Git.
126| - Passwords are stored as salted PBKDF2 hashes, never as plaintext.
127| - Profile writes are atomic and maintain a matching `.bak` safety copy.
128| - Damaged documents are preserved as recovery evidence before a valid backup or safe default is restored.
129| - Imported backups are schema-checked and previewed before confirmation.
130| - No API key, cloud account, analytics service, or external AI provider is required.
131| 
132| > [!IMPORTANT]
133| > This local account model is intended for private use on your own machine. Use managed identity and database services before deploying Water Buddy as a public multi-user application.
134| 
135| ## ℹ️ Good to know
136| 
137| - Reminders operate while the Water Buddy browser tab and server are running.
138| - Sip Guard prevents duplicate entries for 30 seconds without changing intake, XP, achievements, sounds, or saved data.
139| - Water Buddy offers general wellness guidance, not medical advice. Personal needs can vary with health conditions, pregnancy, medications, weather, and clinician guidance.
140| 
141| <div align="center">
142| 
143| </div>
144| 
145| ## Credits
146| 
147| - Name of student: Kavin K
148| - Reg. No.: 1000527
149| - Mentor: Syed Ali Beema S
150| - Name of the school: Jain Vidyalaya
151| 
152|   Made with Python and Streamlit
153| 
154| <div align="center">
155| 
156| ![Water Buddy animated footer](https://capsule-render.vercel.app/api?type=waving&color=0:7C3AED,50:2563EB,100:0EA5E9&height=120&section=footer&animation=fadeIn)
157| 
158| </div>
159| 