## African Climate Trend Analysis (2015–2026)

**Project:** EthioClimate Analytics — COP32 preparation (Week 0 challenge)  
**Countries:** Ethiopia, Kenya, Sudan, Tanzania, Nigeria  
**Data source:** NASA POWER daily climate variables (single representative location per country)

### Executive summary (negotiation-ready)
- **Temperature differences across countries are statistically significant.** A Kruskal–Wallis test on annual-mean daily temperatures indicates the five countries do **not** share the same temperature distribution (**p ≈ 1.84e-10**), supporting cross-country comparisons beyond noise.
- **Sudan emerges as the highest climate-stress profile** in a four-pillar composite (rainfall volatility, heat exposure, drought duration, and warming rate): **vulnerability score ≈ 0.70 (rank #1/5)**.
- **Nigeria is warming fastest** over this 2015–2026 window at **~+0.87 °C/decade**, while Sudan shows a negative fitted slope (**~−1.46 °C/decade**) that likely reflects **strong interannual variability** across a short window rather than “true cooling”.
- **Precipitation instability is most pronounced in Sudan** (interannual CV of annual totals **~0.60** vs ~0.29–0.33 for the other countries), increasing planning risk for rainfed systems.
- **Extreme heat and long dry spells concentrate in Sudan**: **~224 days/year** with **T2M_MAX > 35°C** and **~143-day** mean annual maximum consecutive dry spell (PRECTOTCORR < 1 mm).

### Business context
Ethiopia will host COP32 in 2027. A credible position paper needs:  
1) what is changing (trend), 2) what it causes (stress proxy), and 3) what it demands (policy/finance ask).  
This report focuses on (1) and (2) using the provided dataset, and uses those signals to justify (3): **priority adaptation finance and early-warning investment** in the most stressed profiles.

---

## Task 1 — Git, environment & CI (how the project is reproducible)
- Repo uses a Python virtual environment (`venv/`) and `requirements.txt`.
- `data/` and `*.csv` are **gitignored** (data never committed).
- Notebooks and reusable logic live under `notebooks/` and `src/`.

---

## Task 2 — Per-country cleaning & EDA (what was standardized)
For each country’s NASA POWER CSV:
- **Date parsing:** `YEAR` + `DOY` → `date` using `%Y%j`; add `Month`.
- **Missing sentinel handling:** replace `-999` with `NaN` before stats.
- **Duplicates:** detect and drop exact-row duplicates.
- **Outliers:** z-score flags (|z| > 3) recorded; extremes were retained to preserve climate-stress signals.
- **Missing values:** forward-fill small gaps; drop sparse rows (row-level missingness > 30%).
- **Output:** cleaned daily dataset exported locally as `data/<country>_clean.csv` (gitignored).

---

## Task 3 — Cross-country comparison (2015–2026)

### 1) Temperature trend comparison
- **Visualization:** monthly mean **T2M** plotted for all five countries on one chart (2015–2026).  
- **Summary stats (daily T2M):** mean/median/std were computed per country to compare central tendency and variability.

Key interpretation:
- Sudan’s higher mean and higher variability align with an arid/hot baseline climate and larger seasonal swings.
- Nigeria and Tanzania are warm but show different precipitation stress profiles (see rainfall and dry-spell sections).

### 2) Precipitation variability comparison
- **Visualization:** side-by-side boxplots of **PRECTOTCORR** (mm/day) for the five countries (symlog scaling to show zero-inflation + heavy tail).
- **Summary stats (daily PRECTOTCORR):** mean/median/std per country.

Key interpretation:
- Daily precipitation is **highly skewed and zero-inflated** (many dry days with intermittent heavy rain), so medians help separate “typical” daily conditions from extreme events.
- Interannual instability is better reflected by annual totals and their CV (used in the vulnerability score).

### 3) Extreme event frequency
Two annual metrics were computed per country:
- **Extreme heat days:** count of days/year where **T2M_MAX > 35°C**.
- **Drought stress proxy:** annual **maximum consecutive dry spell length** (days where **PRECTOTCORR < 1 mm**).

Key interpretation:
- Sudan dominates both heat-day counts and dry-spell lengths, indicating chronic stress and stronger exposure to compounding risks (heat + drought).

