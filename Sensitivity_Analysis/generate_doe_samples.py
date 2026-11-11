#%% imports
import os
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import qmc
from scipy.spatial import KDTree
from joblib import Parallel, delayed
from Functions.build_pintle_stl import build_pintle_stl
from Functions.lhs_fun import get_dim_from_non_dim, verify_physics

#%% inputs

# Fixed Parameters_________________________________________________________________________________

# Pintle Post Values
    # Overall dimensions
wpr = 0.15              # [-]    , Wall thickness to pintle ratio (2*w_p / D_p)
    # Fluid Guide 
tgr = 0.05              # [-]    , Top radius to guide radius ratio r_t / r_g
    # Orifices 
Cdo = 0.742             # [-]    , LOx orifices discharge coefficient (approx)
mdo = 1.57              # [kg/s] , LOx mass flow
roo = 1154.0            # [kg/m3], LOx density

# Fuel Values
Cdf = 0.873             # [-]    , Fuel annulus discharge coefficient
mdf = 1.01              # [kg/s] , Ethanol mass flow rate
rof = 810.0             # [kg/m3], Ethanol density

# Domain Dimensions 
L_d = 70.0e-3           # [m]    , Domain length
D_d = 110.85e-3         # [m]    , Domain diameter
L_x = 10.0e-3           # [m]    , extension of ox and f channels in -x

# Pressure Values
p_c = 20.0e5            # [Pa]   , Chamber pressure

# Design parameters______________________________________________________________________________
# Non-dimensionalized (x_min, x_max), marked by b_

d2rd = np.pi / 180.0 

# Pintle Post Values
    # Overall Dimensions
b_pcr = (0.15, 0.35)          # [-]  , Pintle diameter to chamber diameter ratio (D_p / D_d)
b_skd = (0.70, 1.30)          # [-]  , Skip distance (L_p / D_p)
    # Fluid Guide
b_a_i = (0.0, 35*d2rd)        # [rad], Guide injection angle
b_gpr = (0.01, 0.90)          # [-]  , Guide to pintle ratio (D_p / (2*r_g))
    # Orifice Dimensions and Values
b_N_o = (20, 40 + 1)          # [-]  , Number of orifices in each row (+ 1 to ensure equal bin widths with np.floor())
b_a_o = (0.0, 35*d2rd)        # [rad], Orifice angle
b_bf  = (0.40, 0.90)          # [-]  , Blockage factor
b_sar = (0.10, 0.70)          # [-]  , Slit area ratio
b_art = (1.00, 2.00)          # [-]  , Top orifice aspect ratio (l_t / w_t)
b_arb = (1.00, 2.00)          # [-]  , Bottom orifice aspect ratio (l_b / w_b)
b_rsl = (0.10, 0.25)          # [-]  , Row seperation distance to pintle length (d_r / L_p)

# Pressure Values
b_pdr = (0.15, 0.25)          # [-]  , Pressure drop to chamber pressure ratio (dp / p_c), input for t_a, target for dp_o

# Constraints and bounds___________________________________________________________________________

# Spray angle
b_thb = (50*d2rd, 70*d2rd)    # [rad], Target spray angle

# LHS options______________________________________________________________________________________
N_samp = 40             # [-]  , Target final number of samples (i.e. more samples will be generated initially to cover space and then downsampled)
verbose = False         # [-]  , Enables prints during LHS verification sweep - note due to parallel execution it's a bit messed up

#%% Preliminaries

# inputs to add to the lhs samples to fully define geometry
FIXED_INPUTS_GET_DIM = {
    "wpr": wpr,
    "tgr": tgr,
    "mdf": mdf,
    "rof": rof,
    "Cdf": Cdf,
    "D_d": D_d,
    "p_c": p_c,
    "L_d": L_d,
    "L_x": L_x,
}

# construction dict to get names and bounds arrays
B_DESIGN_VAR = {
    "pcr": b_pcr,
    "skd": b_skd,
    "a_i": b_a_i,
    "gpr": b_gpr,
    "N_o": b_N_o,
    "a_o": b_a_o,
    "bf" : b_bf,
    "sar": b_sar,
    "art": b_art,
    "arb": b_arb,
    "rsl": b_rsl,
    "pdr": b_pdr,
}
names_var  = tuple(B_DESIGN_VAR)
bounds_var = np.array([B_DESIGN_VAR[key] for key in B_DESIGN_VAR.keys()])

