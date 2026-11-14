import os
import json
import subprocess
from datetime import datetime

import dash
from dash import html, dcc, Input, Output, clientside_callback
import dash_bootstrap_components as dbc

# =====================================================================
# CONFIG (Edit these or set HPC_HOST / HPC_DIR env vars)
# =====================================================================
SSH_HOST = os.environ.get("HPC_HOST", "giger@jed.epfl.ch")  # Or your ~/.ssh/config alias, e.g. "jed"
REMOTE_DIR = os.environ.get("HPC_DIR", "/scratch/giger/Sensitivity_Analysis")
JOB_NAME_FILTER = "pintle"  # Set to "" to show all your Slurm jobs
SSH_TIMEOUT = 10


# =====================================================================
# REMOTE SCRIPTS (Python 3.6+ compatible for RHEL/Rocky login nodes)
# =====================================================================
REMOTE_SCAN_SCRIPT = r"""
import os, re, sys, glob, json, subprocess
from datetime import datetime

remote_dir = sys.argv[1]
job_filter = sys.argv[2]
cases_dir = os.path.join(remote_dir, "cases")
of_logs = ["log.atomizationFoam", "log.init", "log.balance"]

def expand_array(spec):
    spec = spec.strip("[]").split("%")[0]
    ids = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            ids.extend(range(int(a), int(b) + 1))
        elif part.isdigit():
            ids.append(int(part))
    return ids

def quick_tail(path, max_bytes=6144):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            return f.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

slurm_tasks = {}
try:
    res = subprocess.run(
        ["squeue", "--me", "-h", "-o", "%i|%j|%T|%M|%R"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, timeout=5
    )
    if res.returncode == 0:
        for line in res.stdout.strip().splitlines():
            parts = line.split("|")
            if len(parts) < 5:
                continue
            raw_id, jname, state, elapsed, reason = parts
            if job_filter and jname != job_filter:
                continue
            if "_" in raw_id:
                master_id, arr = raw_id.split("_", 1)
                for tid in expand_array(arr):
                    slurm_tasks[tid] = {
                        "job_id": master_id,
                        "state": state,
                        "elapsed": elapsed,
                        "reason": reason,
                    }
except Exception:
    pass

task_ids = set(slurm_tasks.keys())
if os.path.isdir(cases_dir):
    for entry in os.listdir(cases_dir):
        m = re.match(r"^case_(\d+)$", entry)
        if m:
            task_ids.add(int(m.group(1)))

for f in glob.glob(os.path.join(remote_dir, "job_*_*.out")):
    m = re.search(r"job_\d+_(\d+)\.out$", os.path.basename(f))
    if m:
        task_ids.add(int(m.group(1)))

rows = []
for tid in sorted(task_ids):
    case_name = "case_{:04d}".format(tid)
    case_dir = os.path.join(cases_dir, case_name)

    out_matches = glob.glob(os.path.join(remote_dir, "job_*_{}.out".format(tid)))
    err_matches = glob.glob(os.path.join(remote_dir, "job_*_{}.err".format(tid)))
    latest_out = max(out_matches, key=os.path.getmtime) if out_matches else None
    latest_err = max(err_matches, key=os.path.getmtime) if err_matches else None

    file_job_id = "-"
    ref = latest_out or latest_err
    if ref:
        m = re.search(r"job_(\d+)_\d+\.(out|err)$", os.path.basename(ref))
        if m:
            file_job_id = m.group(1)

    latest_log = None
    latest_mtime = 0.0
    if os.path.isdir(case_dir):
        for lname in of_logs:
            p = os.path.join(case_dir, lname)
            if os.path.exists(p):
                mt = os.path.getmtime(p)
                if mt > latest_mtime:
                    latest_mtime = mt
                    latest_log = lname

    if latest_log:
        ts = datetime.fromtimestamp(latest_mtime).strftime("%H:%M:%S")
        stage = "{} ({})".format(latest_log.replace("log.", ""), ts)
    elif os.path.isdir(case_dir):
        stage = "Waiting for logs"
    else:
        stage = "-"

    if tid in slurm_tasks:
        s = slurm_tasks[tid]
        status = s["state"]
        job_id = s["job_id"]
        runtime = s["elapsed"]
        note = s["reason"] if status == "PENDING" else "Active on node"
    else:
        job_id = file_job_id
        runtime = "-"
        err_tail = quick_tail(latest_err)
        foam_tail = quick_tail(os.path.join(case_dir, "log.atomizationFoam"))
        has_err = any(
            k in err_tail
            for k in ["FOAM FATAL ERROR", "CANCELLED", "TIME LIMIT", "Segmentation fault", "Traceback"]
        )
        if has_err:
            status = "FAILED"
            note = "Error detected in .err"
        elif "\nEnd" in foam_tail or foam_tail.strip().endswith("End"):
            status = "COMPLETED"
            note = "Finished cleanly"
        elif latest_out:
            status = "STOPPED"
            note = "Exited without 'End'"
        else:
            status = "NOT STARTED"
            note = "No Slurm logs yet"

    rows.append({
        "task_id": tid,
        "case_name": case_name,
        "job_id": job_id,
        "status": status,
        "runtime": runtime,
        "stage": stage,
        "note": note,
    })

print(json.dumps({"rows": rows}))
"""

