# Computer Vision Pipeline & macOS Screen Capture Guide

## 1. Overview
The **Binh 13 Analyzer Vision System** provides end-to-end screen capture, image import, preprocessing, card detection, and card recognition without requiring game memory access, hooks, or external network services.

```
[Screen Capture / Image File]
            │
            ▼
[Image Preprocessor (CLAHE, Adaptive Threshold, Grayscale)]
            │
            ▼
[Card Detector (Contours / Horizontal Strip 13 / 3-Row Grid 3-5-5)]
            │
            ▼
[Card Recognizer]
   ├─ Multi-scale Template Matching (Ranks: A, 2-10, J, Q, K)
   ├─ HSV Color Classification (Red vs. Black)
   └─ Multi-scale Suit Matching (♠ Spades, ♣ Clubs, ♦ Diamonds, ♥ Hearts)
            │
            ▼
[Recognition Validator (13 Unique Cards, Duplicate Detection)]
            │
            ▼
[Interactive Zoomable Viewer & Manual Card Correction Dialog]
            │
            ▼
[Binh 13 3-5-5 Combinatorial Solver & Monte Carlo Engine]
```

---

## 2. macOS Screen Capture & Permissions

### Capture Mechanisms
- **Native CLI (`screencapture`)**:
  - `screencapture -i -s -r <path>`: Interactive arbitrary region drag-and-crop.
  - `screencapture -i -w -o <path>`: Window selection mode (targets Chrome, Safari, Edge, Games, or desktop applications without drop shadows).
  - `screencapture -D <display_id> <path>`: Multi-monitor full-screen capture for any connected display.
- **Python Fallbacks**:
  - `mss` multi-monitor capture with bounding box cropping.
  - Pillow `ImageGrab`.

### macOS Screen Recording Permission
macOS (Sonoma, Sequoia, etc.) enforces strict Screen Recording permissions in TCC:
- If permission is denied or missing, macOS returns an **all-black screenshot**.
- The vision pipeline automatically detects this via `img.size > 0 and np.max(img) == 0`.
- Users receive a clear diagnostic prompt guiding them to:
  `System Settings` → `Privacy & Security` → `Screen Recording` → Enable terminal / app.

---

## 3. Handling Retina & High-DPI Displays
- Logical coordinates (points) on macOS Retina displays correspond to 2x physical pixels.
- The `ZoomableImageViewer` preserves the full raw physical resolution (`QImage.Format_RGB888`) without downsampling prior to recognition.
- Interactive zooming (scroll wheel, `+`, `-`, 1:1, Fit to View) and click-and-drag panning allow inspecting individual card corners and suits without image distortion.

---

## 4. Multi-Strategy Card Detection
1. **Contour Detection**:
   - Adaptive thresholding + morphology (`cv2.morphologyEx`) to locate individual card quadrilaterals.
   - Filtered by card aspect ratio ($\approx 1.2$ to $1.6$) and area thresholds.
2. **Horizontal 13-Card Strip Slicing (`slice_horizontal_row`)**:
   - Ideal for mobile / web poker layouts where 13 cards are arranged side-by-side in a single hand bar with slight overlap.
3. **3-Row Grid Slicing (`slice_three_rows_grid`)**:
   - Ideal for 3-5-5 arrangements (3 cards in front, 5 in middle, 5 in back).

---

## 5. Card Recognition Engine
- **Font & Glyph Rendering**:
  - Reference templates are synthesized at multiple scales (16px to 32px height) using macOS system fonts (`Arial`, `Helvetica`, `Arial Unicode MS`).
- **Normalized Cross-Correlation (`cv2.TM_CCOEFF_NORMED`)**:
  - Scale-invariant matching against rank patches (top-left 40% height, 35% width).
- **Color Discrimination (HSV)**:
  - Masks hue for red ($[0, 10] \cup [170, 180]$) vs black ($V < 100$).
  - Prevents confusing Hearts/Diamonds with Spades/Clubs.
- **Suit Template Matching**:
  - Matches suit patch against candidate suit templates matching the detected color.

---

## 6. Manual Correction & Validation
- Cards are rendered with visual confidence badges ($<70\%$ highlighted).
- Users can click on any recognized card or thumbnail to open the **Card Correction Dialog**.
- 1-click rank and suit selector allows correcting false positives or lighting glitches before sending the 13 cards to the solver.
