# climate-challenge-week0

10 Academy Week 0 — African climate trend analysis (NASA POWER).

## Prerequisites

- Python 3.11+ recommended
- Git

## Environment setup

```bash
git clone https://github.com/<your-user>/climate-challenge-week0.git
cd climate-challenge-week0
python -m venv venv
```

**Windows (PowerShell)**

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (Git Bash) / macOS / Linux**

```bash
source venv/Scripts/activate   # Git Bash on Windows
# or: source venv/bin/activate on Unix
pip install -r requirements.txt
```

## Data

1. Download the five country CSVs from the challenge link (NASA POWER extracts).
2. Save as:

   - `data/ethiopia.csv`
   - `data/kenya.csv`
   - `data/sudan.csv`
   - `data/tanzania.csv`
   - `data/nigeria.csv`

3. Raw NASA POWER files include a metadata preamble; notebooks and `src/climate_cleaning.py` **auto-detect** the `YEAR` header row.

4. Cleaned outputs are written to `data/<country>_clean.csv` (gitignored).

## Run EDA notebooks

From the repository root:

```bash
jupyter lab
# or: jupyter notebook
```

Open:

- `notebooks/ethiopia_eda.ipynb` (repeat pattern for each country)
- `notebooks/compare_countries.ipynb`

Kernel: use the `venv` interpreter (`ipykernel` is in `requirements.txt`).

## Run tests (local CI)

```bash
pytest tests/ -q
```

## Streamlit dashboard

With data files present:

```bash
streamlit run app/main.py
```

Deployment: push to GitHub and connect the repo on [Streamlit Community Cloud](https://streamlit.io/cloud). Set the main file to `app/main.py`. **Secrets / data:** keep CSVs out of the repo; for a public demo, upload a private copy to Cloud secrets or use a release artifact per Streamlit docs.

Optional screenshot folder: `dashboard_screenshots/` (commit PNGs only).

## Folder layout

| Path | Purpose |
|------|---------|
| `src/` | Reusable load/clean/compare helpers |
| `notebooks/` | Per-country EDA + cross-country comparison |
| `app/` | Streamlit UI |
| `tests/` | `pytest` checks |
| `scripts/` | Optional automation |
| `data/` | Local data only (ignored by git) |

## Submissions

- **Interim (Sun 26 Apr 2026, 20:00 UTC):** GitHub `main` link + interim report (Task 1 summary, Task 2 approach).
- **Final (Tue 28 Apr 2026, 20:00 UTC):** GitHub `main` link + final Medium-style **PDF**; optional dashboard screenshot in `dashboard_screenshots/`.

## License

Challenge coursework — follow 10 Academy submission rules.
