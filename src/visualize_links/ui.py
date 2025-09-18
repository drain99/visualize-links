# Copyright (c) Indrajit Banerjee
# Licensed under the MIT License.

from pathlib import Path
import shutil
import sys
import subprocess
import webbrowser

# good enough heuristic...
def is_wsl():
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def main() -> int:
    index_file = Path(__file__).parent / "static" / "index.html"

    if is_wsl():
        print("Detected WSL environment...")
        if shutil.which("/usr/bin/wslpath") is None:
            print(f"wslpath not found, open manually: {index_file.resolve()}")
            return 1
        if shutil.which("/mnt/c/Windows/explorer.exe") is None:
            print(f"explorer.exe not found, open manually: {index_file.resolve()}")
            return 1

        win_uri = subprocess.check_output(["wslpath", "-w", str(index_file)], text=True)
        subprocess.run(["/mnt/c/Windows/explorer.exe", win_uri])
        return 0
    else:
        if webbrowser.open(index_file.as_uri()):
            return 0
        else:
            print(f"webbrowser open failed, open manually: {index_file.resolve()}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
