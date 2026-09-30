#%% imports
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LinearRegression
import re
from IPython import get_ipython

ipython = get_ipython()
if ipython is not None:
    ipython.run_line_magic("matplotlib", "widget")

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

#%% Fit linear regression to get mean spray angle

x0 = 3e-3
r0 = 4e-3

x_s = (ppos_proj[:,0] - x0).reshape(-1,1)
r_s = ppos_proj[:,1] - r0

reg_s = LinearRegression(fit_intercept=False).fit(x_s, r_s)
xmax = np.max(ppos_proj[:,0])
x_fit = np.array([x0, xmax]).reshape(-1,1)
r_fit = reg_s.predict(x_fit - x0) + r0

th_m = np.arctan((r_fit[-1] - r_fit[0]) / (x_fit[-1] - x_fit[0]))

#%% 90th percentile regression

x_bins = np.linspace(0, xmax, 100)
x_c = (x_bins[1:] + x_bins[:-1])/2
r95 = []
x95 = []

for i in range(x_bins.shape[0] - 1):
    bin_mask = (ppos_proj[:,0] > x_bins[i]) & (ppos_proj[:,0] < x_bins[i+1])
    if sum(bin_mask) > 5:
        r95.append(np.percentile(ppos_proj[bin_mask, 1], 95))
        x95.append(x_c[i])

x95 = np.array(x95).reshape(-1,1)
r95 = np.array(r95).reshape(-1,1)

x95_s = x95 - x0
r95_s = r95 - r0

reg95_s = LinearRegression(fit_intercept=False).fit(x95_s, r95_s)
r95_fit = reg95_s.predict(x_fit - x0) + r0
th_95 = np.arctan((r95_fit[-1] - r95_fit[0]) / (x_fit[-1] - x_fit[0]))

plt.figure()
plt.scatter(ppos_proj[:, 0], ppos_proj[:, 1], s=3, label='Droplets', zorder=2)
plt.plot(x_fit, r_fit, color="red", label="Mean Regression")
plt.plot(x_fit, r95_fit, color="orange", label="95th Percentile Regression")
plt.xlabel('Axial Position $x$ [m]')
plt.ylabel('Radial Position $r$ [m]')
plt.title(f'Droplet Cloud Projection ($r$ vs $x$) for {ppos_cart.shape[0]:,.0f} particles')
plt.minorticks_on()
plt.grid(which='major', color='#dbdada', linestyle='-', alpha=0.7)
plt.grid(which='minor', color='#dbdada', linestyle=':', alpha=0.5)
text_str = (
    fr'$\theta_m: {np.rad2deg(th_m).item():.2f}^\circ$' '\n'
    fr'$\theta_{{95}}: {np.rad2deg(th_95).item():.2f}^\circ$')
plt.text(
    0.95, 0.05, 
    text_str, 
    transform=plt.gca().transAxes, 
    fontsize=10, 
    fontweight='bold',
    color="#000000",
    ha='right',   # Right-align text box to (0.95, 0.05)
    va='bottom',  # Bottom-align text box
    bbox=dict(
        facecolor='white', 
        alpha=0.85, 
        edgecolor='#dbdada', 
        boxstyle='round,pad=0.5'
    )
)
plt.legend(loc="upper left")
plt.gca().set_aspect('equal', adjustable='box')
plt.tight_layout()
plt.savefig("images/droplet_proj.png", dpi=300, bbox_inches="tight")
plt.show()

#%%
