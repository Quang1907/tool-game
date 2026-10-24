# MACOS SETUP & PERMISSIONS GUIDE

## 1. Prerequisites
- **Operating System:** macOS 13.0+ (Ventura, Sonoma, or Sequoia).
- **Architecture:** Apple Silicon (ARM64) or Intel (x86_64).
- **Homebrew:** Recommended for installing Python 3.11.

```bash
brew install python@3.11
```

---

## 2. Setting Up Virtual Environment
Run the automated setup script:
```bash
./scripts/setup_macos.sh
```

Or manually:
```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. macOS Screen Recording Permissions

When using Computer Vision to capture screen regions via the interactive selector:
macOS requires explicit **Screen Recording** permission for security and privacy.

### How to Grant Permission:
1. Open **System Settings** on your Mac.
2. Navigate to **Privacy & Security** -> **Screen Recording**.
3. Locate **Terminal** (or **iTerm2** / **Binh13Analyzer.app**).
4. Toggle the switch to **On**.
5. If prompted, click **Quit & Reopen** to apply the permissions.

*Note: The application only accesses screen pixels when you explicitly click the "Chụp vùng màn hình" button and drag the crosshair selector.*
