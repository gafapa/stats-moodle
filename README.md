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

### Windows → `dist\MoodleAnalyzer.exe`

Requisitos: Python 3.11+ instalado y en el PATH.

```bat
build.bat
```

El script instala las dependencias, limpia artefactos previos y genera `dist\MoodleAnalyzer.exe` con PyInstaller. El `.exe` es autocontenido — no requiere Python ni instalación adicional en la máquina destino.

---

### Mac Apple Silicon (M1/M2/M3/M4) → `dist/MoodleAnalyzer`

**Opción A — Build local** (ejecutar en el propio Mac):

Requisitos: Python 3.11+ nativo arm64. Verificar antes de compilar:
```bash
python3 -c "import platform; print(platform.machine())"
# Debe mostrar: arm64
```

```bash
chmod +x build_mac.sh
./build_mac.sh
```

El ejecutable queda en `dist/MoodleAnalyzer`. La primera vez que se abre en el Mac:
```bash
xattr -cr dist/MoodleAnalyzer   # quitar bloqueo de Gatekeeper
./dist/MoodleAnalyzer
```

**Opción B — GitHub Actions** (desde cualquier sistema operativo):

1. Ir a [Actions → Build Mac Apple Silicon](https://github.com/gafapa/stats-moodle/actions/workflows/build_mac.yml)
2. Click en **Run workflow** → **Run workflow**
3. Esperar ~5-10 minutos
4. Descargar el artefacto `MoodleAnalyzer-mac-arm64` de la página del job

> PyInstaller no puede compilar de forma cruzada: el ejecutable de Windows debe generarse en Windows y el de Mac en macOS.

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
