# WaterBuddy Windows companion

The desktop mascot is controlled only from **WaterBuddy → Profile → Desktop Pet**.
It is a transparent, frameless PySide6 companion, not a Streamlit page. It reads
the same local profile through `JsonStore`, so water logs use the existing domain
logic and automatically update intake, XP, levels, achievements, reminders, pet
name, mood, and equipped accessory.

Click the mascot for quick water logging, Open WaterBuddy, Snooze, and Skip.
Double-click opens Home; right-click provides quick actions and removal. Position
is saved after dragging, clamped to the current monitor work area, and restored.
A named Windows mutex and loopback command channel enforce one running instance.

## Build and install

```powershell
.\windows_companion\build.ps1
.\windows_companion\install.ps1 -Profile ".\data\users\YOUR_PROFILE.json"
```

The installer adds only a Desktop shortcut. Startup is deliberately opt-in:

```powershell
.\windows_companion\install.ps1 -Profile ".\data\users\YOUR_PROFILE.json" -StartWithWindows
```

Enable the mascot in Profile after installing it. Turning the Profile toggle off,
or choosing **Remove mascot from Windows**, disables the same profile setting and
stops the companion. The executable and optional shortcut remain reinstallable.

The current Streamlit deployment stores profile JSON on its server. Browser code
cannot securely start a Windows executable or expose that server-side file. The
`ProfileBridge` protocol therefore provides a clean boundary for a future managed,
authenticated sync backend; the included `LocalJsonProfileBridge` is fully live
when WaterBuddy and the companion share a local profile.
