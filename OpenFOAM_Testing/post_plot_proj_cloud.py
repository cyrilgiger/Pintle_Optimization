#%% imports
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import re

%matplotlib widget

#%% Get particle (x,y,z) positions
# read helper
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
#____________________________________________________________________________

base_dir = Path(__file__).parent.resolve() / Path("run_openfoam_hex_amr/")
proc_dir_pattern = "processor*"

proc_dirs = [p for p in base_dir.glob(proc_dir_pattern)]

time_str = "0.00135"

# load particle positions
ppos_cart = []
for pdir in proc_dirs:
    lag_dir = pdir / Path(time_str) / Path("lagrangian/dropletCloud")
    if lag_dir.exists():
        pos_file = lag_dir / Path("positions")
        print(f"Reading file: {pos_file}")
        ppos_cart.append(read_openfoam_positions(pos_file))
    else:
        print(f"{pdir} contains no lagrangian directory")
        continue
ppos_cart = np.vstack(ppos_cart)

#%% Tranform to cylindrical coordinates

r_vec = np.sqrt(ppos_cart[:,1]**2 + ppos_cart[:,2]**2).T

ppos_proj = np.array([ppos_cart[:,0], r_vec]).T

plt.figure()
plt.scatter(ppos_proj[:, 0], ppos_proj[:, 1], s=3, label='Droplets', zorder=2)
plt.xlabel('Axial Position $x$ [m]')
plt.ylabel('Radial Position $r$ [m]')
plt.title(f'Droplet Cloud Projection ($r$ vs $x$) for {ppos_cart.shape[0]:,.0f} particles')
plt.minorticks_on()
plt.grid(which='major', color='#dbdada', linestyle='-', alpha=0.7)
plt.grid(which='minor', color='#dbdada', linestyle=':', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig("images/droplet_proj.png", dpi=300, bbox_inches="tight")
plt.show()

#%%
