<img width="1879" height="1032" alt="website.jpg" src="https://github.com/user-attachments/assets/a57345f6-9edb-4e13-83dc-571b473ef663" />

# 🎓 CyberAcademy Matrix — Deep Focus Task Dashboard

A premium, glassmorphic Python Flask task manager and study assistant designed to optimize academic and professional focus sprints. It features dynamic priority color-coding, custom background audio triggers, and an automated timeline shifting system.

---

## 🌌 Key Features

* **Dynamic Priority Matrix**: Beautifully visual color-blocking for task identification based on high, medium, and low urgency thresholds.
* **Audio Engine Bypass**: Secure, browser-compliant web audio pipeline utilizing HTML5 Audio constraints safely.
* **Chrono Ripple Engine**: An intelligent scheduling algorithm that allows you to extend an active block and seamlessly cascade the exact delay across the rest of your day.

---

## ⚡ The Chrono Ripple Extension Feature
When a session deadline passes, an integrated system modal sounds an alarm and checks if you have completed the objective. If you need more time, you can extend your deadline. You can configure how that time shift cascades through the rest of your dashboard:

1. **Just This Task**: Updates only the active task's end time.
2. **Delay Next Tasks**: Cascades the exact minute delay to the start and end times of all remaining subsequent items down the list.
3. **Delay All Tasks**: Delays all incomplete tasks globally on your schedule.

---

## ⚙️ Architecture & File Structure

```text
MINI PROJECTS-2/
├── templates/
│   └── index.html   # Main dashboard and glassmorphic UI matrix
├── static/
│   └── alarm.mp3     # Local audio asset folder for alert execution
└── App.py           # Multi-threaded Flask core server & time tracking loops