REMOTE_LOGS_SCRIPT = r"""
import os, sys, glob, json

remote_dir = sys.argv[1]
task_id = int(sys.argv[2])
max_lines = int(sys.argv[3])

case_name = "case_{:04d}".format(task_id)
case_dir = os.path.join(remote_dir, "cases", case_name)

def tail_file(filepath, n_lines):
    if not filepath or not os.path.exists(filepath):
        return "[File not found on HPC]"
    try:
        with open(filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return "[Log file is currently empty]"
            block_size = 8192
            blocks = []
            lines_found = 0
            pos = size
            while pos > 0 and lines_found <= n_lines:
                read_len = min(block_size, pos)
                pos -= read_len
                f.seek(pos)
                chunk = f.read(read_len)
                blocks.append(chunk)
                lines_found += chunk.count(b"\n")
            text = b"".join(reversed(blocks)).decode("utf-8", errors="replace")
            lines = text.splitlines()
            if len(lines) > n_lines:
                return "... [Showing last {} lines] ...\n".format(n_lines) + "\n".join(lines[-n_lines:])
            return "\n".join(lines)
    except Exception as e:
        return "[Error reading log: {}]".format(e)

out_matches = glob.glob(os.path.join(remote_dir, "job_*_{}.out".format(task_id)))
err_matches = glob.glob(os.path.join(remote_dir, "job_*_{}.err".format(task_id)))
latest_out = max(out_matches, key=os.path.getmtime) if out_matches else None
latest_err = max(err_matches, key=os.path.getmtime) if err_matches else None

payload = {
    "out_name": os.path.basename(latest_out) if latest_out else "job_*_{}.out (missing)".format(task_id),
    "err_name": os.path.basename(latest_err) if latest_err else "job_*_{}.err (missing)".format(task_id),
    "out_text": tail_file(latest_out, max_lines),
    "err_text": tail_file(latest_err, max_lines),
    "of_logs": {
        "log.atomizationFoam": tail_file(os.path.join(case_dir, "log.atomizationFoam"), max_lines),
        "log.init": tail_file(os.path.join(case_dir, "log.init"), max_lines),
        "log.balance": tail_file(os.path.join(case_dir, "log.balance"), max_lines),
    },
}
print(json.dumps(payload))
"""


# =====================================================================
# SSH RUNNER (Uses ControlMaster multiplexing on Linux/WSL2 for speed)
# =====================================================================
def run_remote_python(script: str, args: list[str]) -> tuple[dict | None, str | None]:
    cmd = ["ssh", "-o", f"ConnectTimeout={SSH_TIMEOUT}", "-o", "BatchMode=yes"]

    # Reuse single SSH socket on Linux/WSL2 so 5s refreshes take ~40ms
    if os.name == "posix":
        cmd.extend([
            "-o", "ControlMaster=auto",
            "-o", "ControlPath=/tmp/dash_hpc_mux_%r@%h:%p",
            "-o", "ControlPersist=10m",
        ])

    cmd.extend([SSH_HOST, "python3", "-", *args])

    try:
        res = subprocess.run(
            cmd,
            input=script,
            capture_output=True,
            text=True,
            timeout=SSH_TIMEOUT + 5,
        )
    except subprocess.TimeoutExpired:
        return None, f"SSH connection to {SSH_HOST} timed out."
    except FileNotFoundError:
        return None, "`ssh` executable not found in PATH."
    except Exception as e:
        return None, f"SSH execution failed: {e}"

    if res.returncode != 0:
        err_msg = res.stderr.strip() or f"SSH exited with code {res.returncode}"
        return None, err_msg

    try:
        return json.loads(res.stdout), None
    except json.JSONDecodeError:
        return None, f"Invalid JSON from remote host:\n{res.stdout[:400]}"