#%% Create LHS samples

lhc_sampler = qmc.LatinHypercube(d=len(names_var), optimization="random-cd")
samples_01 = lhc_sampler.random(n=N_samp * 100)
samples_sc = qmc.scale(sample=samples_01, l_bounds=bounds_var[:,0], u_bounds=bounds_var[:,1])

#%% Apply checks to samples and store

valid_records = []

def evaluate_sample(sample):
    # Run geometry and theoretical checks______________________________________
    d_des = dict(zip(names_var, sample, strict=True))
    d_des["N_o"] = int(np.clip(np.floor(d_des["N_o"]), b_N_o[0], b_N_o[1]))

    d_dim = get_dim_from_non_dim(**(FIXED_INPUTS_GET_DIM | d_des))

    d_phys = {"N_o": d_dim["N_o"], "w_t": d_dim["w_t"], "l_t": d_dim["l_t"], "w_b": d_dim["w_b"], "l_b": d_dim["l_b"],
              "Cdo": Cdo, "roo": roo, "mdo": mdo, "rof": rof, "mdf": mdf, "t_a": d_dim["t_a"],
              "D_p": d_dim["D_p"], "a_i": d_dim["a_i"], "b_pdr": b_pdr, "b_thb": b_thb, "p_c": p_c}

    passed_all, _, mssg = verify_physics(**d_phys)
    if not passed_all:
        if verbose: 
            for m in mssg: print(m)
        return None

    try: 
        build_pintle_stl(**d_dim, output_stl=None, verbose=False)
    except RuntimeError as exc:
        if verbose:
            print(f"Geometry FAILED: {str(exc)}")
        return None

    # Checks passed - store case as valid______________________________________
    # rename design non-dimensional entries for extra clarity
    record = {f"des_{k}": v for k, v in d_des.items()}

    # Add dimensional entries for building stl later
    record.update({f"geo_{k}": v for k, v in d_dim.items()})

    # Add fluidic inputs
    record.update({
        "Cdo": Cdo, "roo": roo, "mdo": mdo, 
        "rof": rof, "mdf": mdf, "p_c": p_c
    })

    return record

res_raw = Parallel(n_jobs=-1)(delayed(evaluate_sample)(sample) for sample in samples_sc)

#%% Post process samples

# Extract only valid samples
res = [row for row in res_raw if row is not None]

# Downsample samples to requested amount removing those with smallest minimum neighbor distance
    # Reextract design variables from res
X_des = np.array([[row[f"des_{k}"] for k in names_var] for row in res])
    # Un-scale them back to 0-1
X_norm = (X_des - bounds_var[:,0]) / (bounds_var[:,1] - bounds_var[:,0])

while len(res) > N_samp:
    tree = KDTree(X_norm)
    dist, _ = tree.query(X_norm, k=2) # k=2 calculates minumum neighbor distance as [dist_to_self, dist_to_nearest_neighbor]

    min_idx = np.argmin(dist[:,1])

    res.pop(min_idx)
    X_norm = np.delete(X_norm, min_idx, axis=0)

# Convert to data frame and add case identifier
df_res = pd.DataFrame(res)
df_res.insert(0, "case_id", [f"case_{i:04d}" for i in range(len(df_res))])
df_res.to_csv("case_data.csv", index=False)

#%% Test: generate stl s

parent_dir =  Path.cwd() / Path("stl")
parent_dir.mkdir(exist_ok=True)

# Dump the whole dataframe so we don't lose the case_id
cases = df_res.to_dict(orient="records")

for case in cases:
    case_id = case["case_id"]
    
    # Extract and clean up only the geometry parameters on the fly
    geo_dict = {k.removeprefix("geo_"): v for k, v in case.items() if k.startswith("geo_")}
    
    stl_path = parent_dir / f"{case_id}.stl"
    
    build_pintle_stl(**geo_dict, output_stl=stl_path, verbose=False)
