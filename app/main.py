from __future__ import annotations

from pathlib import Path

import plotly.express as px
import streamlit as st

try:
    # When running from repo root (common locally / in notebooks)
    from app.utils import (
        DEFAULT_COUNTRIES,
        available_numeric_variables,
        expected_clean_csv_paths,
        filter_df,
        load_clean_csvs,
        monthly_mean,
        repo_root,
    )
except ModuleNotFoundError:
    # When Streamlit runs with `app/` on sys.path (common on some deployments)
    from utils import (  # type: ignore
        DEFAULT_COUNTRIES,
        available_numeric_variables,
        expected_clean_csv_paths,
        filter_df,
        load_clean_csvs,
        monthly_mean,
        repo_root,
    )


st.set_page_config(page_title="Climate cross-country dashboard", layout="wide")

st.title("Cross-country climate dashboard (Week 0)")
st.caption(
    "Reads local cleaned CSVs from `data/<country>_clean.csv` (gitignored). "
    "Use this to explore temperature and precipitation patterns across countries."
)


@st.cache_data(show_spinner=False)
def _load() -> tuple[object, list[str]]:
    root = repo_root()
    data_dir = root / "data"
    paths = expected_clean_csv_paths(data_dir, DEFAULT_COUNTRIES)
    res = load_clean_csvs(paths)
    return res.df, res.missing_files


df, missing = _load()

if missing:
    # Optional: try pulling the cleaned CSVs from a public Google Drive folder on Cloud.
    try:
        from app.utils import try_download_clean_csvs_from_gdrive, GDRIVE_FOLDER_ENV  # type: ignore
    except Exception:
        from utils import try_download_clean_csvs_from_gdrive, GDRIVE_FOLDER_ENV  # type: ignore

    root = repo_root()
    data_dir = root / "data"
    downloaded = try_download_clean_csvs_from_gdrive(data_dir)
    if downloaded:
        st.info(
            "Downloaded cleaned CSVs from Google Drive (env: "
            f"`{GDRIVE_FOLDER_ENV}`) — reloading data."
        )
        st.cache_data.clear()
        df, missing = _load()

    st.warning(
        "Missing cleaned CSVs (expected locally, not committed):\n\n"
        + "\n".join(f"- `{m}`" for m in missing)
    )

if df.empty:
    st.stop()

all_years = sorted(df["Year"].dropna().unique().tolist())
min_year, max_year = int(all_years[0]), int(all_years[-1])

st.sidebar.header("Filters")
countries = st.sidebar.multiselect(
    "Countries",
    options=sorted(df["Country"].unique().tolist()),
    default=DEFAULT_COUNTRIES,
)
year_range = st.sidebar.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(max(2015, min_year), min(2026, max_year)),
)

vars_ = available_numeric_variables(df)
default_var = "T2M" if "T2M" in vars_ else (vars_[0] if vars_ else None)
var = st.sidebar.selectbox("Variable (monthly mean)", options=vars_, index=vars_.index(default_var))

filtered = filter_df(df, countries=countries, year_range=year_range)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Temperature / variable trend (monthly mean)")
    mm = monthly_mean(filtered, var)
    if mm.empty:
        st.info("No data for current filters.")
    else:
        fig = px.line(
            mm,
            x="date",
            y="value",
            color="Country",
            markers=False,
            title=f"Monthly mean {var} ({year_range[0]}–{year_range[1]})",
        )
        fig.update_layout(legend_title_text="Country", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Precipitation distribution (daily)")
    if "PRECTOTCORR" not in filtered.columns:
        st.info("`PRECTOTCORR` not found in the loaded data.")
    else:
        fig = px.box(
            filtered,
            x="Country",
            y="PRECTOTCORR",
            points="outliers",
            title=f"Daily PRECTOTCORR distribution ({year_range[0]}–{year_range[1]})",
        )
        fig.update_yaxes(type="log", title="PRECTOTCORR (mm/day, log scale)")
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)


st.divider()
st.subheader("Quick data preview")
st.dataframe(
    filtered.sort_values(["Country", "date"]).tail(50),
    use_container_width=True,
)

