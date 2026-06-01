from __future__ import annotations

import json
import subprocess
import sys

from products.matrix.usb_distribution.build_usb_bundle import USB_DIR_NAME, build_bundle, smoke_bundle


def test_usb_bundle_builds_signed_offline_runtime(tmp_path):
    bundle = build_bundle(tmp_path)

    assert bundle.name == USB_DIR_NAME
    assert (bundle / "runtime" / "matrix_usb_runtime.py").exists()
    assert (bundle / "data" / "knowledge" / "manifest.json").exists()
    assert (bundle / "data" / "knowledge" / "packages" / "kpkg_admission_public_001.enc.json").exists()
    assert (bundle / "config" / "capability.policy.json").exists()
    assert (bundle / "checks" / "release-manifest.json").exists()

    release = json.loads((bundle / "checks" / "release-manifest.json").read_text())
    assert release["signature_alg"] == "ML-DSA-65"
    assert release["kem_alg"] == "ML-KEM-768"
    assert release["symmetric_alg"] == "AES-256-GCM"

    root_private_candidates = [
        path for path in (bundle / "keys").iterdir()
        if "root" in path.name.lower() and "DO_NOT" not in path.name
    ]
    assert root_private_candidates == []


def test_usb_runtime_verify_query_and_sync(tmp_path):
    bundle = build_bundle(tmp_path)
    report = smoke_bundle(bundle)
    assert report["status"] == "passed"

    runtime = bundle / "runtime" / "matrix_usb_runtime.py"
    proc = subprocess.run(
        [sys.executable, str(runtime), "query", "U盘分发包里不能放什么"],
        cwd=bundle,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["allowed"] is True
    assert "Root" in payload["answer"]

