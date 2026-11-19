# imports
import os
import re
import shutil
import numpy as np
import pandas as pd
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

def get_spray_vals(str_case_id: str, base_dir: Path, plane_x: float, d_case: dict, N_bins: int):

    case_dir = base_dir / Path(str_case_id)

    state_file = case_dir / "state.txt"
    if state_file.exists():
        state = state_file.read_text().strip()
    else:
        logger.warning(f"Could not find state file - terminating post processing")
        return

    # Run VOF post processing__________________________________________________________________________________________

    ctrl_dict = case_dir / "system/controlDict"

    if state == "run complete":
        subprocess.run(f"foamDictionary {str(ctrl_dict)} -entry functions/planeDropletAnalysis/enabled -set true -disableFunctionEntries", shell=True, check=True)

        subprocess.run(f"foamDictionary {str(ctrl_dict)} -entry functions/planeDropletAnalysis/plane_x -set {plane_x} -disableFunctionEntries", shell=True, check=True)

        subprocess.run(f'srun atomizationFoam -parallel -postProcess > log.postprocess 2>&1', cwd=case_dir, shell=True, check=True)

        state = "vof post processed"
        state_file.write_text(state)

    elif state == "vof post processed":
        vof_file = case_dir / "postProcessing" / "plane_droplets.csv"
        if vof_file.exists():
            logger.warning("Found state as 'vof post processed' - skipping vof processing.")
        else:
            logger.warning(f"State as 'vof post processed' but no file found at {vof_file} - terminating post processing")
            return
    else:
        logger.warning(f"Simulation did not finish as expected - found state {state} - terminating post processing")
        return

    # Import VOF stats on plane________________________________________________________________________________________

    vof_data_file = case_dir / "postProcessing/plane_droplets.csv"
    df_vof = pd.read_csv(vof_data_file)
    if df_vof.empty:
        df_vof = pd.DataFrame(columns=['t', 'x', 'y', 'z', 'vx', 'vy', 'vz', 'A', 'V', 'r', 'th', 'vr', 'source'])
    else:
        df_vof['source'] = 'vof'
        df_vof['r']  = np.sqrt(df_vof['y']**2 + df_vof['z']**2)
        df_vof['th'] = np.arctan2(df_vof['z'], df_vof['y'])
        df_vof['vr'] = np.where(df_vof['r'] > 0.0, (df_vof['y'] * df_vof['vy'] + df_vof['z'] * df_vof['vz']) / df_vof['r'], 0.0)

    # Import Lagrangian stats__________________________________________________________________________________________

    df_lag = import_lagrangian_cloud(case_dir=case_dir, plane_x=plane_x)
    df_lag['r']  = np.sqrt(df_lag['y']**2 + df_lag['z']**2)
    df_lag['th'] = np.arctan2(df_lag['z'], df_lag['y'])
    df_lag['vr'] = np.where(df_lag['r'] > 0.0, (df_lag['y'] * df_lag['vy'] + df_lag['z'] * df_lag['vz']) / df_lag['r'], 0.0)

    # Run individual calculations______________________________________________________________________________________

    SMD_mean, SMD_t, SMD_lag_t, SMD_vof_t = calculate_SMD(df_lag=df_lag, df_vof=df_vof)

    phi_seg = 2*np.pi / d_case["des_N_o"]
    N_seg = np.floor(np.pi/2 / phi_seg)
    rev_angle = N_seg * phi_seg
    std_final_v_rel, final_v_rel, bin_widths = calculate_uniformity(df_lag=df_lag, df_vof=df_vof, N_bins=N_bins, rev_angle=rev_angle)

    angle_m, angle_t = calculate_spray_angle(df_lag=df_lag, df_vof=df_vof)

    dp = get_delta_p(point=(0, d_case["geo_D_p"] / 4, d_case["geo_D_p"] / 4), case_dir=case_dir)

    # Save outputs_____________________________________________________________________________________________________
    common_cols = ['t', 'x', 'y', 'z', 'r', 'th', 'vx', 'vy', 'vz', 'vr', 'A', 'V', 'source']
    df_all = pd.concat([df_lag[common_cols], df_vof[common_cols]], ignore_index=True)
    # df_all.to_parquet(case_dir / "postProcessing/crossed_droplets.parquet", index=False)

    out_dir = case_dir / "results"
    out_dir.mkdir(exist_ok=True)

    df_ts = pd.DataFrame({
        "case_id": str_case_id,
        "t": SMD_t.index,
        "SMD": SMD_t.values,
        "SMD_lag": SMD_lag_t.reindex(SMD_t.index).values,
        "SMD_vof": SMD_vof_t.reindex(SMD_t.index).values,
        "angle": angle_t.reindex(SMD_t.index).values,
    })
    df_ts.to_parquet(out_dir / "spray_timeseries.parquet", index=False)

    summary_row = {
        "case_id": str_case_id,
        "SMD_mean": SMD_mean,
        "spray_angle_deg": np.degrees(angle_m),
        "uniformity_std": std_final_v_rel,
        "ox_dp": dp,
        "V_total": df_all["V"].sum(),
        "V_lag_frac": df_lag["V"].sum() / df_all["V"].sum() if df_all["V"].sum() > 0 else np.nan,
        "n_droplets": len(df_all),
    }
    pd.DataFrame([summary_row]).to_parquet(out_dir / "spray_summary.parquet", index=False)

    np.savez(
        out_dir / "spray_azimuthal.npz",
        case_id=str_case_id,
        final_v_rel=final_v_rel,
        bin_widths=bin_widths,
    )


