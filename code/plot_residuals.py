import sys
import subprocess
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"

name = sys.argv[1]                      # e.g. airFoil2D
case = CASES_DIR / name

if not case.is_dir():
    sys.exit(f"Case not found: {case}")

# extract residuals from the log
subprocess.run(["foamLog", "log.simpleFoam"], cwd=case, check=True,
               stdout=subprocess.DEVNULL)

for field in ["Ux", "Uy", "p", "nuTilda"]:
    data = np.loadtxt(case / "logs" / f"{field}_0")
    plt.semilogy(data[:, 0], data[:, 1], label=field)

plt.title(name)
plt.xlabel("Iteration")
plt.ylabel("Initial residual")
plt.legend()
plt.grid(True, which="both", alpha=0.3)
plt.savefig(case / "residuals.png", dpi=150)
print(f"saved {case / 'residuals.png'}")