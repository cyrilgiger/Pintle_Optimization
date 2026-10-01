#%% imports
import numpy as np
import re
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import os
from IPython import get_ipython

ipython = get_ipython()
if ipython is not None:
    ipython.run_line_magic("matplotlib", "widget")

#%% Inputs

sim_dir = Path(__file__).parent.resolve() / "run_openfoam_hex_amr"
plane_x = 35e-3  # only applied to lagrangian clouds !! for vof check controlDict/functions

#%% Import VOF stats on plane

vof_data_file = sim_dir / "postProcessing/plane_droplets.csv"
df_vof = pd.read_csv(vof_data_file)
df_vof['source'] = 'vof'

#%% Import Lagrangian stats
#____________________________________________________________________________________
# Helper Functions
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
                
    return np.array(positions_dat)

def read_openfoam_diameters(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Grab everything inside the data block starting after the list count
    match = re.search(r'\n\d+\s*\(\s*([\s\S]*?)\s*\)', content)
    if match:
        # np.fromstring automatically parses scientific notation and whitespace-separated numbers
        return np.fromstring(match.group(1), dtype=float, sep=' ')

    return np.array([])

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
#____________________________________________________________________________________

proc_dir_pattern = "processor*"
proc_dirs = [p for p in sim_dir.glob(proc_dir_pattern)]

lag_data_list = []

for proc_dir in proc_dirs:
    t_strings = [d for d in os.listdir(proc_dir) if is_number(d)]
    for t_str in t_strings:
        t_val = float(t_str)
        lag_dir = proc_dir / t_str / "lagrangian/dropletCloud/"
        if not os.path.exists(lag_dir):
            continue
        d_file = lag_dir / "d"
        pos_file = lag_dir / "positions"
        origId_file = lag_dir / "origId"
        origProcId_file = lag_dir / "origProcId"
        d_vals = read_openfoam_diameters(d_file)
        pos_vals = read_openfoam_positions(pos_file)
        origId_vals = read_openfoam_labels(origId_file, expected_count=len(d_vals))
        origProcId_vals = read_openfoam_labels(origProcId_file, expected_count=len(d_vals))
        id_vals = [f"{p}_{id}" for p, id in zip(origProcId_vals, origId_vals)]
        df_tmp = pd.DataFrame({
            "t":  t_val,
            "x":  pos_vals[:,0],
            "y":  pos_vals[:,1],
            "z":  pos_vals[:,2],
            "d":  d_vals,
            "id": id_vals
        })
        lag_data_list.append(df_tmp)

df_lag_all = pd.concat(lag_data_list, ignore_index=True)

seen_ids = set() # set type for O(1) lookup speed
df_lag_list = []

for t_val, df_tmp in df_lag_all.groupby('t'):
    crossed_mask = (df_tmp['x'] >= plane_x) & (~df_tmp['id'].isin(seen_ids))
    df_new_crossed = df_tmp[crossed_mask]

    if not df_new_crossed.empty:
        df_lag_list.append(df_new_crossed)
        seen_ids.update(df_new_crossed['id'].tolist())

df_lag = pd.concat(df_lag_list, ignore_index=True)

df_lag['A'] = np.pi * df_lag['d']**2
df_lag['V'] = np.pi * df_lag['d']**3 / 6.0
df_lag['source'] = 'lagrangian'

#%% Calculate SMD

cols = ['t', 'A', 'V', 'source']
df = pd.concat([df_lag[cols], df_vof[cols]], ignore_index=True)

df_A_V_sum = df.groupby(['t'])[['V', 'A']].sum()
SMD = 6 * df_A_V_sum['V'] / df_A_V_sum['A']

df_A_V_sum_lag = df_lag.groupby(['t'])[['V', 'A']].sum()
SMD_lag = 6 * df_A_V_sum_lag['V'] / df_A_V_sum_lag['A']

df_A_V_sum_vof = df_vof.groupby(['t'])[['V', 'A']].sum()
SMD_vof = 6 * df_A_V_sum_vof['V'] / df_A_V_sum_vof['A']

scale = 1e6
plt.figure()
plt.plot(SMD.index, SMD * scale, '-o', label='Total SMD')
plt.plot(SMD_vof.index, SMD_vof * scale,'-s' ,label='VOF SMD')
plt.plot(SMD_lag.index, SMD_lag * scale, '-^', label='Lagrangian SMD')
plt.xlabel('$t$ [s]')
plt.ylabel(r'$d_{32}$ [$\mu$m]')
plt.title('Droplet Size Evolution ($d_{32}$)')
plt.minorticks_on()
plt.grid(which='major', color='#dbdada', linestyle='-', alpha=0.7)
plt.grid(which='minor', color='#dbdada', linestyle=':', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig("images/SMD_plot.png", dpi=300, bbox_inches="tight")
plt.show()

# %%
