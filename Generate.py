import os
import subprocess
import json
import hashlib
import shutil

DEBS_DIR = "debs"
DEPICTIONS_DIR = "depictions"
BASE_URL = "https://aimijian.github.io"

if not os.path.exists(DEPICTIONS_DIR):
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

def safe_control(path):
    out = subprocess.check_output(
        ["dpkg-deb", "-f", path],
        text=True,
        errors="ignore"
    )

    data = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k and v:
                data[k] = v
    return data

entries = []

for file in sorted(os.listdir(DEBS_DIR)):
    if not file.endswith(".deb"):
        continue

    path = os.path.join(DEBS_DIR, file)
    control = safe_control(path)

    package = control.get("Package", "").strip()
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

    entry = []
    entry.append(f"Package: {package}")

    if "Name" in control:
        entry.append(f"Name: {control['Name']}")

    if "Version" in control:
        entry.append(f"Version: {control['Version']}")

    if "Architecture" in control:
        entry.append(f"Architecture: {control['Architecture']}")

    if "Maintainer" in control:
        entry.append(f"Maintainer: {control['Maintainer']}")

    if "Author" in control:
        entry.append(f"Author: {control['Author']}")

    if "Description" in control:
        entry.append(f"Description: {control['Description']}")

    if "Depends" in control:
        entry.append(f"Depends: {control['Depends']}")

    entry.append(f"Filename: debs/{file}")
    entry.append(f"Size: {size}")
    entry.append(f"MD5sum: {md5sum}")
    entry.append(f"SHA1: {sha1sum}")
    entry.append(f"SHA256: {sha256sum}")

    if screenshots or header:
        entry.append(f"Depiction: {BASE_URL}/depictions/{package.lower()}/depiction.json")
        entry.append(f"SileoDepiction: {BASE_URL}/depictions/{package.lower()}/depiction.json")

    entry.append("")

    entries.append("\n".join(entry))

with open("Packages", "w", encoding="utf-8") as f:
    f.write("\n".join(entries))

os.system("rm -f Packages.gz Packages.bz2")
os.system("gzip -c Packages > Packages.gz")
os.system("bzip2 -c Packages > Packages.bz2")