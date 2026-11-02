import os
import shutil
from pathlib import Path

case_dir = Path(__file__).parent.resolve()
os.chdir(case_dir)

print("🧹 Cleaning OpenFOAM case directory...")

# 1. Remove processor directories (parallel runs)
for proc_dir in case_dir.glob("processor*"):
    if proc_dir.is_dir():
        shutil.rmtree(proc_dir)
        print(f"  - Removed: {proc_dir.name}")

# 2. Remove openfoam log files
for log_file in case_dir.glob("log.*"):
    if log_file.is_file():
        log_file.unlink()
        print(f"  - Removed: {log_file.name}")

# Remove slurm log files
for pattern in ("job_*.err", "job_*.log"):
    for log_file in case_dir.glob(pattern):
        if log_file.is_file():
            log_file.unlink()
            print(f"  - Removed: {log_file.name}")

# 3. Remove generated time directories (e.g. 0.001, 1, 2)
for item in case_dir.iterdir():
    if item.is_dir() and item.name not in ["0.orig", "constant", "system", ".git", ".venv", "__pycache__"]:
        try:
            float(item.name)
            shutil.rmtree(item)
            print(f"  - Removed time dir: {item.name}")
        except ValueError:
            pass

# 4. Remove post-processing, VTK, and dynamic code folders
extra_dirs = ["postProcessing", "VTK", "dynamicCode"]
for d in extra_dirs:
    target = case_dir / d
    if target.is_dir():
        shutil.rmtree(target)
        print(f"  - Removed: {d}")

# 5. Remove constant/polyMesh (rebuilt by blockMesh / snappyHexMesh)
poly_mesh = case_dir / "constant/polyMesh"
if poly_mesh.is_dir():
    shutil.rmtree(poly_mesh)
    print("  - Removed: constant/polyMesh")

# 6. Remove surfaceFeatureExtract artifacts (.eMesh / .extendedFeatureEdgeMesh)
tri_surface = case_dir / "constant/triSurface"
if tri_surface.is_dir():
    for e_mesh in tri_surface.glob("*.eMesh"):
        e_mesh.unlink()
        print(f"  - Removed: {e_mesh.name}")

ext_feature = case_dir / "constant/extendedFeatureEdgeMesh"
if ext_feature.is_dir():
    shutil.rmtree(ext_feature)
    print("  - Removed: constant/extendedFeatureEdgeMesh")

print("✨ Clean complete! Case is ready for a fresh run.")