import os
import subprocess
import json
import hashlib
import shutil

DEBS_DIR = "debs"
DEPICTIONS_DIR = "depictions"
BASE_URL = "https://aimijian.github.io"

os.makedirs(DEPICTIONS_DIR, exist_ok=True)

for root, dirs, files in os.walk(DEPICTIONS_DIR):
    for f in files:
        if f != f.lower():
            old = os.path.join(root, f)
            new = os.path.join(root, f.lower())
            if not os.path.exists(new):
                shutil.move(old, new)

def compute_hashes(path):
    with open(path, "rb") as f:
        data = f.read()
    return (
        hashlib.md5(data).hexdigest(),
        hashlib.sha1(data).hexdigest(),
        hashlib.sha256(data).hexdigest()
    )

entries = []

for file in sorted(os.listdir(DEBS_DIR)):
    if not file.endswith(".deb"):
        continue

    path = os.path.join(DEBS_DIR, file)

    control = subprocess.check_output(
        ["dpkg-deb", "-f", path],
        text=True,
        errors="ignore"
    )

    package = None
    for line in control.splitlines():
        if line.lower().startswith("package:"):
            package = line.split(":", 1)[1].strip()

    if not package:
        continue

    pkg_dir = os.path.join(DEPICTIONS_DIR, package.lower())
    os.makedirs(pkg_dir, exist_ok=True)

    files_in_pkg = os.listdir(pkg_dir)

    screenshots = sorted([
        f for f in files_in_pkg
        if f.lower().startswith("screenshot") and f.lower().endswith(".png")
    ])

    header = None
    for f in files_in_pkg:
        if f.lower().startswith("header") and f.lower().endswith(".png"):
            header = f
            break

    depiction = {
        "class": "DepictionStackView",
        "views": []
    }

    if screenshots:
        depiction["views"].append({
            "class": "DepictionScreenshotsView",
            "itemSize": "{200, 415}",
            "itemCornerRadius": 20,
            "screenshots": [
                {
                    "url": f"{BASE_URL}/depictions/{package.lower()}/{s.lower()}",
                    "accessibilityText": f"Screenshot {i+1}"
                }
                for i, s in enumerate(screenshots)
            ]
        })

    if header:
        depiction["headerImage"] = f"{BASE_URL}/depictions/{package.lower()}/{header.lower()}"

    with open(os.path.join(pkg_dir, "depiction.json"), "w", encoding="utf-8") as f:
        json.dump(depiction, f, indent=2, ensure_ascii=False)

    size = os.path.getsize(path)
    md5sum, sha1sum, sha256sum = compute_hashes(path)

    entry = control.strip() + "\n"
    entry += f"Filename: debs/{file}\n"
    entry += f"Size: {size}\n"
    entry += f"MD5sum: {md5sum}\n"
    entry += f"SHA1: {sha1sum}\n"
    entry += f"SHA256: {sha256sum}\n"

    if screenshots or header:
        entry += f"Depiction: {BASE_URL}/depictions/{package.lower()}/depiction.json\n"
        entry += f"SileoDepiction: {BASE_URL}/depictions/{package.lower()}/depiction.json\n"

    entries.append(entry)

with open("Packages", "w", encoding="utf-8") as f:
    f.write("\n".join(entries))

os.system("gzip -kf Packages")
os.system("bzip2 -kf Packages")