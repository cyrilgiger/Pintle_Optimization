import os
import shutil
import subprocess
from pathlib import Path

case_dir = Path(__file__).parent.resolve()
os.chdir(case_dir)

print("📂 Created 0 dir copy")
if not os.path.isdir("0"): subprocess.run("cp -r 0.orig 0", shell=True, check=True)

print("📂 Extracting surface features")
subprocess.run("surfaceFeatureExtract > log.init 2>&1", shell=True, check=True)

print("⏹️  Creating background mesh")
subprocess.run("blockMesh >> log.init 2>&1", shell=True, check=True)

print("⏹️  Meshing full domain...")
subprocess.run("snappyHexMesh -overwrite >> log.init 2>&1", shell=True, check=True)

print("🔁 Replacing cyclic boundary patch type")
# Direct boundary file update in Python
boundary_path = case_dir / "constant/polyMesh/boundary"
boundary_text = boundary_path.read_text()
boundary_text = boundary_text.replace(
    "pintleDomain_periodic_0\n    {\n        type            patch;",
    """pintleDomain_periodic_0
    {
        type            symmetry;""",
)
boundary_text = boundary_text.replace(
    "pintleDomain_periodic_rev\n    {\n        type            patch;",
    """pintleDomain_periodic_rev
    {
        type            symmetry;""",
)
boundary_path.write_text(boundary_text)

print("📝 Set topo for cyldic faces")
subprocess.run("topoSet >> log.init 2>&1", shell=True, check=True)

print("📝 Initializing lox fraction")
subprocess.run("setFields >> log.init 2>&1", shell=True, check=True)

print("⚡ Decomposing into processors")
subprocess.run("decomposePar >> log.init 2>&1", shell=True, check=True)

print("🌟 Start time loop")
subprocess.run("mpirun -np 6 atomizationFoam -parallel > log.atomizationFoam 2>&1", shell=True, check=True)