# =====================================================================
# DASH UI SETUP
# =====================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Pintle HPC Monitor"


def status_badge(status: str) -> dbc.Badge:
    colors = {
        "RUNNING": "success",
        "PENDING": "warning",
        "COMPLETED": "info",
        "FAILED": "danger",
        "STOPPED": "secondary",
        "NOT STARTED": "dark",
    }
    return dbc.Badge(status, color=colors.get(status, "secondary"), className="px-2 py-1")


app.layout = dbc.Container(
    fluid=True,
    className="py-4 px-4",
    children=[
        dcc.Store(id="selected-task-store", data=None),
        dcc.Input(id="dblclick-bridge", type="text", value="", style={"display": "none"}),
        dcc.Interval(id="refresh-interval", interval=30000, n_intervals=0),

        # Header
        dbc.Row(
            className="align-items-center mb-3",
            children=[
                dbc.Col(
                    [
                        html.H3("Pintle Simulation Monitor", className="mb-0 fw-bold"),
                        html.Small(
                            f"SSH: {SSH_HOST}  |  Dir: {REMOTE_DIR}  |  Double-click any row to inspect logs",
                            className="text-muted",
                        ),
                    ],
                    md=8,
                ),
                dbc.Col(
                    className="d-flex justify-content-md-end align-items-center gap-3 mt-2 mt-md-0",
                    md=4,
                    children=[
                        dbc.Switch(
                            id="auto-refresh-toggle",
                            label="Live Refresh (30s)",
                            value=True,
                            className="mb-0",
                        ),
                        dbc.Button("Refresh Now", id="manual-refresh-btn", color="primary", size="sm"),
                    ],
                ),
            ],
        ),

        # SSH Error Banner (hidden when healthy)
        html.Div(id="ssh-error-banner"),

        # Summary KPI Cards
        html.Div(id="summary-cards", className="mb-4"),

        # Cases Table
        dbc.Card(
            className="mb-4 shadow-sm",
            children=[
                dbc.CardHeader(
                    className="d-flex justify-content-between align-items-center",
                    children=[
                        html.Span("Simulation Cases", className="fw-semibold"),
                        html.Small(id="last-sync-label", className="text-muted"),
                    ],
                ),
                dbc.CardBody(
                    className="p-0",
                    children=[
                        html.Div(
                            id="cases-table-container",
                            style={"maxHeight": "380px", "overflowY": "auto"},
                        )
                    ],
                ),
            ],
        ),

        # Log Viewer Panel (Appears on double-click)
        html.Div(
            id="log-viewer-wrapper",
            style={"display": "none"},
            children=[
                dbc.Card(
                    className="shadow-sm border-primary",
                    children=[
                        dbc.CardHeader(
                            className="d-flex flex-wrap justify-content-between align-items-center gap-2",
                            children=[
                                html.Div(
                                    [
                                        html.Span("Inspecting: ", className="text-muted"),
                                        html.Span(id="log-header-title", className="fw-bold text-info fs-5"),
                                    ]
                                ),
                                html.Div(
                                    className="d-flex align-items-center gap-2",
                                    children=[
                                        dbc.Select(
                                            id="tail-lines-select",
                                            options=[
                                                {"label": "Last 150 lines", "value": 150},
                                                {"label": "Last 300 lines", "value": 300},
                                                {"label": "Last 1000 lines", "value": 1000},
                                            ],
                                            value=300,
                                            size="sm",
                                            style={"width": "160px"},
                                        ),
                                        dbc.Button(
                                            "Close Logs",
                                            id="close-logs-btn",
                                            color="outline-light",
                                            size="sm",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        dbc.CardBody(
                            children=[
                                dbc.Row(
                                    className="mb-4",
                                    children=[
                                        dbc.Col(
                                            md=6,
                                            className="mb-3 mb-md-0",
                                            children=[
                                                html.Div(
                                                    id="slurm-out-label",
                                                    className="fw-semibold text-success mb-1 small",
                                                ),
                                                html.Pre(
                                                    id="slurm-out-content",
                                                    style={
                                                        "backgroundColor": "#111",
                                                        "color": "#e0e0e0",
                                                        "padding": "12px",
                                                        "borderRadius": "6px",
                                                        "height": "340px",
                                                        "overflowY": "auto",
                                                        "fontSize": "12px",
                                                        "whiteSpace": "pre-wrap",
                                                        "border": "1px solid #333",
                                                    },
                                                ),
                                            ],
                                        ),
                                        dbc.Col(
                                            md=6,
                                            children=[
                                                html.Div(
                                                    id="slurm-err-label",
                                                    className="fw-semibold text-danger mb-1 small",
                                                ),
                                                html.Pre(
                                                    id="slurm-err-content",
                                                    style={
                                                        "backgroundColor": "#111",
                                                        "color": "#ff9e9e",
                                                        "padding": "12px",
                                                        "borderRadius": "6px",
                                                        "height": "340px",
                                                        "overflowY": "auto",
                                                        "fontSize": "12px",
                                                        "whiteSpace": "pre-wrap",
                                                        "border": "1px solid #442222",
                                                    },
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                html.Hr(className="my-3"),
                                html.Div("OpenFOAM Solver Logs", className="fw-semibold mb-2 small text-muted"),
                                dbc.Tabs(
                                    id="openfoam-log-tabs",
                                    active_tab="log.atomizationFoam",
                                    children=[
                                        dbc.Tab(label="log.atomizationFoam", tab_id="log.atomizationFoam"),
                                        dbc.Tab(label="log.init", tab_id="log.init"),
                                        dbc.Tab(label="log.balance", tab_id="log.balance"),
                                    ],
                                ),
                                html.Pre(
                                    id="openfoam-log-content",
                                    className="mt-2 mb-0",
                                    style={
                                        "backgroundColor": "#111",
                                        "color": "#cfd8dc",
                                        "padding": "12px",
                                        "borderRadius": "6px",
                                        "height": "300px",
                                        "overflowY": "auto",
                                        "fontSize": "12px",
                                        "whiteSpace": "pre-wrap",
                                        "border": "1px solid #333",
                                    },
                                ),
                            ]
                        ),
                    ],
                )
            ],
        ),
    ],
)


# =====================================================================
# CLIENTSIDE DOUBLE-CLICK LISTENER
# =====================================================================
clientside_callback(
    """
    function(containerId) {
        const container = document.getElementById(containerId);
        if (container && !container.dataset.dblclickAttached) {
            container.dataset.dblclickAttached = "true";
            container.addEventListener("dblclick", function(e) {
                const row = e.target.closest("tr[data-task-id]");
                if (row) {
                    const input = document.getElementById("dblclick-bridge");
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, "value"
                    ).set;
                    nativeSetter.call(input, row.dataset.taskId + ":" + Date.now());
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                }
            });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("cases-table-container", "title"),
    Input("cases-table-container", "id"),
)


# =====================================================================
# SERVER CALLBACKS
# =====================================================================
@app.callback(
    Output("refresh-interval", "disabled"),
    Input("auto-refresh-toggle", "value"),
)
def toggle_interval(enabled: bool) -> bool:
    return not enabled


@app.callback(
    Output("selected-task-store", "data"),
    Input("dblclick-bridge", "value"),
    Input("close-logs-btn", "n_clicks"),
    prevent_initial_call=True,
)
def handle_case_selection(dblclick_val: str, _):
    triggered = dash.ctx.triggered_id
    if triggered == "close-logs-btn":
        return None
    if triggered == "dblclick-bridge" and dblclick_val:
        task_id_str = dblclick_val.split(":")[0]
        if task_id_str.isdigit():
            return int(task_id_str)
    return dash.no_update


@app.callback(
    Output("ssh-error-banner", "children"),
    Output("summary-cards", "children"),
    Output("cases-table-container", "children"),
    Output("last-sync-label", "children"),
    Input("refresh-interval", "n_intervals"),
    Input("manual-refresh-btn", "n_clicks"),
    Input("selected-task-store", "data"),
)
def refresh_dashboard(_, __, selected_task_id):
    data, err = run_remote_python(REMOTE_SCAN_SCRIPT, [REMOTE_DIR, JOB_NAME_FILTER])

    if err:
        banner = dbc.Alert(
            [
                html.Strong("SSH Connection Error: "),
                html.Code(err, className="text-light"),
            ],
            color="danger",
            className="mb-3",
        )
        return banner, dash.no_update, dash.no_update, f"Failed at {datetime.now().strftime('%H:%M:%S')}"

    cases = data.get("rows", [])
    counts = {
        "TOTAL": len(cases),
        "RUNNING": sum(1 for c in cases if c["status"] == "RUNNING"),
        "PENDING": sum(1 for c in cases if c["status"] == "PENDING"),
        "COMPLETED": sum(1 for c in cases if c["status"] == "COMPLETED"),
        "FAILED": sum(1 for c in cases if c["status"] == "FAILED"),
    }

    cards = dbc.Row(
        className="g-3",
        children=[
            dbc.Col(dbc.Card(dbc.CardBody([html.Small("Total Cases", className="text-muted"), html.H4(counts["TOTAL"], className="mb-0")])), xs=6, md=True),
            dbc.Col(dbc.Card(dbc.CardBody([html.Small("Running", className="text-success"), html.H4(counts["RUNNING"], className="mb-0 text-success")])), xs=6, md=True),
            dbc.Col(dbc.Card(dbc.CardBody([html.Small("Pending", className="text-warning"), html.H4(counts["PENDING"], className="mb-0 text-warning")])), xs=6, md=True),
            dbc.Col(dbc.Card(dbc.CardBody([html.Small("Completed", className="text-info"), html.H4(counts["COMPLETED"], className="mb-0 text-info")])), xs=6, md=True),
            dbc.Col(dbc.Card(dbc.CardBody([html.Small("Failed", className="text-danger"), html.H4(counts["FAILED"], className="mb-0 text-danger")])), xs=6, md=True),
        ],
    )

    if not cases:
        table = html.Div(
            f"Connected to {SSH_HOST}, but no cases or Slurm jobs found in {REMOTE_DIR}.",
            className="p-4 text-center text-muted",
        )
    else:
        header = html.Thead(
            html.Tr(
                [
                    html.Th("Case"),
                    html.Th("Array ID"),
                    html.Th("Job ID"),
                    html.Th("Status"),
                    html.Th("Runtime"),
                    html.Th("Latest OpenFOAM Stage"),
                    html.Th("Info"),
                ]
            )
        )
        body_rows = []
        for c in cases:
            row_class = "table-active" if selected_task_id == c["task_id"] else ""
            body_rows.append(
                html.Tr(
                    className=row_class,
                    style={"cursor": "pointer", "userSelect": "none"},
                    **{"data-task-id": str(c["task_id"])},
                    children=[
                        html.Td(html.Strong(c["case_name"])),
                        html.Td(str(c["task_id"])),
                        html.Td(c["job_id"]),
                        html.Td(status_badge(c["status"])),
                        html.Td(c["runtime"]),
                        html.Td(c["stage"]),
                        html.Td(html.Small(c["note"], className="text-muted")),
                    ],
                )
            )
        table = dbc.Table(
            [header, html.Tbody(body_rows)],
            hover=True,
            responsive=True,
            className="mb-0 align-middle",
        )

    sync_text = f"Last synced: {datetime.now().strftime('%H:%M:%S')}"
    return None, cards, table, sync_text


@app.callback(
    Output("log-viewer-wrapper", "style"),
    Output("log-header-title", "children"),
    Output("slurm-out-label", "children"),
    Output("slurm-out-content", "children"),
    Output("slurm-err-label", "children"),
    Output("slurm-err-content", "children"),
    Output("openfoam-log-content", "children"),
    Input("selected-task-store", "data"),
    Input("refresh-interval", "n_intervals"),
    Input("manual-refresh-btn", "n_clicks"),
    Input("openfoam-log-tabs", "active_tab"),
    Input("tail-lines-select", "value"),
)
def update_log_viewer(task_id, _, __, active_of_tab, max_lines):
    if task_id is None:
        return {"display": "none"}, "", "", "", "", "", ""

    max_lines = str(max_lines or 300)
    case_name = f"case_{task_id:04d}"

    payload, err = run_remote_python(REMOTE_LOGS_SCRIPT, [REMOTE_DIR, str(task_id), max_lines])
    if err:
        return (
            {"display": "block"},
            f"{case_name} (Task ID {task_id})",
            "Output Log",
            f"[SSH Error: {err}]",
            "Error Log",
            f"[SSH Error: {err}]",
            f"[SSH Error: {err}]",
        )

    of_logs = payload.get("of_logs", {})
    return (
        {"display": "block"},
        f"{case_name} (Task ID {task_id})",
        f"Output Log: {payload.get('out_name')}",
        payload.get("out_text", ""),
        f"Error Log: {payload.get('err_name')}",
        payload.get("err_text", ""),
        of_logs.get(active_of_tab, ""),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)