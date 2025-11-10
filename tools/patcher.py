from __future__ import annotations
import sys, subprocess, shutil
from pathlib import Path

def apply_patch(patch_path: str) -> int:
    patch = Path(patch_path)
    if not patch.exists():
        print(f"✗ Patch not found: {patch}", file=sys.stderr); return 1
    if shutil.which("git") and (Path.cwd()/".git").exists():
        r = subprocess.run(["git","apply","--whitespace=fix",str(patch)])
        if r.returncode == 0:
            print("✓ Applied with git apply"); return 0
        else:
            print("git apply failed; trying patch(1)...", file=sys.stderr)
    if shutil.which("patch"):
        r = subprocess.run(["patch","-p0","-N","-r","patch.rej","-i",str(patch)])
        if r.returncode == 0: print("✓ Applied with patch(1)")
        return r.returncode
    print("✗ Neither git nor patch(1) available.", file=sys.stderr); return 2

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tools/patcher.py <diff>", file=sys.stderr); sys.exit(2)
    sys.exit(apply_patch(sys.argv[1]))