# ---------------------------------------------------------------------------------------------------------------------
# Calculate SMD
# ---------------------------------------------------------------------------------------------------------------------

def calculate_SMD(df_lag: pd.DataFrame, df_vof: pd.DataFrame):

    cols = ['t', 'A', 'V', 'source']
    df = pd.concat([df_lag[cols], df_vof[cols]], ignore_index=True)

    df_A_V_sum = df.groupby(['t'])[['V', 'A']].sum()
    SMD = 6 * df_A_V_sum['V'] / df_A_V_sum['A']

    df_A_V_sum_lag = df_lag.groupby(['t'])[['V', 'A']].sum()
    SMD_lag = 6 * df_A_V_sum_lag['V'] / df_A_V_sum_lag['A']

    df_A_V_sum_vof = df_vof.groupby(['t'])[['V', 'A']].sum()
    SMD_vof = 6 * df_A_V_sum_vof['V'] / df_A_V_sum_vof['A']

    SMD_mean = 6 * df_A_V_sum['V'].sum() / df_A_V_sum['A'].sum()

    return SMD_mean, SMD, SMD_lag, SMD_vof


# ---------------------------------------------------------------------------------------------------------------------
# Calculate Uniformity
# ---------------------------------------------------------------------------------------------------------------------

def calculate_uniformity(df_lag: pd.DataFrame, df_vof: pd.DataFrame, N_bins: int, rev_angle: float):

    cols = ['t', 'x', 'r', 'th', 'V', 'source']
    df = pd.concat([df_lag[cols], df_vof[cols]], ignore_index=True)

    th_bins = np.linspace(0, rev_angle, N_bins + 1)
    th_cs = (th_bins[:-1] + th_bins[1:]) / 2
    bin_widths = np.diff(th_bins)

    df['th_bin'] = pd.cut(df['th'], bins=th_bins, include_lowest=True, labels=th_cs)

    v_per_step = (df.groupby(['t', 'th_bin'], observed=False)['V'].sum().unstack(fill_value=0))

    v_cum = v_per_step.cumsum(axis=0)
    if v_cum.empty:
        return np.nan, np.full(N_bins, np.nan), bin_widths

    final_v = v_cum.iloc[-1].to_numpy(dtype=float)
    total_v = final_v.sum() # all bins

    if not np.isfinite(total_v) or total_v <= 0:
        return np.nan, np.full(N_bins, np.nan), bin_widths

    final_v_rel = final_v / total_v
    std_final_v_rel = np.std(final_v_rel)

    return std_final_v_rel, final_v_rel, bin_widths



# ---------------------------------------------------------------------------------------------------------------------
# Calculate Spray Angle
# ---------------------------------------------------------------------------------------------------------------------

def calculate_spray_angle(df_lag: pd.DataFrame, df_vof: pd.DataFrame):

    cols = ['t', 'V', 'vx', 'vr', 'source']
    df = pd.concat([df_lag[cols], df_vof[cols]], ignore_index=True)

    df['V_vx'] = df['V'] * df['vx']
    df['V_vr'] = df['V'] * df['vr']

    df_t = df.groupby('t')[['V', 'V_vx', 'V_vr']].sum()

    vx_m_t = df_t['V_vx'] / df_t['V']
    vr_m_t = df_t['V_vr'] / df_t['V']

    angle_t = np.arctan2(vr_m_t, vx_m_t)

    vx_m = df_t['V_vx'].sum() / df_t['V'].sum()
    vr_m = df_t['V_vr'].sum() / df_t['V'].sum()

    angle_m = np.arctan2(vr_m, vx_m)

    return angle_m, angle_t


