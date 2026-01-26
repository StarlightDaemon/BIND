# BIND UI DESIGN SYSTEM AUDIT REPORT
**Execution Context:** `BIND_UI_CARBON_AUDIT_v1.0`  
**Date:** 2026-01-25  
**Auditor:** BIND UI Audit Agent  
**Governance:** TRON Design Standards  

---

## 1. Executive Summary

The BIND User Interface is currently **Carbon-Compliant with Legacy Artifacts**.

While the visual presentation strictly adheres to IBM Carbon Design System principles (White Theme) via the legacy "Vesper/Starlight" implementation, the technical architecture is **non-compliant**. The design system is implemented via massive copy-pasted `<style>` blocks in every template, rather than a centralized CSS asset.

**Verdict:** **Carbon-Compliant with Legacy Artifacts**  
**Risk Level:** **High** (Maintainability)

---

## 2. UI Asset Inventory

### 2.1 HTML Templates
All templates contain embedded legacy CSS.
- `src/templates/index.html` (Dashboard)
- `src/templates/magnets.html` (Search & List)
- `src/templates/settings.html` (Config Form)
- `src/templates/logs.html` (Log Viewer)
- `src/templates/setup.html` (First-run)

### 2.2 Static Assets
- **CSS:** None (Missing centralized stylesheet)
- **JS:** None (Inline scripts only)
- **Images:** None (SVG paths embedded in HTML)

---

## 3. Carbon Compliance Assessment

### 3.1 Component Usage
| Component | Carbon Equivalent | Compliance | Notes |
|-----------|-------------------|------------|-------|
| UI Shell | `ui-shell` | **High** | Correct height, padding, and typography. |
| Side Nav | `left-nav` | **High** | Correct spacing, hover states, and selection markers. |
| Buttons | `btn`, `btn-primary` | **High** | Correct tokens for padding, height (48px), and interaction. |
| Data Table | `magnet-list` | **Medium** | Custom grid implementation, but visually aligns with Carbon structured list. |
| Forms | `input`, `label` | **High** | Correct bottom-border usage and focus states. |
| Typography | IBM Plex Sans | **High** | Correct font family and scale. |

### 3.2 Tokens & Variables
The embedded CSS defines a root block mapping "Starlight" tokens to standard Carbon values:
- **Colors:** `--colors-blue-60` (#0f62fe), `--colors-gray-10` (#f4f4f4), etc.
- **Spacing:** `--spacing-05` (1rem), `--spacing-07` (2rem).
- **Theme:** Explicitly implements Carbon "White Theme" semantics.

---

## 4. Legacy Vesper Artifact Findings

**Status:** **ACTIVE** (Rendering the entire UI)

The "Vesper" system (referenced as `Starlight Carbon Design System - BIND Implementation` in code comments) is the **sole styling engine** currently.

### Detected Artifacts (Repeated in ALL templates)
1.  **CSS Header:**
    ```css
    /*!
     * Starlight Carbon Design System - BIND Implementation
     * Source: starlight-governance-kit (v2.0.0)
     * Theme: White
     */
    ```
2.  **Token Definitions:** A `:root` block defining `1-primitive` and `2-semantic` tokens.
3.  **Component Classes:** Full CSS definitions for `.btn`, `.ui-shell`, etc. embedded directly in `<head>`.

---

## 5. Hybridization & Drift Risks

- **Hybridization:** Low. The system is consistently "Legacy Vesper". It does not mix multiple design systems.
- **Drift:** **Critical**.
    - Because the CSS is duplicated 5 times, it is practically guaranteed that one file will drift from the others during future edits.
    - Example: Changing the accent color requires 5 manual edits.

---

## 6. Accessibility & UX Observations

- **Focus States:** Carbon default focus rings (blue glow) are implemented correctly.
- **Contrast:** High contrast (Gray 100 on White) meets readability standards.
- **Responsiveness:** Mobile-first media queries (`max-width: 672px`) for SideNav hiding are present and functional.

---

## 7. Compliance Verdict

**Final Verdict:** **Carbon-Compliant with Legacy Artifacts**

The UI *looks* and *behaves* like Carbon, but the *code* is Legacy Vesper.

---

## 8. Required Remediation

**Blocking for 1.0 Release:**
1.  **Centralize CSS:** Extract the embedded `<style>` block from `index.html` (as the master) into `src/static/css/carbon.css`.
2.  **Refactor Templates:** Replace `<style>` blocks in all 5 templates with `<link rel="stylesheet" href="/static/css/carbon.css">`.
3.  **Purge Legacy Comments:** Remove "Starlight Carbon" headers and replace with standard "IBM Carbon / TRON Governance" attributions.

---

## 9. Non-Blocking Recommendations

- **Iconography:** Replace embedded SVG paths with a standard icon sprite or Carbon icon library linkage.
- **JS Extraction:** Move the polling logic in `index.html` to `src/static/js/dashboard.js`.

---

## 10. Appendix: Evidence

**File:** `src/templates/setup.html` (Lines 8-13)
```html
    <style>
        /*!
     * Starlight Carbon Design System - BIND Implementation
     * Source: starlight-governance-kit (v2.0.0)
     * Theme: White
     */
```

**File:** `src/templates/settings.html` (Lines 15-25)
```css
        :root {
            /* 1. Primitive Tokens */
            --colors-blue-60: #0f62fe;
            --colors-gray-10: #f4f4f4;
            /* ... */
```
