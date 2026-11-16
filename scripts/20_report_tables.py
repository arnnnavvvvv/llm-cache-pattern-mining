# report tables from logs and the environment: llm token use and cost, tool versions, machine details
import ctypes
import json
import os
import platform
import sys
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, storage

# gateway price per million tokens in inr (input, output), the same rates used when the judge was picked
RATES = {"claude-haiku-5.5": (9.90, 49.49), "claude-sonnet-5.5": (197.95, 989.75), "claude-opus-5.5": (395.90, 1979.50)}
ROLES = {"claude-sonnet-5.5": "reference judge (all labels)", "claude-haiku-5.5": "act tagging + judge candidate",
         "claude-opus-5.5": "judge candidate", "qwen/qwen3.8-27b": "act seed labels", "openai/gpt-oss-120b": "early judge tests",
         "openai/gpt-oss-20b": "early judge tests"}
PACKAGES = ["pandas", "numpy", "pyarrow", "datasets", "sentence-transformers", "torch", "faiss-cpu", "scikit-learn", "lightgbm",
            "mlxtend", "prefixspan", "matplotlib", "fastapi", "uvicorn", "anthropic", "groq", "streamlit", "altair",
            "python-docx", "python-pptx", "playwright", "pytest", "joblib", "pyyaml"]


# calls, tokens and cost per model, summed from every cached response on disk
def llm_costs() -> pd.DataFrame:
    rows = []
    for folder in sorted(config.path("llm_cache").iterdir()):
        used = [json.loads(f.read_text(encoding="utf-8")).get("usage", {}) for f in folder.glob("*.json")]
        model = folder.name.replace("_", "/", 1) if not folder.name.startswith("claude") else folder.name
        tin, tout = sum(u.get("input", 0) for u in used), sum(u.get("output", 0) for u in used)
        p_in, p_out = RATES.get(model, (0.0, 0.0))
        rows.append({"model": model, "role": ROLES.get(model, ""), "calls": len(used), "input_tokens": tin, "output_tokens": tout,
                     "provider": "prepaid gateway" if model in RATES else "free tier (usage not metered)",
                     "cost_inr": round((tin * p_in + tout * p_out) / 1e6, 2)})
    return pd.DataFrame(rows)


# installed version of every library the pipeline, service, demo and report use
def tool_versions() -> pd.DataFrame:
    rows = [{"tool": "Python", "version": platform.python_version()}]
    for p in PACKAGES:
        try:
            rows.append({"tool": p, "version": metadata.version(p)})
        except metadata.PackageNotFoundError:
            pass
    return pd.DataFrame(rows)


# total physical memory in gb on windows, read through the win32 api
def memory_gb() -> float:
    class Status(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    s = Status()
    s.dwLength = ctypes.sizeof(Status)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    return round(s.ullTotalPhys / 1024 ** 3, 1)


# machine the whole project ran on, plus the size of the data it produced
def machine() -> dict:
    import subprocess

    cpu = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                         capture_output=True, text=True).stdout.strip()
    work = config.path("work")
    data_mb = sum(f.stat().st_size for f in work.rglob("*") if f.is_file()) / 1024 ** 2
    return {"cpu": cpu, "logical_cores": os.cpu_count(), "ram_gb": memory_gb(), "gpu": "none used",
            "os": f"Windows {11 if int(platform.version().split('.')[-1]) >= 22000 else 10} (build {platform.version()})",
            "python": platform.python_version(),
            "work_tables_mb": round(data_mb, 1), "turns": int(len(storage.load("turns")))}


# writes all three tables
def main():
    costs = llm_costs()
    storage.save_result(costs, "llm_usage_cost")
    storage.save_result(tool_versions(), "tool_versions")
    storage.save_json(machine(), "machine")
    print(costs.to_string(index=False))
    print("total inr", costs["cost_inr"].sum())


if __name__ == "__main__":
    main()
