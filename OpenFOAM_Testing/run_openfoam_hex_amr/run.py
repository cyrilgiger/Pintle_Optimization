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

    print("🔁 Replacing cyclic boundary patch type")
    boundary_path = case_dir / "constant/polyMesh/boundary"
    boundary_text = boundary_path.read_text()
    boundary_text = re.sub(
        r'(pintleDomain_periodic_0\s*\{\s*type\s+)patch;', r'\1symmetry;', boundary_text)
    boundary_text = re.sub(
        r'(pintleDomain_periodic_rev\s*\{\s*type\s+)patch;', r'\1symmetry;', boundary_text)
    boundary_path.write_text(boundary_text)

    print("📝 Set topo for cyldic faces")
    subprocess.run("topoSet >> log.init 2>&1", shell=True, check=True)

    print("📝 Initializing lox fraction")
    subprocess.run("setFields >> log.init 2>&1", shell=True, check=True)

    print("⚡ Decomposing into processors")
    subprocess.run("decomposePar >> log.init 2>&1", shell=True, check=True)
else: 
    print("Detected existing run, reading latest time")

print("🌟 Start time loop")
end_time = 0.002
balance_int = 5e-4
current_time = latest_time()
ctrl_dict = case_dir / "system/controlDict"
while current_time < end_time - 1e-10:
    if not ((current_time % balance_int) < 1e-7 or (balance_int - (current_time % balance_int)) < 1e-7):
        next_time = math.ceil(current_time / balance_int) * balance_int
        print(f"Detected unfinished iteration - continueing: {current_time:.3g} -> {next_time:.3g}")
    else:
        next_time = (round(current_time / balance_int) + 1) * balance_int

    subprocess.run(f"foamDictionary {str(ctrl_dict)} -entry endTime -set {next_time:.16g}", shell=True, check=True)
    subprocess.run("mpirun -np 6 atomizationFoam -parallel > log.atomizationFoam 2>&1", shell=True, check=True)
    current_time = latest_time()
    subprocess.run(f"reconstructParMesh -case {str(case_dir)} > log.balance 2>&1", shell=True, check=True)
    subprocess.run(f"reconstructPar -case {str(case_dir)} >> log.balance", shell=True, check=True)

    if current_time + balance_int < end_time - 1e-10:
        subprocess.run(f"decomposePar -force -case {str(case_dir)} >> log.balance", shell=True, check=True)

    if current_time < next_time - 1e-10:
        print("Detected abort: Terminating run")
        exit()


# # ---------------------------------------------------------
# import os
# import re
# import subprocess
# from pathlib import Path

# case_dir = Path(__file__).parent.resolve()
# control_dict = case_dir / "system/controlDict"
# end_time_marker = case_dir / ".redistribute_end_time"
# redistribute_interval = float(os.environ.get("REDISTRIBUTE_INTERVAL", "0.00005"))


# def foam_value(entry):
#     result = subprocess.run(
#         ["foamDictionary", str(control_dict), "-entry", entry, "-value"],
#         cwd=case_dir,
#         check=True,
#         capture_output=True,
#         text=True,
#     )
#     return result.stdout.strip().rstrip(";")


# def set_end_time(value):
#     subprocess.run(
#         ["foamDictionary", str(control_dict), "-entry", "endTime", "-set", f"{value:.16g}"],
#         cwd=case_dir,
#         check=True,
#     )


# def run_logged(command, log_path, mode="a"):
#     with log_path.open(mode) as log_file:
#         subprocess.run(
#             command,
#             cwd=case_dir,
#             stdout=log_file,
#             stderr=subprocess.STDOUT,
#             check=True,
#         )


# def numeric_times(directory):
#     times = []
#     for child in directory.iterdir():
#         if child.is_dir():
#             try:
#                 times.append(float(child.name))
#             except ValueError:
#                 pass
#     return times


# def latest_parallel_time(n_subdomains):
#     latest = []
#     for proc in range(n_subdomains):
#         proc_dir = case_dir / f"processor{proc}"
#         times = numeric_times(proc_dir)
#         if not times:
#             raise RuntimeError(f"No written time directories found in {proc_dir}")
#         latest.append(max(times))