### 4) Statistical testing (Kruskal–Wallis)
To test whether T2M differs across countries:
- **Annual-mean T2M Kruskal–Wallis:** **p ≈ 1.84e-10** → strong evidence temperature distributions differ by country over this window.

Note: daily tests can be overly sensitive because \(N\) is large; annual aggregation is more policy-legible.

---

## Vulnerability ranking (composite, data-driven)
The notebook computes a transparent composite score (0–1, higher = more stressed) using four pillars:
1) **Warming rate** (°C/decade; annual mean T2M trend)  
2) **Rainfall volatility** (CV of annual precipitation totals)  
3) **Heat exposure** (mean annual heat days > 35°C)  
4) **Drought duration** (mean annual max dry streak)

### Ranking results (from `compare_countries.ipynb`)
- **#1 Sudan** — vulnerability score **~0.70**  
- **#2 Nigeria** — **~0.32**  
- **#3 Ethiopia** — **~0.29**  
- **#4 Tanzania** — **~0.26**  
- **#5 Kenya** — **~0.25**

Supporting pillar metrics (selected):
- **Nigeria warming rate:** **~+0.87 °C/decade** (fastest)  
- **Sudan rainfall volatility (CV):** **~0.60** (highest)  
- **Sudan heat exposure:** **~224 days/year** with **T2M_MAX > 35°C**  
- **Sudan dry streak:** **~143 days** mean annual maximum consecutive dry spell  
- **Ethiopia context:** warming **~+0.43 °C/decade**, rainfall CV **~0.33**, **0** heat days >35°C, dry streak **~38 days**

---

## COP32 framing — five bullets (from notebook narrative)
1) **Fastest warming:** **Nigeria** (~+0.87 °C/decade) over 2015–2026; Sudan’s negative fitted slope (~−1.46 °C/decade) likely reflects short-window variability rather than structural cooling.  
2) **Most unstable precipitation:** **Sudan** (annual rainfall CV ~0.60) → heightened uncertainty for agriculture/water planning.  
3) **Extreme heat + drought stress:** Sudan concentrates both **heat-day exposure** and **long dry spells**, which is the most policy-relevant “stress stack.”  
4) **Ethiopia vs neighbors:** Ethiopia is mid-pack on warming and rainfall variability, and strongly separated from Sudan on extremes due to highland buffering (0 heat days >35°C at the grid point).  
5) **Priority climate finance ask:** The evidence supports Ethiopia championing **Sudan** for priority adaptation + loss-and-damage support at COP32 (highest composite stress profile across volatility + heat + drought).

---

## Bonus — Streamlit dashboard
The repo includes a minimal Streamlit dashboard (`app/main.py`) with:
- Country multi-select
- Year range slider
- Monthly mean trend line (variable selector; defaults to `T2M`)
- Daily `PRECTOTCORR` distribution boxplot (log scale)

### Deployment note
Because `data/` is gitignored, the Cloud app must load CSVs at runtime. The dashboard supports a Google Drive folder download when `GDRIVE_FOLDER_URL` is configured in Streamlit Secrets.

---

## Limitations and caveats (important for policy readers)
- Each country represents **one location/grid point**, not a national spatial mean; results compare “representative points”, not full-country aggregates.
- The period (2015–2026) is relatively short for climate trend inference; interpret slopes as **recent-change indicators**, not long-term climatology.
- Impact statistics (yields, displacement, GDP) are not in the dataset; a final position paper should weld these climate signals to secondary sources (e.g., WMO Africa climate reports, World Bank country profiles).

---

## Reproducibility (how to run)
- Create venv and install requirements:

```bash
python -m venv venv
source venv/Scripts/activate  # Git Bash (Windows)
pip install -r requirements.txt
```

- Run notebooks:

```bash
jupyter lab
```

- Run dashboard locally:

```bash
venv/Scripts/python.exe -m streamlit run app/main.py
```

---

## References (recommended for “negotiation-grade” final PDF)
- WMO State of the Climate in Africa (annual series)  
- World Bank Climate Risk Country Profiles / Climate Knowledge Portal  
- IPCC AR6 Africa chapter

