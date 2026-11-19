import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "cases" / "airFoil2D"
CASES = ROOT / "cases"
U_MAG = 26.0
AOA_MIN, AOA_MAX = -5.0, 20.0


def ignore_results(folder, names):
    """Skip old results when copying the template."""
    skip = []
    for n in names:
        if n == "0.orig":
            continue
        if (n.replace(".", "").isdigit()          # time folders: 0, 50, 100...
                or n.startswith("processor")
                or n.startswith("log")
                or n in ("postProcessing", "logs")
                or n.endswith((".obj", ".png"))):
            skip.append(n)
    return skip


def make_case(aoa):
    """Copy the template and set the angle of attack."""
    case = CASES / f"aoa_{aoa:g}"
    if case.exists():
        shutil.rmtree(case)
    shutil.copytree(TEMPLATE, case, ignore=ignore_results)

    a = math.radians(aoa)

    u_file = case / "0.orig" / "U"
    u_file.write_text(re.sub(
        r"internalField\s+uniform\s+\([^)]*\);",
        f"internalField   uniform ({U_MAG*math.cos(a):.6f} {U_MAG*math.sin(a):.6f} 0);",
        u_file.read_text()))

    cd_file = case / "system" / "controlDict"
    text = cd_file.read_text()
    text = re.sub(r"liftDir\s+\([^)]*\);",
                  f"liftDir         ({-math.sin(a):.6f} {math.cos(a):.6f} 0);", text)
    text = re.sub(r"dragDir\s+\([^)]*\);",
                  f"dragDir         ({math.cos(a):.6f} {math.sin(a):.6f} 0);", text)
    cd_file.write_text(text)

    return case


def read_coeffs(case, last_n=50):
    """Average Cl/Cd over the last iterations and check they are stable."""
    path = case / "postProcessing" / "forceCoeffs" / "0" / "coefficient.dat"
    with open(path) as f:
        header = [l for l in f if l.startswith("#")][-1].lstrip("#").split()
    data = np.loadtxt(path, comments="#")

    cl_hist = data[:, header.index("Cl")]
    cd_hist = data[:, header.index("Cd")]
    cl, cd = cl_hist[-last_n:].mean(), cd_hist[-last_n:].mean()

    # converged if Cl barely moves over the last iterations
    cl_spread = cl_hist[-last_n:].max() - cl_hist[-last_n:].min()
    converged = cl_spread < 1e-3 * max(abs(cl), 1e-6) * 10

    return cl, cd, converged, len(data)


def run_case(aoa):
    """Build, run and evaluate one case. Returns a result dict."""
    if not AOA_MIN <= aoa <= AOA_MAX:
        return {"aoa": aoa, "status": "rejected",
                "error": f"aoa must be between {AOA_MIN} and {AOA_MAX}"}

    case = make_case(aoa)
    proc = subprocess.run(["./Allrun"], cwd=case,
                          capture_output=True, text=True)

    if proc.returncode != 0:
        return {"aoa": aoa, "status": "failed", "error": proc.stderr[-500:]}

    try:
        cl, cd, converged, iters = read_coeffs(case)
    except Exception as e:
        return {"aoa": aoa, "status": "failed", "error": str(e)}

    return {"aoa": aoa, "status": "ok", "cl": round(cl, 4), "cd": round(cd, 5),
            "l_d": round(cl / cd, 2), "converged": bool(converged),
            "iterations": iters}


if __name__ == "__main__":
    import db

    angles = [float(a) for a in sys.argv[1:]]
    study_id = db.start_study("manual", f"manual sweep {angles}")

    for aoa in angles:
        result = run_case(aoa)
        db.save_run(study_id, result)
        print(result)

    print(f"saved as study {study_id}")