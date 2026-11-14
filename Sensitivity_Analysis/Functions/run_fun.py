# imports
import os
import sys
import math
import logging
import shutil
import subprocess
import numpy as np
from pathlib import Path
# from Functions.build_pintle_stl import build_pintle_stl

logger = logging.getLogger(__name__)

def prepare_case(str_case_id: str, d_case: dict, base_dir: Path):

    # Create run directory and copy contents from base case________________________________________
    case_dir  = base_dir / Path(str_case_id)
    base_case = base_dir / Path("case_xxxx")
    if case_dir.exists():
        shutil.rmtree(case_dir)

    shutil.copytree(base_case, case_dir)

    logger.info("Created case directory %s", case_dir)


    # Copy STL____________________________________________________________________________________
    d_geo = {k.removeprefix("geo_"): v for k, v in d_case.items() if k.startswith("geo_")}
    stl_path = case_dir / "constant/triSurface" / "pintle.stl"
    # _, rev_angle = build_pintle_stl(**d_geo, output_stl=stl_path)
    shutil.copy2(base_dir / "stl" / f"{str_case_id}.stl", stl_path)

    phi_seg = 2*np.pi / d_geo["N_o"]
    N_seg = np.floor(np.pi/2 / phi_seg)
    rev_angle = N_seg * phi_seg

    logger.info("Created STL at: %s", stl_path)


    # Modify mass flow inlet values________________________________________________________________
    mdo_cfd = d_case["mdo"] * rev_angle / (2*np.pi)
    mdf_cfd = np.sqrt(d_case["roo"] / d_case["rof"]) * d_case["mdf"] * rev_angle / (2*np.pi)

    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField/fluidDomain_inlet_o/massFlowRate -set 'constant {mdo_cfd:.5f}'",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField/fluidDomain_inlet_o/rhoInlet -set {d_case['roo']:.5f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField/fluidDomain_inlet_f/massFlowRate -set 'constant {mdf_cfd:.5f}'",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField/fluidDomain_inlet_f/rhoInlet -set {d_case['roo']:.5f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)

    logger.info(
        "Modified mass flow rates to: mdo_cfd: %.3f, mdf_cfd: %.3f "
        "due to rev_angle: %.2f",
        mdo_cfd,
        mdf_cfd,
        rev_angle,
    )
    

    # Modify fluid properties as entered___________________________________________________________
    subprocess.run(f"foamDictionary constant/transportProperties -entry fluid.rho -set {d_case['roo']:.5f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)

    logger.info("Modified fluid properties: fluid rho: %.3f", d_case['roo'])


    # Modify block mesh dict to the correct wedge and diameter_____________________________________
    write_block_mesh_dict(case_dir=case_dir, rev_angle=rev_angle, r_out=d_geo["D_d"]/2+1e-2, x_min=-d_geo["L_x"]-1e-2, x_max=d_geo["L_d"]+1e-2, r_in=0.3*d_geo["D_d"]/2)


    # Modify fluid domain intialization____________________________________________________________
    v_f_cfd = (np.sqrt(d_case["roo"] / d_case["rof"]) * d_case["mdf"]) / (d_case["roo"] * np.pi * d_geo["t_a"] * (d_geo["D_p"] + d_geo["t_a"]))
    v_p_cfd = d_case["mdo"] / (d_case["roo"] * 0.25 * np.pi * (d_geo["D_p"] - 2 * d_geo["w_p"])**2)     # fluid plug velocity in pintle (not ox. injection)

    x_p = (1 - v_p_cfd / v_f_cfd) * d_geo["L_p"]
    x_p = np.clip(x_p, 0, d_geo["L_p"])
    r_cyl1 = d_geo["D_p"] / 2 - d_geo["w_p"] + 0.5e-3
    r_cyl2 = d_geo["D_p"] / 2 + d_geo["t_a"] + 0.5e-3

    cmds = [
        ["foamDictionary", "system/setFieldsDict", "-entry", "cyl1_p2", "-set", f"({x_p:.4g} 0 0)"],
        ["foamDictionary", "system/setFieldsDict", "-entry", "cyl1_radius", "-set", f"{r_cyl1:.4g}"],
        ["foamDictionary", "system/setFieldsDict", "-entry", "cyl2_radius", "-set", f"{r_cyl2:.4g}"],
    ]
    for cmd in cmds:
        try:
            subprocess.run(cmd, cwd=case_dir, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error("foamDictionary failed (%s): %s", " ".join(cmd), e.stderr.strip())
            raise

    logger.info(
        "Modified fluid domain initialization to: x_p: %.2g with "
        "v_f_cfd: %.2g, v_p_cfd: %.2g",
        x_p,
        v_f_cfd,
        v_p_cfd,
    )

def write_block_mesh_dict(case_dir: Path, rev_angle: float, r_out: float, x_min: float, x_max: float, r_in: float):
    c, s = np.cos, np.sin
    t = rev_angle

    # Inner core (0, theta, and vector sum corner)
    y1, z1 = r_in, 0.0
    y3, z3 = r_in * c(t), r_in * s(t)
    y2, z2 = y1 + y3, z1 + z3

    # Outer wall (0, theta/2, theta)
    y4, z4 = r_out, 0.0
    y5, z5 = r_out * c(0.5 * t), r_out * s(0.5 * t)
    y6, z6 = r_out * c(t), r_out * s(t)

    # Outer arc midpoints (theta/4, 3*theta/4)
    ya1, za1 = r_out * c(0.25 * t), r_out * s(0.25 * t)
    ya2, za2 = r_out * c(0.75 * t), r_out * s(0.75 * t)

    content = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}

scale   1;

vertices
(
    // --- Inlet Face Extended (x = {x_min:.6f}) ---
    ({x_min:.6f}  {0.0:.6f}  {0.0:.6f})  // 0
    ({x_min:.6f}  {y1:.6f}  {z1:.6f})  // 1
    ({x_min:.6f}  {y2:.6f}  {z2:.6f})  // 2
    ({x_min:.6f}  {y3:.6f}  {z3:.6f})  // 3
    ({x_min:.6f}  {y4:.6f}  {z4:.6f})  // 4
    ({x_min:.6f}  {y5:.6f}  {z5:.6f})  // 5
    ({x_min:.6f}  {y6:.6f}  {z6:.6f})  // 6

    // --- Outlet Face Extended (x = {x_max:.6f}) ---
    ({x_max:.6f}  {0.0:.6f}  {0.0:.6f})  // 7
    ({x_max:.6f}  {y1:.6f}  {z1:.6f})  // 8
    ({x_max:.6f}  {y2:.6f}  {z2:.6f})  // 9
    ({x_max:.6f}  {y3:.6f}  {z3:.6f})  // 10
    ({x_max:.6f}  {y4:.6f}  {z4:.6f})  // 11
    ({x_max:.6f}  {y5:.6f}  {z5:.6f})  // 12
    ({x_max:.6f}  {y6:.6f}  {z6:.6f})  // 13
);

blocks
(
    hex (0 1 2 3 7 8 9 10) (12 12 48) simpleGrading (1 1 1)
    hex (1 4 5 2 8 11 12 9) (18 12 48) simpleGrading (1 1 1)
    hex (2 5 6 3 9 12 13 10) (18 12 48) simpleGrading (1 1 1)
);

edges
(
    arc 4 5 ({x_min:.6f}  {ya1:.6f}  {za1:.6f})
    arc 5 6 ({x_min:.6f}  {ya2:.6f}  {za2:.6f})

    arc 11 12 ({x_max:.6f}  {ya1:.6f}  {za1:.6f})
    arc 12 13 ({x_max:.6f}  {ya2:.6f}  {za2:.6f})
);

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 3 2 1)
            (1 2 5 4)
            (2 3 6 5)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (7 8 9 10)
            (8 11 12 9)
            (9 12 13 10)
        );
    }}
    periodic_0
    {{
        type symmetry;
        faces
        (
            (0 1 8 7)
            (1 4 11 8)
        );
    }}
    periodic_rev
    {{
        type symmetry;
        faces
        (
            (0 7 10 3)
            (3 10 13 6)
        );
    }}
    outerWall
    {{
        type wall;
        faces
        (
            (4 11 12 5)
            (5 12 13 6)
        );
    }}
);

