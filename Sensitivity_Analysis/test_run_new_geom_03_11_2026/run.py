import os
import shutil
import subprocess
import re
from pathlib import Path
import math

case_dir = Path(__file__).parent.resolve()
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

    print("⏹️  Meshing full domain...")
    subprocess.run("snappyHexMesh -overwrite >> log.init 2>&1", shell=True, check=True)

    # print("📝 Creating cyclic patches.")
    # subprocess.run("createPatch -overwrite >> log.init 2>&1", shell=True, check=True)

    # print("📝 Set topo for cyclic faces")
    # subprocess.run("topoSet >> log.init 2>&1", shell=True, check=True)

    print("📝 Initializing fluid fraction")
    subprocess.run("setFields >> log.init 2>&1", shell=True, check=True)

    print("⚡ Decomposing into processors")
    subprocess.run("decomposePar >> log.init 2>&1", shell=True, check=True)
else: 
    print("Detected existing run, reading latest time")

print("🌟 Start time loop")
end_time = 0.005
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
        subprocess.run("topoSet -latestTime >> log.balance 2>&1", shell=True, check=True)
        subprocess.run(f"decomposePar -force -latestTime -case {str(case_dir)} >> log.balance", shell=True, check=True)

    if current_time < next_time - 1e-10:
        print("Detected abort: Terminating run")
        exit()