#     tolerance = 1e-10
#     if max(latest) - min(latest) > tolerance:
#         raise RuntimeError(f"Processor latest times do not match: {latest}")
#     return max(latest)


# def prepare_fresh_case():
#     print("Preparing a fresh case")
#     if not (case_dir / "0").is_dir():
#         subprocess.run(["cp", "-r", "0.orig", "0"], cwd=case_dir, check=True)

#     log_init = case_dir / "log.init"
#     run_logged(["surfaceFeatureExtract"], log_init, "w")
#     run_logged(["blockMesh"], log_init)
#     run_logged(["snappyHexMesh", "-overwrite"], log_init)

#     boundary_path = case_dir / "constant/polyMesh/boundary"
#     boundary_text = boundary_path.read_text()
#     boundary_text = re.sub(
#         r'(pintleDomain_periodic_0\s*\{\s*type\s+)patch;', r'\1symmetry;', boundary_text)
#     boundary_text = re.sub(
#         r'(pintleDomain_periodic_rev\s*\{\s*type\s+)patch;', r'\1symmetry;', boundary_text)
#     boundary_path.write_text(boundary_text)

#     run_logged(["topoSet"], log_init)
#     run_logged(["setFields"], log_init)
#     run_logged(["decomposePar"], log_init)


# processor_dirs = list(case_dir.glob("processor[0-9]*"))
# has_parallel_mesh = (case_dir / "processor0/constant/polyMesh").is_dir()
# if processor_dirs and not has_parallel_mesh:
#     raise RuntimeError(
#         "Processor directories exist but processor0/constant/polyMesh is missing. "
#         "Inspect or clean the incomplete decomposition before running."
#     )
# if not has_parallel_mesh:
#     prepare_fresh_case()
# else:
#     print("Resuming the existing decomposed case")

# n_subdomains = 6
# write_interval = float(foam_value("writeInterval"))
# configured_end_time = float(foam_value("endTime"))

# if end_time_marker.exists():
#     final_end_time = float(end_time_marker.read_text().strip())
# else:
#     final_end_time = configured_end_time
#     end_time_marker.write_text(f"{final_end_time:.16g}\n")

# if redistribute_interval <= 0 or write_interval <= 0:
#     raise RuntimeError("REDISTRIBUTE_INTERVAL and writeInterval must be positive")

# for value, name in (
#     (redistribute_interval / write_interval, "REDISTRIBUTE_INTERVAL"),
#     (final_end_time / write_interval, "endTime"),
# ):
#     if abs(value - round(value)) > 1e-8:
#         raise RuntimeError(
#             f"{name} must be an integer multiple of writeInterval ({write_interval}) "
#             "so redistribution occurs only at written checkpoints."
#         )

# solver_log = case_dir / "log.atomizationFoam"
# current_time = latest_parallel_time(n_subdomains)
# if current_time >= final_end_time - 1e-10:
#     print(f"Case is already at endTime {final_end_time:g}")
#     end_time_marker.unlink(missing_ok=True)
# else:
#     while current_time < final_end_time - 1e-10:
#         next_boundary = (int(current_time / redistribute_interval + 1e-9) + 1)
#         segment_end = min(next_boundary * redistribute_interval, final_end_time)
#         print(f"Running solver from {current_time:g} to {segment_end:g}")
#         set_end_time(segment_end)
#         run_logged(["mpirun","-np", "6", "atomizationFoam", "-parallel"], solver_log)

#         written_time = latest_parallel_time(n_subdomains)
#         if abs(written_time - segment_end) > 1e-10:
#             raise RuntimeError(
#                 f"Solver stopped at {written_time:g}, not the requested checkpoint "
#                 f"{segment_end:g}; redistribution skipped."
#             )
#         current_time = written_time

#         if current_time < final_end_time - 1e-10:
#             print(f"Redistributing at checkpoint {current_time:g}")
#             run_logged(["reconstructParMesh", "-latestTime"], case_dir / "log.reconstruct")
#             run_logged(["reconstructPar", "-latestTime"], case_dir / "log.reconstruct")
#             run_logged(["decomposePar", "-force", "-latestTime"], case_dir / "log.reconstruct")

#     set_end_time(final_end_time)
#     end_time_marker.unlink(missing_ok=True)