mergePatchPairs
(
);
"""
    (case_dir / "system" / "blockMeshDict").write_text(content)


#################################################################################################################################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
#################################################################################################################################

def run_case(str_case_id: str, base_dir: Path):

    case_dir  = base_dir / Path(str_case_id)
    os.chdir(case_dir)

    #_____________________________________________________________________________________
    # Helper functions
    def latest_time():
        proc_dir = case_dir / "processor0"
        times = numeric_times(proc_dir)
        if not times:
            raise RuntimeError(f"No written time directories found in {proc_dir}")
        return max(times)

    def numeric_times(directory):
        times = []
        for child in directory.iterdir():
            if child.is_dir():
                try:
                    times.append(float(child.name))
                except ValueError:
                    pass
        return times
    #_____________________________________________________________________________________

    if not (case_dir / "processor0").is_dir():
        print("📂 Created 0 dir copy")
        if not os.path.isdir("0"): subprocess.run("cp -r 0.orig 0", shell=True, check=True)

        print("📂 Extracting surface features")
        subprocess.run("surfaceFeatureExtract > log.init 2>&1", shell=True, check=True)

        print("⏹️  Creating background mesh")
        subprocess.run("blockMesh >> log.init 2>&1", shell=True, check=True)

        print("🔪 Decomposing for parallel meshing")
        subprocess.run("decomposePar -no-fields >> log.init 2>&1", shell=True, check=True)

        print("🚀 Meshing full domain (parallel)...")
        subprocess.run("srun snappyHexMesh -overwrite -parallel >> log.init 2>&1", shell=True, check=True)

        print("🧩 Reconstructing the mesh")
        subprocess.run("reconstructParMesh -constant >> log.init 2>&1", shell=True, check=True)

        # print("📝 Creating cyclic patches.")
        # subprocess.run("createPatch -overwrite >> log.init 2>&1", shell=True, check=True)

        # print("📝 Set topo for cyclic faces")
        # subprocess.run("topoSet >> log.init 2>&1", shell=True, check=True)

        print("📝 Initializing fluid fraction")
        subprocess.run("setFields >> log.init 2>&1", shell=True, check=True)

        print("🔪 Distributing initial fields to the existing processor meshes")
        subprocess.run("decomposePar -force -fields >> log.init 2>&1", shell=True, check=True)
    else: 
        print("Detected existing run, reading latest time")

    print("🌟 Start time loop")
    end_time = 0.006
    balance_int = 10e-4
    current_time = latest_time()
    ctrl_dict = case_dir / "system/controlDict"

    while current_time < end_time - 1e-10:

        if not ((current_time % balance_int) < 1e-7 or (balance_int - (current_time % balance_int)) < 1e-7):
            next_time = math.ceil(current_time / balance_int) * balance_int
            print(f"Detected unfinished iteration - continueing: {current_time:.3g} -> {next_time:.3g}")
        else:
            next_time = (round(current_time / balance_int) + 1) * balance_int

        subprocess.run(f"foamDictionary {str(ctrl_dict)} -entry endTime -set {next_time:.16g}", shell=True, check=True)
        subprocess.run("srun atomizationFoam -parallel > log.atomizationFoam 2>&1", shell=True, check=True)
        current_time = latest_time()
        subprocess.run(f"reconstructParMesh -case {str(case_dir)} > log.balance 2>&1", shell=True, check=True)
        subprocess.run(f"reconstructPar -case {str(case_dir)} >> log.balance", shell=True, check=True)

        if current_time < end_time - 1e-10:
            # subprocess.run("topoSet -latestTime >> log.balance 2>&1", shell=True, check=True)
            subprocess.run(f"decomposePar -force -latestTime -case {str(case_dir)} >> log.balance", shell=True, check=True)

        if current_time < next_time - 1e-10:
            print("Detected abort: Terminating run")
            sys.exit(1)