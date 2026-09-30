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
plane_x = 25e-3  # only applied to lagrangian clouds !! for vof check controlDict/functions

#%% Import VOF stats on plane

vof_data_file = sim_dir / "postProcessing/plane_droplets.csv"
df_vof = pd.read_csv(vof_data_file)
df_vof['source'] = 'vof'

#%% Import Lagrangian stats
#____________________________________________________________________________________
# Helper Functions
def read_openfoam_positions(filepath):
    positions = []
    
    # Matches: (x y z) cell_id, including scientific notation like 4.25897e-05
    pattern = re.compile(r'\(\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)\s*\)\s*(\d+)')
    
    with open(filepath, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                x, y, z, _ = match.groups()
                positions.append([float(x), float(y), float(z)])
                
    return np.array(positions)

def read_openfoam_diameters(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Grab everything inside the data block starting after the list count
    match = re.search(r'\n\d+\s*\(\s*([\s\S]*?)\s*\)', content)
    if match:
        # np.fromstring automatically parses scientific notation and whitespace-separated numbers
        return np.fromstring(match.group(1), dtype=float, sep=' ')

    return np.array([])

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
        d_vals = read_openfoam_diameters(d_file)
        pos_vals = read_openfoam_positions(pos_file)
        df_tmp = pd.DataFrame({
            "t": t_val,
            "x": pos_vals[:,0],
            "y": pos_vals[:,1],
            "z": pos_vals[:,2],
            "d": d_vals,
        })
        lag_data_list.append(df_tmp)

df_lag_all = pd.concat(lag_data_list, ignore_index=True)

df_lag = df_lag_all[np.abs(df_lag_all['x'] - plane_x) < (df_lag_all['d'] / 2.0)]
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
plt.xlabel('$t$ [s]', fontsize=11)
plt.ylabel('$d_{32}$ [$\mu$m]', fontsize=11)
plt.title('Droplet Size Evolution ($d_{32}$)')
plt.minorticks_on()
plt.grid(which='major', color='#dbdada', linestyle='-', alpha=0.7)
plt.grid(which='minor', color='#dbdada', linestyle=':', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.show()

# %%
