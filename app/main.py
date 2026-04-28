from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

try:
    import plotly.express as px  # type: ignore
except Exception:  # pragma: no cover
    px = None

# Ensure repo root is on sys.path (Streamlit Cloud sometimes runs with `app/` as cwd).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    # When running from repo root (common locally / in notebooks)
    from app.utils import (
        DEFAULT_COUNTRIES,
        available_numeric_variables,
        expected_clean_csv_paths,
        filter_df,
        load_clean_csvs,
        load_clean_csv_uploads,
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
        load_clean_csv_uploads,
        monthly_mean,
        repo_root,
    )


st.set_page_config(page_title="Climate cross-country dashboard", layout="wide")

st.title("Cross-country climate dashboard (Week 0)")
st.caption(
    "Upload one or more cleaned CSVs, or (optionally) load them from `data/<country>_clean.csv` "
    "when running locally. Use this to explore temperature and precipitation patterns across countries."
)

st.sidebar.header("Data source")
uploaded_files = st.sidebar.file_uploader(
    "Upload cleaned CSV file(s)",
    type=["csv"],
    accept_multiple_files=True,
    help=(
        "Upload one or more `*_clean.csv` files. Each CSV must have either a `date` column, "
        "or `YEAR` + `DOY`. A `Country` column is optional (it can be inferred from the filename)."
    ),
)


@st.cache_data(show_spinner=False)
def _load() -> tuple[object, list[str]]:
    root = repo_root()
    data_dir = root / "data"
    paths = expected_clean_csv_paths(data_dir, DEFAULT_COUNTRIES)
    df, missing = load_clean_csvs(paths)
    return df, missing


df, missing = _load()

if uploaded_files:
    try:
        df = load_clean_csv_uploads(uploaded_files)
        missing = []
    except Exception as e:
        st.error(f"Could not read uploaded CSV(s): {e}")
        st.stop()

if missing and not uploaded_files:
    # Optional: try pulling the cleaned CSVs from a public Google Drive folder on Cloud.
    try:
        from app.utils import (  # type: ignore
            try_download_clean_csvs_from_gdrive,
            gdrive_diagnostics,
            GDRIVE_FOLDER_ENV,
        )
    except Exception:
        from utils import (  # type: ignore
            try_download_clean_csvs_from_gdrive,
            gdrive_diagnostics,
            GDRIVE_FOLDER_ENV,
        )

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
    else:
        st.info(
            "Google Drive download did not run or did not produce the expected files. "
            f"Set `{GDRIVE_FOLDER_ENV}` in Streamlit Secrets to enable it."
        )
        with st.expander("Google Drive diagnostics"):
            st.json(gdrive_diagnostics(data_dir))

    st.warning(
        "Missing cleaned CSVs (expected locally, not committed):\n\n"
        + "\n".join(f"- `{m}`" for m in missing)
    )

if df.empty:
    st.info("No data loaded yet. Upload cleaned CSV file(s) from the sidebar to begin.")
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
        if px is None:
            st.line_chart(mm, x="date", y="value", color="Country", use_container_width=True)
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
        if px is None:
            st.bar_chart(
                filtered.groupby("Country", observed=True)["PRECTOTCORR"].median().sort_values(),
                use_container_width=True,
            )
            st.caption("Plotly not installed; showing median PRECTOTCORR by country.")
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

