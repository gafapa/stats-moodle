# Moodle Student Analyzer

Desktop application for analyzing Moodle course activity, student engagement, grade trends, and follow-up risk.

## Requirements

- Python 3.11+
- Dependencies from `requirements.txt`
- Access to a Moodle site with REST web services enabled

## Run

```bash
pip install -r requirements.txt
python main.py
```

At startup, the app asks for the UI language on the first screen. That language stays fixed for the session.

## Standalone Build

Windows:

```bat
build.bat
```

Linux/macOS:

```bash
./build.sh
```

The generated artifact is standalone and does not require Python or a separate dependency installation on the target machine.

## Project Website

Open `website/index.html` in a browser to view a simple static page that explains the idea of the project and how to use it.
The website includes client-side internationalization for Spanish, Galician, English, French, German, Catalan, and Basque.
The website also exposes a direct download link for the standalone Windows executable at `./downloads/MoodleAnalyzer.exe`.
Its copy also explains that analysis uses a configurable passing threshold and hides metrics that do not apply to the selected course.

## Web Server Bundle

To prepare a folder that is ready to upload to a web server:

```bat
prepare_web_release.bat
```

The script copies the website assets into `deploy/webserver/`, places the standalone executable in `deploy/webserver/downloads/MoodleAnalyzer.exe`, and runs `build.bat` automatically if the executable is missing.

## Connection Options

The application supports two authentication paths:

1. Direct token authentication with an existing Moodle web service token.
2. Automatic token generation through `login/token.php` using Moodle `username` and `password` with the `moodle_mobile_app` service for Mobile web services.

Passwords are only used in memory to request the token. They are not persisted in saved profiles.
The `Generate token` action and its explanation are only shown when the token field is empty.
If token generation fails, the application shows an explicit error dialog with the Moodle error message.

## Saved Profiles

Saved profiles store:

- Profile name
- Moodle base URL
- Token, when available
- Username, when provided

Saved profiles do not store passwords.

## Internationalization

The desktop app persists the selected UI language locally and supports:

- Spanish
- Galician
- English
- French
- German
- Catalan
- Basque

UI copy for the desktop app is centralized in `src/i18n.py`, and website copy is centralized in `website/app.js`.
Both were normalized to clean UTF-8 text so labels, hints, and status messages render without mojibake.
The desktop app now asks for the UI language on the initial connection screen and does not expose a language switcher after that first step.
The desktop runtime translation layer also handles icon-prefixed labels and dynamic status messages.

## Analysis Scope

The analyzer adapts its metrics to the course components that actually exist.

- If a course has no forums, forum participation is excluded from student and course-level analysis instead of being treated as zero participation.
- The same rule applies to assignments, quizzes, and completion-driven metrics when those components are not present in the course.
- Dashboards and detail views hide unsupported analysis sections instead of showing misleading empty metrics.

## Passing Threshold And Risk

- The passing grade threshold is configurable on the course selection screen before analysis starts.
- The default threshold is `50%`.
- The selected threshold is reused by grade-risk analysis, fail-risk estimation, chart reference lines, dashboard color cues, student detail indicators, and AI report context.
- Risk classification is conservative for high-performing students: mild signals by themselves should not move a student with clearly safe grades into medium risk.
- Risk interpretation is threshold-relative, so a course configured with a different pass mark is analyzed against that mark instead of a hardcoded `50%`.

## Outputs

The application can produce:

- Course dashboards with overview KPIs, risk distribution, recent activity, and adaptive metrics based on available Moodle components.
- Student-level views with engagement, predicted grade, risk level, assignment and quiz history, and timeline charts.
- Charts for distribution, comparison, correlation, percentile, and risk-oriented visual inspection.
- AI-assisted reports for courses, assignments, and individual students, using the active UI language and configured passing threshold as context.
- A static project website plus a deployable web-server bundle prepared with `prepare_web_release.bat`.

## Tests

```bash
python -m unittest discover -s tests
```
