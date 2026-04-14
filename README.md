# Moodle Student Analyzer

Desktop application for analyzing Moodle course activity, student engagement, grade trends, and follow-up risk.

## Download

Pre-built executables are available from [GitHub Actions](https://github.com/gafapa/stats-moodle/actions):

| Platform | How to get it |
|---|---|
| **Windows** | Run `build.bat` or download from the web server bundle |
| **Mac (Apple Silicon M1/M2/M3/M4)** | Trigger the **"Build Mac Apple Silicon"** workflow in Actions, then download the artifact |

> **Mac note:** After downloading, remove the Gatekeeper quarantine flag before running:
> ```bash
> xattr -cr MoodleAnalyzer
> ./MoodleAnalyzer
> ```

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

Requirements: Python 3.11+ and access to a Moodle site with REST web services enabled.

At startup the app asks for the UI language on the first screen. That language stays fixed for the session.

## Build

**Windows:**
```bat
build.bat
```

**Mac (Apple Silicon — must run on the Mac itself):**
```bash
chmod +x build_mac.sh
./build_mac.sh
```

**Via GitHub Actions (Mac, from any OS):**
1. Go to [Actions → Build Mac Apple Silicon](https://github.com/gafapa/stats-moodle/actions/workflows/build_mac.yml)
2. Click **Run workflow**
3. Download the `MoodleAnalyzer-mac-arm64` artifact when the job finishes

The generated artifact is standalone and does not require Python or a separate dependency installation on the target machine.

## Credentials and privacy

Saved profiles are stored **locally** on each user's machine at `~/.moodle_analyzer/profiles.json`. They are never uploaded anywhere.

Profiles store:
- Profile name
- Moodle base URL
- Token (when available)
- Username (when provided)

**Passwords are never persisted.** They are only kept in memory to request a token and are discarded immediately after.

## Connection

Two authentication paths are supported:

1. **Direct token** — paste an existing Moodle web service token.
2. **Auto-generate token** — enter username and password; the app calls `login/token.php` with the `moodle_mobile_app` service and stores only the resulting token.

The "Generate token" option is only shown when the token field is empty. If generation fails, an explicit error dialog shows the Moodle error message.

## Internationalization

The desktop app supports:

- Spanish · Galician · English · French · German · Catalan · Basque

The UI language is chosen on the connection screen and stays fixed for the session. Desktop copy is centralized in `src/i18n.py`; website copy in `website/app.js`.

## Analysis scope

Metrics adapt to what actually exists in each course:

- Forums, assignments, quizzes, and completion metrics are excluded from analysis (not zeroed) when those components are not present.
- Dashboards and detail views hide unsupported sections instead of showing misleading empty metrics.

## Passing threshold and risk

- Configurable on the course selection screen (default: `50%`).
- Applies to grade-risk analysis, fail-risk estimation, chart reference lines, dashboard color cues, student detail indicators, and AI report context.
- Risk classification is conservative for high-performing students.

## Outputs

- Course dashboards — overview KPIs, risk distribution, recent activity, adaptive metrics.
- Student views — engagement, predicted grade, risk level, assignment/quiz history, timeline charts.
- Charts — distribution, comparison, correlation, percentile, risk-oriented.
- AI-assisted reports — for courses, assignments, and individual students (uses active language and configured threshold as context).
- Static project website + deployable web-server bundle (`prepare_web_release.bat`).

## Project website

Open `website/index.html` in a browser for a static overview page with client-side i18n (Spanish, Galician, English, French, German, Catalan, Basque) and a direct download link for the Windows executable.

To prepare a deployable web-server folder:
```bat
prepare_web_release.bat
```

## Tests

```bash
python -m unittest discover -s tests
```
