"""Offline source integrity checks. Does not import external libraries or call APIs."""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "main.py", "agent_1_reader.py", "agent_2_analyst.py", "agent_3_critic.py", "utils.py",
    "experiments/vision/agent_1_screenshot.py", "experiments/vision/agent_2_classifier.py",
    "experiments/vision/test_1_2.py", "experiments/vision/view_results.py",
]

failures = []
for name in REQUIRED:
    path = ROOT / name
    if not path.is_file():
        failures.append(f"MISSING: {name}")
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        failures.append(f"INVALID SYNTAX: {name}: {exc}")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print(f"PASS: {len(REQUIRED)} source files present and syntactically valid. No runtime test performed.")
