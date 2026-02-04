import os
import shutil
import subprocess
import sys
from pathlib import Path


MAX_ONEFILE_SIZE = 15 * 1024 * 1024
MAX_ONEDIR_SIZE = 20 * 1024 * 1024


def run_pyinstaller(args: list[str]) -> None:
    result = subprocess.run(args, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def file_size(path: Path) -> int:
    return path.stat().st_size


def dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            total += Path(root, name).stat().st_size
    return total


def main() -> None:
    dist = Path("dist")
    if dist.exists():
        shutil.rmtree(dist)

    onefile_cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name",
        "VoiceCode",
        "voicecode/main.py",
    ]
    run_pyinstaller(onefile_cmd)

    exe_path = dist / "VoiceCode.exe"
    if exe_path.exists():
        size = file_size(exe_path)
        print(f"单文件体积: {size}")
        if size <= MAX_ONEFILE_SIZE:
            print("单文件打包成功")
            return

    onedir_cmd = [
        "pyinstaller",
        "--noconsole",
        "--onedir",
        "--name",
        "VoiceCode",
        "voicecode/main.py",
    ]
    run_pyinstaller(onedir_cmd)

    dir_path = dist / "VoiceCode"
    if dir_path.exists():
        size = dir_size(dir_path)
        print(f"目录体积: {size}")
        if size <= MAX_ONEDIR_SIZE:
            print("目录打包成功")
            return

    print("打包完成，但体积超出目标")
    sys.exit(1)


if __name__ == "__main__":
    main()
