"""Engineering dashboard for pipeline health, quality flags, and audit tables."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared import (  # noqa: E402
    DANGER,
    PRIMARY,
    SUCCESS,
    WARNING,
    apply_theme,
    load_csv_or_db,
)

st.set_page_config(
    page_title="Olist Engineering Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Olist Engineering Dashboard")
st.caption(
    "Answers: did the last pipeline run succeed, where did time go, and are "
    "there data-quality or ingestion issues?"
)

needs_data: list[str] = []
AIRFLOW_DIR = Path(os.getenv("AIRFLOW_DIR", str(Path.home() / "projects" / "airflow")))
DAG_ID = "ecommerce_pipeline"


def run_airflow(args: list[str], timeout: int = 60) -> tuple[str | None, str | None]:
    """Run an Airflow CLI command through docker-compose, without secrets."""
    command = [
        "docker-compose",
        "exec",
        "-T",
        "airflow-scheduler",
        "airflow",
        *args,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=str(AIRFLOW_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)

    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        return None, message[:300]
    return result.stdout, None


def parse_cli_table(text: str | None, columns: list[str]) -> pd.DataFrame:
    if not text:
        return pd.DataFrame(columns=columns)
    rows = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(columns):
            continue
        if cells[0] in {"dag_id", ""}:
            continue
        if set(cells[0]) <= set("-+= "):
            continue
        rows.append(cells)
    return pd.DataFrame(rows, columns=columns)


def add_datetimes(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("execution_date", "start_date", "end_date"):
        if column in frame.columns:
            frame[f"{column}_dt"] = pd.to_datetime(
                frame[column], errors="coerce", utc=True
            )
    if {"start_date_dt", "end_date_dt"}.issubset(frame.columns):
        frame["duration_seconds"] = (
            frame["end_date_dt"] - frame["start_date_dt"]
        ).dt.total_seconds()
    return frame


def fmt_duration(seconds: float | None) -> str:
    if seconds is None or pd.isna(seconds):
        return "<TBD>"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remaining = divmod(seconds, 60)
    return f"{int(minutes)}m {remaining:.0f}s"


def try_load(name: str) -> pd.DataFrame | None:
    try:
        return load_csv_or_db(name)
    except Exception:
        return None


runs_text, _ = run_airflow(["dags", "list-runs", "-d", DAG_ID])
runs = add_datetimes(
    parse_cli_table(
        runs_text,
        ["dag_id", "run_id", "state", "execution_date", "start_date", "end_date"],
    )
)

latest = runs.iloc[0] if not runs.empty else None
latest_run_id = str(latest["run_id"]) if latest is not None else None
latest_state = str(latest["state"]).lower() if latest is not None else None
latest_duration = (
    float(latest["duration_seconds"])
    if latest is not None and pd.notna(latest.get("duration_seconds"))
    else None
)

tasks = pd.DataFrame(
    columns=[
        "dag_id",
        "execution_date",
        "task_id",
        "state",
        "start_date",
        "end_date",
    ]
)
if latest_run_id:
    tasks_text, _ = run_airflow(
        ["tasks", "states-for-dag-run", DAG_ID, latest_run_id]
    )
    tasks = add_datetimes(
        parse_cli_table(
            tasks_text,
            [
                "dag_id",
                "execution_date",
                "task_id",
                "state",
                "start_date",
                "end_date",
            ],
        )
    )

if latest is None:
    needs_data.append("Airflow run history (CLI unavailable)")
    st.warning(
        "Airflow CLI is unavailable. Start the stack and run Streamlit from a "
        "shell with Docker permissions (for example, after `newgrp docker`)."
    )
else:
    if latest_state == "success":
        st.success(
            f"Latest run {latest_run_id} succeeded in {fmt_duration(latest_duration)}."
        )
    elif latest_state in {"failed", "upstream_failed"}:
        st.error(
            f"Latest run {latest_run_id} is {latest_state.upper()}. "
            "Inspect the task log before re-running."
        )
    elif latest_state in {"running", "queued"}:
        st.warning(f"Latest run {latest_run_id} is currently {latest_state}.")
    else:
        st.info(f"Latest run {latest_run_id} state: {latest_state}.")

    if not tasks.empty:
        counts = tasks["state"].value_counts().to_dict()
        st.caption(
            "Task counts: "
            + " · ".join(f"{state}={count}" for state, count in counts.items())
        )

# --- Data sources ----------------------------------------------------------
flags = try_load("vw_data_quality_flags")
batches = try_load("bronze_load_batches")
bronze_rejects = try_load("bronze_rejected_rows")
silver_rejects = try_load("silver_rejected_rows")

if flags is None:
    needs_data.append("vw_data_quality_flags")
if batches is None:
    needs_data.append("bronze.load_batches")
if bronze_rejects is None:
    needs_data.append("bronze.rejected_rows")
if silver_rejects is None:
    needs_data.append("silver.rejected_rows")

bronze_rows = None
if batches is not None and not batches.empty:
    batches = batches.copy()
    batches["row_count"] = pd.to_numeric(batches["row_count"], errors="coerce").fillna(0)
    successful = batches[batches["status"].astype(str).str.lower() == "success"]
    bronze_rows = int(successful["row_count"].sum())

rejects_total = None
if bronze_rejects is not None and silver_rejects is not None:
    rejects_total = int(len(bronze_rejects) + len(silver_rejects))
elif bronze_rejects is not None:
    rejects_total = int(len(bronze_rejects))
    needs_data.append("silver.rejected_rows")
elif silver_rejects is not None:
    rejects_total = int(len(silver_rejects))
    needs_data.append("bronze.rejected_rows")
else:
    needs_data.append("reject counts")

quality_total = None
if flags is not None and not flags.empty:
    flags = flags.copy()
    flags["rows"] = pd.to_numeric(flags["rows"], errors="coerce").fillna(0)
    quality_total = int(flags["rows"].sum())
else:
    needs_data.append("quality flag totals")

# --- KPI row ---------------------------------------------------------------
previous_duration = None
if len(runs) >= 2 and pd.notna(runs.iloc[1].get("duration_seconds")):
    previous_duration = float(runs.iloc[1]["duration_seconds"])

duration_delta = (
    latest_duration - previous_duration
    if latest_duration is not None and previous_duration is not None
    else None
)

kpi_columns = st.columns(4)
kpi_columns[0].metric(
    "Bronze Rows Loaded",
    f"{bronze_rows:,}" if bronze_rows is not None else "<TBD>",
)
if rejects_total is None:
    kpi_columns[1].metric("Total Rejects", "<TBD>")
elif rejects_total == 0:
    kpi_columns[1].metric("Total Rejects", "0", delta="0", delta_color="normal")
else:
    kpi_columns[1].metric(
        "Total Rejects",
        f"{rejects_total:,}",
        delta=f"{rejects_total:,}",
        delta_color="inverse",
    )
kpi_columns[2].metric(
    "Total Quality Flags",
    f"{quality_total:,}" if quality_total is not None else "<TBD>",
)
kpi_columns[3].metric(
    "Last Run Duration",
    fmt_duration(latest_duration),
    f"{duration_delta:+.1f}s vs previous" if duration_delta is not None else None,
    delta_color="inverse",
)
st.caption("Operational headline values for the latest successful build.")

# --- Chart row -------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Task duration waterfall")
    duration_df = tasks.dropna(subset=["duration_seconds"]).copy()
    if duration_df.empty:
        st.info("<TBD> — task durations are unavailable from the CLI.")
    else:
        duration_df = duration_df.sort_values("start_date_dt")
        duration_fig = px.bar(
            duration_df,
            x="duration_seconds",
            y="task_id",
            orientation="h",
            color="state",
            text=duration_df["duration_seconds"].round(2),
            color_discrete_map={
                "success": SUCCESS,
                "failed": DANGER,
                "upstream_failed": DANGER,
                "running": WARNING,
                "queued": PRIMARY,
            },
            labels={"duration_seconds": "Seconds", "task_id": "Task"},
        )
        duration_fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        duration_fig = apply_theme(duration_fig, title="Seconds per task")
        st.plotly_chart(duration_fig, use_container_width=True)
    st.caption("Answers: which task dominates the run and whether retries cost time?")

with right:
    st.subheader("Quality flags ranked")
    if flags is None or flags.empty:
        st.info("<TBD> — no quality-flag data available.")
    else:
        ranked = flags.sort_values("rows", ascending=False).copy()

        def flag_color(value: float) -> str:
            if value >= 500:
                return DANGER
            if value >= 100:
                return WARNING
            return SUCCESS

        ranked["color"] = ranked["rows"].apply(flag_color)
        flags_fig = px.bar(
            ranked,
            x="flag",
            y="rows",
            color="color",
            color_discrete_map={
                DANGER: DANGER,
                WARNING: WARNING,
                SUCCESS: SUCCESS,
            },
            text="rows",
            labels={"flag": "Quality flag", "rows": "Rows"},
        )
        flags_fig.update_layout(showlegend=False)
        flags_fig = apply_theme(flags_fig, title="Retained anomalies")
        st.plotly_chart(flags_fig, use_container_width=True)
    st.caption("Answers: which data-quality conditions are largest right now?")

# --- Full-width table: Airflow runs ---------------------------------------
st.subheader("Last 10 Airflow runs")
if runs.empty:
    st.info("<TBD> — run history is unavailable.")
else:
    runs_display = runs.head(10)[
        ["run_id", "state", "execution_date", "start_date", "end_date", "duration_seconds"]
    ].copy()
    runs_display["duration_seconds"] = runs_display["duration_seconds"].round(2)

    def state_style(value: str) -> str:
        color = {
            "success": SUCCESS,
            "failed": DANGER,
            "upstream_failed": DANGER,
            "running": WARNING,
            "queued": PRIMARY,
        }.get(str(value).lower(), "#FAFAFA")
        return f"color: {color}; font-weight: 600;"

    try:
        styled_runs = runs_display.style.map(state_style, subset=["state"])
    except AttributeError:
        styled_runs = runs_display.style.applymap(state_style, subset=["state"])
    st.dataframe(styled_runs, use_container_width=True, hide_index=True)
st.caption("Answers: is the scheduler producing runs consistently, and how stable is duration?")

# --- Secondary table: Bronze batches --------------------------------------
st.subheader("Bronze load batches")
if batches is None or batches.empty:
    st.info("<TBD> — bronze.load_batches is unavailable.")
else:
    batch_display = batches.copy()
    batch_display["started_at"] = pd.to_datetime(
        batch_display.get("started_at"), errors="coerce"
    )
    batch_display["finished_at"] = pd.to_datetime(
        batch_display.get("finished_at"), errors="coerce"
    )
    batch_display["duration_seconds"] = (
        batch_display["finished_at"] - batch_display["started_at"]
    ).dt.total_seconds()
    batch_display["hash_skipped"] = "first load"
    if "source_file" in batch_display.columns:
        batch_display = batch_display.sort_values("started_at")
        for _, group in batch_display.groupby("source_file"):
            if len(group) > 1:
                batch_display.loc[group.index[1:], "hash_skipped"] = "new version"
    columns = [
        "load_id",
        "source_file",
        "row_count",
        "status",
        "started_at",
        "duration_seconds",
        "hash_skipped",
    ]
    batch_display = batch_display[
        [column for column in columns if column in batch_display.columns]
    ]
    st.dataframe(batch_display, use_container_width=True, hide_index=True)
    st.caption(
        "Answers: what was loaded and when? A hash-skipped re-run leaves no new "
        "row, so each row is the first load of a file version."
    )

# --- Freshness -------------------------------------------------------------
bronze_last = None
if batches is not None and not batches.empty and "finished_at" in batches.columns:
    finished = pd.to_datetime(batches["finished_at"], errors="coerce")
    successful_mask = batches["status"].astype(str).str.lower() == "success"
    if finished[successful_mask].notna().any():
        bronze_last = finished[successful_mask].max()

silver_last = None
if not tasks.empty and "task_id" in tasks.columns:
    silver_tasks = tasks[tasks["task_id"] == "silver_rebuild"]
    if not silver_tasks.empty:
        silver_times = pd.to_datetime(silver_tasks["end_date"], errors="coerce")
        if silver_times.notna().any():
            silver_last = silver_times.max()

st.caption(
    "Last successful Bronze load: "
    f"{bronze_last if bronze_last is not None else '<TBD>'} · "
    "Silver rebuild: "
    f"{silver_last if silver_last is not None else '<TBD>'}"
)

if needs_data:
    with st.expander("Needs data"):
        for item in sorted(set(needs_data)):
            st.write(f"- {item}")

st.caption(
    "Sources: Airflow CLI (docker-compose exec airflow-scheduler airflow ...), "
    "Gold quality flags, and Bronze/Silver audit tables."
)
