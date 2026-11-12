# imports
import os
import math
import logging
import shutil
import subprocess
import numpy as np
import pandas as pd
from pathlib import Path
from Functions.build_pintle_stl import build_pintle_stl

logger = logging.getLogger(__name__)


def prepare_case(str_case_id: str, d_case: dict, base_dir: Path):

    # Create run direcotry and copy contents from base case________________________________________
    case_dir  = base_dir / Path(str_case_id)
    base_case = base_dir / Path("case_xxxx")
    shutil.copytree(base_case, case_dir)

    logger.info("Created case directory %s", case_dir)

    # Build STL____________________________________________________________________________________
    d_geo = {k.removeprefix("geo_"): v for k, v in d_case.items() if k.startswith("geo_")}
    stl_path = case_dir / "constant/triSurface" / "pintle.stl"
    _, rev_angle = build_pintle_stl(**d_geo, output_stl=stl_path)

    logger.info("Created STL at: %s", stl_path)

    # Modify mass flow inlet values________________________________________________________________
    mdo_cfd = d_case["mdo"] * rev_angle / (2*np.pi)
    mdf_cfd = np.sqrt(d_case["roo"] / d_case["rof"]) * d_case["mdf"] * rev_angle / (2*np.pi)

    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField.fluidDomain_inlet_o.massFlowRate -set 'constant {mdo_cfd:.5f}'",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField.fluidDomain_inlet_o.rhoInlet -set {d_case["roo"]:.5f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField.fluidDomain_inlet_f.massFlowRate -set 'constant {mdf_cfd:.5f}'",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary 0.orig/U -entry boundaryField.fluidDomain_inlet_f.rhoInlet -set {d_case["roo"]:.5f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)

    logger.info(
        "Modified mass flow rates to: mdo_cfd: %.3f, mdf_cfd: %.3f "
        "due to rev_angle: %.2f",
        mdo_cfd,
        mdf_cfd,
        rev_angle,
    )

    # Modify fluid properties as entered___________________________________________________________
    subprocess.run(f"foamDictionary constant/transportProperties -entry fluid.rho -set {d_case["roo"]:.5f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)

    logger.info("Modified fluid properties: fluid rho: %.3f", d_case["roo"])

    # Modify fluid domain intialization____________________________________________________________
    v_f_cfd = np.sqrt(d_case["roo"] / d_case["rof"]) * d_case["mdf"] / (d_case["rof"] * np.pi * d_geo["t_a"] * (d_geo["D_p"] + d_geo["t_a"]))
    v_p_cfd = d_case["mdo"] / (d_case["roo"] * 0.25 * np.pi * d_geo["D_p"]**2)     # fluid plug velocity in pintle (not ox. injection)

    x_p = (1 - v_p_cfd / v_f_cfd) * d_geo["L_p"]
    subprocess.run(f"foamDictionary system/setFieldsDict -entry cyl1_p2 -set {x_p:.4f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary system/setFieldsDict -entry cyl1_radius -set {d_geo["D_p"]/2 - d_geo["w_p"]:.4f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)
    subprocess.run(f"foamDictionary system/setFieldsDict -entry cyl1_radius -set {d_geo["D_p"]/2 + d_geo["t_a"]:.4f}",
                    cwd=case_dir, shell=True, check=True, capture_output=True)

    logger.info(
        "Modified fluid domain initialization to: x_p: %.2g with "
        "v_f_cfd: %.2g, v_p_cfd: %.2g",
        x_p,
        v_f_cfd,
        v_p_cfd,
    )

#################################################################################################################################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
#################################################################################################################################

def run_case(str_case_id: str, base_dir: Path):

    case_dir  = base_dir / Path(str_case_id)

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
        logger.info("📂 Created 0 dir copy")
        if not os.path.isdir("0"): subprocess.run("cp -r 0.orig 0", shell=True, check=True)

        logger.info("📂 Extracting surface features")
        subprocess.run("surfaceFeatureExtract > log.init 2>&1", shell=True, check=True)

        logger.info("⏹️  Creating background mesh")
        subprocess.run("blockMesh >> log.init 2>&1", shell=True, check=True)

        logger.info("🔪 Decomposing for parallel meshing")
        subprocess.run("decomposePar >> log.init 2>&1", shell=True, check=True)

        logger.info("🚀 Meshing full domain (parallel)...")
        # Using srun since you are on a SLURM cluster. Ensure decomposeParDict matches your SLURM task count.
        subprocess.run("srun snappyHexMesh -overwrite -parallel >> log.init 2>&1", shell=True, check=True)

        logger.info("🧩 Reconstructing the mesh")
        subprocess.run("reconstructParMesh -constant >> log.init 2>&1", shell=True, check=True)

        logger.info("🧹 Cleaning up meshing processors")
        subprocess.run("rm -rf processor*", shell=True, check=True)

        # logger.info("📝 Creating cyclic patches.")
        # subprocess.run("createPatch -overwrite >> log.init 2>&1", shell=True, check=True)

        # logger.info("📝 Set topo for cyclic faces")
        # subprocess.run("topoSet >> log.init 2>&1", shell=True, check=True)

        logger.info("📝 Initializing fluid fraction")
        subprocess.run("setFields >> log.init 2>&1", shell=True, check=True)

        logger.info("⚡ Decomposing into processors for solver")
        subprocess.run("decomposePar >> log.init 2>&1", shell=True, check=True)
    else: 
        logger.info("Detected existing run, reading latest time")

    logger.info("🌟 Start time loop")
    end_time = 0.005
    balance_int = 10e-4
    current_time = latest_time()
    ctrl_dict = case_dir / "system/controlDict"

    while current_time < end_time - 1e-10:

        if not ((current_time % balance_int) < 1e-7 or (balance_int - (current_time % balance_int)) < 1e-7):
            next_time = math.ceil(current_time / balance_int) * balance_int
            logger.info(f"Detected unfinished iteration - continueing: {current_time:.3g} -> {next_time:.3g}")
        else:
            next_time = (round(current_time / balance_int) + 1) * balance_int
            logger.info(f"Finished iteration - next time: {next_time:.3g}")

        subprocess.run(f"foamDictionary {str(ctrl_dict)} -entry endTime -set {next_time:.16g}", shell=True, check=True)
        subprocess.run("srun atomizationFoam -parallel > log.atomizationFoam 2>&1", shell=True, check=True)
        current_time = latest_time()
        subprocess.run(f"reconstructParMesh -case {str(case_dir)} > log.balance 2>&1", shell=True, check=True)
        subprocess.run(f"reconstructPar -case {str(case_dir)} >> log.balance", shell=True, check=True)

        if current_time < end_time - 1e-10:
            subprocess.run("topoSet -latestTime >> log.balance 2>&1", shell=True, check=True)
            subprocess.run(f"decomposePar -force -latestTime -case {str(case_dir)} >> log.balance", shell=True, check=True)

        if current_time < next_time - 1e-10:
            logger.info("Detected abort: Terminating run")
            exit()