---
title: 2026 04 09 Bubblewrap Twa
tags:
  - tecnico
prioridade: media
status: documentado
---
# Bubblewrap TWA Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the COTTE frontend installable as an Android App via Bubblewrap by providing a 512x512 PNG icon, updating the web app manifest, and ensuring the Digital Asset Links route is set up.

**Architecture:** We use Python Pillow to generate the `icon-512x512.png` and update `manifest.json`. The backend already has `/.well-known/assetlinks.json` in `sistema/app/main.py`.

**Tech Stack:** Python, Bubblewrap, FastAPI

---

### Task 1: Generate PNG Icon and Update Manifest

**Files:**
- Create: `sistema/cotte-frontend/icon-512x512.png`
- Modify: `sistema/cotte-frontend/manifest.json`

- [ ] **Step 1: Generate 512x512 PNG icon**

```bash
cat << 'PY_SCRIPT' > sistema/cotte-frontend/generate_icon.py
from PIL import Image, ImageDraw
img = Image.new('RGB', (512, 512), color = '#2563eb')
d = ImageDraw.Draw(img)
img.save('/home/gk/Projeto-izi/sistema/cotte-frontend/icon-512x512.png')
print("Success using PIL")
PY_SCRIPT
source sistema/venv/bin/activate && pip install Pillow && python3 sistema/cotte-frontend/generate_icon.py
```

- [ ] **Step 2: Update manifest.json with the PNG icon**

Verify or update `sistema/cotte-frontend/manifest.json` to include the PNG icon in the `icons` array:

```json
    {
      "src": "/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
```

### Task 2: Verify `/.well-known/assetlinks.json` endpoint

**Files:**
- Read: `sistema/app/main.py`

- [ ] **Step 1: Verify the endpoint exists**

```bash
cat sistema/app/main.py | grep -A 10 "\.well-known/assetlinks.json"
```

The route already exists in `sistema/app/main.py`:
```python
@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def get_assetlinks():
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "app.cotte.twa",  # Substitua pelo seu package name
                "sha256_cert_fingerprints": [
                    "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00"  # Substitua
                ]
            }
        }
    ]
```

### Task 3: Build using Bubblewrap CLI

**This task is meant for the user to run on their local machine or CI/CD environment.**

- [ ] **Step 1: Install Bubblewrap CLI**

```bash
npm install -g @bubblewrap/cli
```

- [ ] **Step 2: Initialize Bubblewrap Project**
*Run this in a new empty directory outside the codebase where you want to keep Android build files.*

```bash
mkdir -p /home/gk/cotte-android
cd /home/gk/cotte-android
bubblewrap init --manifest=https://app.cotte.com.br/manifest.json
```
*(Replace the URL with your actual production domain where the manifest is hosted).*

- [ ] **Step 3: Build the Application**

```bash
cd /home/gk/cotte-android
bubblewrap build
```

- [ ] **Step 4: Update Digital Asset Links**
The `bubblewrap build` command will output a SHA-256 fingerprint for your app signing key. You must update `sistema/app/main.py` -> `sha256_cert_fingerprints` with this value and deploy the backend again for the digital asset links verification to pass.