# ---------------------------------------------------------------------------------------------------------------------
# Get delta P
# ---------------------------------------------------------------------------------------------------------------------

def get_delta_p(point: tuple[float, float, float], case_dir: Path):
    x,y,z = point
    content = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      probes;
}}

type            probes;
libs            ("libsampling.so");
fields          (p);
probeLocations  (({x} {y} {z}));
"""

    (case_dir / "system" / "probes").write_text(content)

    probes_out = case_dir / "postProcessing" / "probes"
    if probes_out.exists():
        shutil.rmtree(probes_out)

    subprocess.run(
        "srun atomizationFoam -parallel -postProcess -func probes -noFunctionObjects -latestTime >> log.postprocess 2>&1",
        cwd=case_dir,
        shell=True,
        check=True,
    )

    if not probes_out.exists():
        logger.warning(f"No probes output file was created at: {probes_out}")
        return np.nan

    time_dirs = [d for d in probes_out.iterdir() if d.is_dir()]
    if not time_dirs:
        raise RuntimeError("postProcess finished, but no probe output was written.")

    data_file = time_dirs[0] / "p"
    for line in data_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # Line format: <time>   <value>
            return float(line.split()[1])

    logger.warning(f"No valid pressure value found in {data_file}")
    return np.nan
# _____________________________________________________________________________________________________________________
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Helper Functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def import_lagrangian_cloud(case_dir: Path, plane_x: float):
    proc_dir_pattern = "processor*"
    proc_dirs = [p for p in case_dir.glob(proc_dir_pattern)]

    lag_data_list = []

    for proc_dir in proc_dirs:
        t_strings = [d for d in os.listdir(proc_dir) if is_number(d)]
        for t_str in t_strings:
            t_val = float(t_str)
            lag_dir = proc_dir / t_str / "lagrangian/dropletCloud/"
            if not os.path.exists(lag_dir):
                print(f"Didnt find lagrangian directory in {proc_dir} at time {t_str}")
                continue
            d_file = lag_dir / "d"
            pos_file = lag_dir / "positions"
            vel_file = lag_dir / "U"
            if not os.path.exists(pos_file):
                print(f"Didnt find positions file in {proc_dir} at time {t_str}")
                continue
            origId_file = lag_dir / "origId"
            origProcId_file = lag_dir / "origProcId"
            d_vals = read_openfoam_diameters(d_file)
            pos_vals = read_openfoam_positions(pos_file)
            vel_vals = read_openfoam_velocities(vel_file, expected_count=len(d_vals))
            origId_vals = read_openfoam_labels(origId_file, expected_count=len(d_vals))
            origProcId_vals = read_openfoam_labels(origProcId_file, expected_count=len(d_vals))
            id_vals = [f"{p}_{id}" for p, id in zip(origProcId_vals, origId_vals)]
            df_tmp = pd.DataFrame({
                "t":  t_val,
                "x":  pos_vals[:,0],
                "y":  pos_vals[:,1],
                "z":  pos_vals[:,2],
                "d":  d_vals,
                "vx": vel_vals[:,0],
                "vy": vel_vals[:,1],
                "vz": vel_vals[:,2],
                "id": id_vals
            })
            lag_data_list.append(df_tmp)

    empty_cols = ['t', 'x', 'y', 'z', 'd', 'vx', 'vy', 'vz', 'id', 'A', 'V', 'source']
    if not lag_data_list:
        return pd.DataFrame(columns=empty_cols)

    df_lag_all = pd.concat(lag_data_list, ignore_index=True)

    seen_ids = set() # set type for O(1) lookup speed
    df_lag_list = []

    first_observations = (df_lag_all.sort_values("t").drop_duplicates("id", keep="first"))
    started_before_plane = set(first_observations.loc[first_observations["x"] < plane_x, "id"])

    for t_val, df_tmp in df_lag_all.groupby('t'):
        crossed_mask = (df_tmp['x'] >= plane_x) & (~df_tmp['id'].isin(seen_ids))
        df_new_crossed = df_tmp[crossed_mask]

        if not df_new_crossed.empty:
            seen_ids.update(df_new_crossed['id'].tolist())
            df_new_crossed = df_new_crossed.loc[df_new_crossed["id"].isin(started_before_plane)]
            if not df_new_crossed.empty:
                df_lag_list.append(df_new_crossed)
            

    if not df_lag_list:
        return pd.DataFrame(columns=empty_cols)

    df_lag = pd.concat(df_lag_list, ignore_index=True)

    df_lag['A'] = np.pi * df_lag['d']**2
    df_lag['V'] = np.pi * df_lag['d']**3 / 6.0
    df_lag['source'] = 'lagrangian'

    return df_lag


# Helper - Helper Functions____________________________________________________________________________________________

def read_openfoam_positions(filepath):
    positions_dat = []
    
    # Matches: (x y z) cell_id, including scientific notation like 4.25897e-05
    pattern = re.compile(r'\(\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)\s*\)\s*(\d+)')
    
    with open(filepath, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                x, y, z, _ = match.groups()
                positions_dat.append([float(x), float(y), float(z)])

    pos_array = np.array(positions_dat) if len(positions_dat) > 0 else np.empty((0, 3), dtype=float)
    return pos_array


def read_openfoam_diameters(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        if '// * * * *' in content:
            content = content.split('// * * * *')[-1].strip()

    if not content:
        return np.array([], dtype=float)

    # Compact uniform: e.g. 5{1.5e-05}
    match_curly = re.search(r'(\d+)\s*\{\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*\}', content)
    if match_curly:
        return np.full(int(match_curly.group(1)), float(match_curly.group(2)), dtype=float)

    # Standard list: e.g. 5(\n1.5e-05\n...)
    match = re.search(r'(\d+)\s*\(\s*([\s\S]*?)\s*\)', content)
    if match:
        count = int(match.group(1))
        body = match.group(2).strip()
        if count == 0 or not body:
            return np.array([], dtype=float)
        parsed = np.fromstring(body, dtype=float, sep=' ')
        if len(parsed) == 1 and count > 1:
            return np.full(count, parsed[0], dtype=float)
        return parsed

    return np.array([], dtype=float)


def read_openfoam_velocities(filepath, expected_count=None):
    with open(filepath, 'r') as f:
        content = f.read()
        if '// * * * *' in content:
            content = content.split('// * * * *')[-1].strip()

    if not content:
        return np.empty((0, 3), dtype=float)

    vec_pat = r'\(\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*\)'

    # Compact uniform: e.g. 5{(10 0 0)}
    match_curly = re.search(r'(\d+)\s*\{\s*' + vec_pat + r'\s*\}', content)
    if match_curly:
        count = int(match_curly.group(1))
        vec = [float(match_curly.group(2)), float(match_curly.group(3)), float(match_curly.group(4))]
        return np.tile(vec, (count, 1))

    # Uniform keyword: e.g. uniform (10 0 0);
    match_uniform = re.search(r'uniform\s+' + vec_pat + r'\s*;', content)
    if match_uniform and expected_count is not None:
        vec = [float(match_uniform.group(1)), float(match_uniform.group(2)), float(match_uniform.group(3))]
        return np.tile(vec, (expected_count, 1))

    matches = re.findall(vec_pat, content)
    if not matches:
        return np.empty((0, 3), dtype=float)
    return np.array(matches, dtype=float)


def read_openfoam_labels(filepath, expected_count=None):
    if not os.path.exists(filepath):
        return np.array([], dtype=int)
        
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Strip OpenFOAM header banner if present
    if '// * * * *' in content:
        content = content.split('// * * * *')[-1]

    content = content.strip()
    if not content:
        return np.array([], dtype=int)

    # 2. Compact Uniform Notation: e.g. "4{1}" -> 4 elements of value 1
    match_curly = re.search(r'(\d+)\s*\{\s*(-?\d+)\s*\}', content)
    if match_curly:
        count = int(match_curly.group(1))
        val = int(match_curly.group(2))
        return np.full(count, val, dtype=int)

    # 3. Standard List Notation: e.g. "4(19 20 21 0)" or multi-line "92\n(\n1\n...)"
    match_paren = re.search(r'(\d+)\s*\(\s*([\s\S]*?)\s*\)', content)
    if match_paren:
        count = int(match_paren.group(1))
        body = match_paren.group(2).strip()
        if count == 0 or not body:
            return np.array([], dtype=int)
        
        parsed = np.fromstring(body, dtype=int, sep=' ')
        
        # Edge case: single-value compressed list like "500(0)"
        if len(parsed) == 1 and count > 1:
            return np.full(count, parsed[0], dtype=int)
        return parsed

    # 4. Uniform Keyword Notation: e.g. "uniform 1;"
    match_uniform = re.search(r'uniform\s+(-?\d+);', content)
    if match_uniform and expected_count is not None:
        val = int(match_uniform.group(1))
        return np.full(expected_count, val, dtype=int)

    return np.array([], dtype=int)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False