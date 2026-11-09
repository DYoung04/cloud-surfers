"""Build a fresh Linux Lambda ZIP; never upload or overwrite existing artifacts.

Usage: .venv/bin/python scripts/package_lambda.py --application deployment/original_application.py
The supplied module must expose lambda_handler and the telemetry contract in deployment/DEPLOYMENT.md.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]


def stage_payload(build, application, model_dir):
    """Assemble runtime files while keeping the Lambda handler at the ZIP root."""
    shutil.copy2(BASE / "deployment/lambda_function.py", build / "lambda_function.py")
    shutil.copy2(application, build / "original_application.py")
    package = build / "runtime_detector"
    package.mkdir()
    for name in ("__init__.py", "detector.py", "invocation_counter.py"):
        shutil.copy2(BASE / "src/runtime_detector" / name, package / name)
    (build / "models").mkdir()
    for name in ("logistic_regression", "decision_tree", "scaler", "feature_names"):
        shutil.copy2(model_dir / f"{name}.joblib", build / "models" / f"{name}.joblib")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application", type=Path, default=BASE / "deployment/original_application.py")
    parser.add_argument("--model-dir", type=Path, default=BASE / "models/training_run_001")
    parser.add_argument("--architecture", choices=["x86_64", "arm64"], default="x86_64")
    args = parser.parse_args()
    if not args.application.is_file():
        parser.error("Provide the original AWS application's Python source file")
    if args.application.resolve() == BASE / "deployment/lambda_function.py":
        parser.error("The application must be the original handler, not the detector wrapper")
    for name in ("logistic_regression", "decision_tree", "scaler", "feature_names"):
        if not (args.model_dir / f"{name}.joblib").is_file():
            parser.error(f"Missing model artifact: {args.model_dir / name}")
    arch = "aarch64" if args.architecture == "arm64" else "x86_64"
    output_root = BASE / "dist"
    output_root.mkdir(exist_ok=True)
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    with tempfile.TemporaryDirectory(prefix="lambda-build-") as temporary:
        build = Path(temporary)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt"),
                        "--target", str(build), "--platform", f"manylinux_2_28_{arch}",
                        "--platform", f"manylinux2014_{arch}", "--implementation", "cp",
                        "--python-version", "3.14", "--only-binary=:all:", "--no-compile"], check=True)
        stage_payload(build, args.application, args.model_dir)
        files = [p for p in build.rglob("*") if p.is_file()]
        size = sum(p.stat().st_size for p in files)
        if size > 250 * 1024 * 1024:
            raise RuntimeError(f"Uncompressed package is {size / 1024**2:.1f} MiB; use a container image")
        output = output_root / f"runtime-detector-{args.architecture}-{run}.zip"
        with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(build))
        print(f"Created {output}\nUncompressed: {size / 1024**2:.1f} MiB")
        print(f"ZIP: {output.stat().st_size / 1024**2:.1f} MiB")
        if output.stat().st_size > 50 * 1024 * 1024:
            print("Upload through S3 (ZIP exceeds the 50 MiB direct-upload threshold).")
        print("No AWS deployment was performed.")


if __name__ == "__main__":
    main()
