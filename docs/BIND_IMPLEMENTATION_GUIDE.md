# StarlightDaemon Design System - BIND Implementation Guide

**For:** BIND Web UI  
**Date:** 2026-01-03  
**Design System Version:** 1.0  
**Agent Instructions:** Read this file completely, then apply the design system to BIND's web interface

---

## 📋 Overview

This guide contains everything you need to implement the StarlightDaemon design system in BIND's web UI. The design system provides:

- **Modern, clean aesthetic** inspired by AlternativeTo.net
- **Light theme** with blue accent color (#06a0ff)
- **Complete component library** (buttons, cards, inputs, etc.)
- **Responsive layouts** (mobile-first)
- **Accessibility built-in** (WCAG AA compliant)

---

## 🎨 Design Principles

### Core Values
1. **System fonts only** - No custom fonts (fast, native appearance)
2. **8px spacing scale** - Consistent rhythm (4px, 8px, 16px, 24px, etc.)
3. **12px border radius** - Standard for all components
4. **Light, clean backgrounds** - #f5f7f9 page background, white cards
5. **Blue accent** - #06a0ff for interactive elements
6. **Subtle shadows** - Depth without distraction

### Color Philosophy
- **Neutrals dominate** - Gray scale for 90% of the interface
- **Blue accent sparingly** - Only on interactive elements (buttons, links, focus)
- **High contrast text** - #2d3436 on light backgrounds (4.5:1+ ratio)
- **Generous whitespace** - Let content breathe

---

## 🚀 Quick Implementation

### Step 1: Add CSS to Your HTML
Copy the CSS from the section below and add it to your HTML `<head>` section:

```html
<head>
  <!-- ... other head content ... -->
  <style>
    /* PASTE THE COMPLETE CSS HERE (see next section) */
  </style>
</head>
```

### Step 2: Update HTML Structure
Replace existing class names with design system classes:
- `<button>` → `<button class="btn btn-primary">`
- `<div>` containers → `<div class="card">`
- `<input>` → `<input class="input">`
- Layout grids → `<div class="grid-auto">` or `<div class="grid-3">`

### Step 3: Test Responsiveness
- Resize browser to mobile width (375px minimum)
- Verify all components work on small screens
- Check that grids collapse properly

---

## 📦 COMPLETE CSS - COPY THIS ENTIRE BLOCK

```css
/*!
 * StarlightDaemon Design System v1.0
 * For BIND Web UI Implementation
 */

/* ============================================
   CSS VARIABLES
   ============================================ */
:root {
  /* Colors - Neutrals */
  --white: #ffffff;
  --gray-50: #f5f7f9;
  --gray-100: #e1e8ed;
  --gray-400: #636e72;
  --gray-700: #2d3436;
  --black: #000000;

  /* Colors - Brand */
  --primary: #06a0ff;
  --primary-dark: #0087d2;

  /* Colors - Status */
  --success: #1b5e20;
  --success-light: #a5d6a7;
  --error: #c62828;
  --warning: #f57c00;
  --info: #0277bd;

  /* Semantic Mapping */
  --bg: var(--gray-50);
  --bg-secondary: var(--white);
  --text: var(--gray-700);
  --text-secondary: var(--gray-400);
  --border: var(--gray-100);
  --accent: var(--primary);
  --accent-hover: var(--primary-dark);

  /* Typography */
  --font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', Consolas, 'Courier New', monospace;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.75rem;
  --text-3xl: 2rem;
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* Spacing (8px scale) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;

  /* Border Radius */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 2px 6px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 12px 32px rgba(0, 0, 0, 0.18);

  /* Animation */
  --ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
  --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0.0, 1, 1);
}

/* ============================================
   BASE RESET
   ============================================ */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-primary);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ============================================
   LAYOUT
   ============================================ */
.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.container-lg {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

/* ============================================
   GRIDS
   ============================================ */
.grid-auto {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6);
}

@media (max-width: 640px) {
  .grid-auto {
    grid-template-columns: 1fr;
  }
}

.grid-2 { 
  display: grid;
  grid-template-columns: repeat(2, 1fr); 
  gap: var(--space-6);
}

.grid-3 { 
  display: grid;
  grid-template-columns: repeat(3, 1fr); 
  gap: var(--space-6);
}

/* ============================================
   BUTTONS
   ============================================ */
.btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  font-family: var(--font-primary);
  border: none;
  cursor: pointer;
  transition: all 0.2s var(--ease-standard);
  display: inline-block;
  text-decoration: none;
  text-align: center;
}

.btn-primary {
  background: var(--accent);
  color: var(--white);
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ============================================
   CARDS
   ============================================ */
.card {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  transition: all 0.2s var(--ease-standard);
}

.card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.card-compact {
  padding: var(--space-4) var(--space-5);
}

/* ============================================
   INPUTS
   ============================================ */
.input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-base);
  font-family: var(--font-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--white);
  color: var(--text);
  transition: all 0.2s var(--ease-standard);
}

.input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(6, 160, 255, 0.1);
}

.input-error {
  border-color: var(--error);
}

.input:disabled {
  background: var(--gray-50);
  cursor: not-allowed;
  opacity: 0.6;
}

/* ============================================
   BADGES
   ============================================ */
.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-full);
  background: var(--gray-100);
  color: var(--text-secondary);
}

.badge-primary {
  background: var(--accent);
  color: var(--white);
}

.badge-success {
  background: var(--success-light);
  color: var(--success);
}

.badge-error {
  background: rgba(198, 40, 40, 0.1);
  color: var(--error);
}

/* ============================================
   LISTS
   ============================================ */
.list-clean {
  list-style: none;
  padding: 0;
  margin: 0;
}

.list-item {
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border);
}

.list-item:last-child {
  border-bottom: none;
}

/* ============================================
   HEADER/NAV
   ============================================ */
.header {
  background: var(--white);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-8);
}

.logo {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--accent);
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: var(--space-6);
  list-style: none;
}

.nav-links a {
  color: var(--text);
  text-decoration: none;
  font-weight: var(--font-medium);
  transition: color 0.2s var(--ease-standard);
}

.nav-links a:hover {
  color: var(--accent);
}

/* ============================================
   ACCESSIBILITY
   ============================================ */
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(6, 160, 255, 0.2);
}

/* ============================================
   ANIMATIONS
   ============================================ */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton {
  animation: skeleton-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  background: var(--gray-100);
  border-radius: var(--radius-md);
}

/* ============================================
   RESPONSIVE
   ============================================ */
.responsive-flex {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

@media (min-width: 768px) {
  .responsive-flex {
    flex-direction: row;
  }
}
```

---

## 🎯 Component Reference

### Buttons
```html
<!-- Primary button -->
<button class="btn btn-primary">Save Changes</button>

<!-- Small button -->
<button class="btn btn-primary btn-sm">Edit</button>

<!-- Disabled button -->
<button class="btn btn-primary" disabled>Processing...</button>
```

**When to use:**
- Primary actions (save, submit, confirm)
- Navigation (next, back)
- Destructive actions with confirmation

---

### Cards
```html
<!-- Standard card -->
<div class="card">
  <h3>Torrent Title</h3>
  <p>Torrent details here...</p>
</div>

<!-- Compact card -->
<div class="card card-compact">
  <span>Status: Active</span>
</div>
```

**When to use:**
- List items (torrents, feeds)
- Grouped information
- Dashboard widgets

---

### Inputs
```html
<!-- Standard input -->
<input type="text" class="input" placeholder="RSS Feed URL">

<!-- Error state -->
<input type="text" class="input input-error" placeholder="Invalid URL">

<!-- Disabled -->
<input type="text" class="input" disabled>
```

**When to use:**
- Form fields
- Search boxes
- Filter inputs

---

### Badges
```html
<!-- Status badges -->
<span class="badge-success badge">Active</span>
<span class="badge-error badge">Failed</span>
<span class="badge">Queued</span>
```

**When to use:**
- Status indicators (downloading, seeding, stopped)
- Categories or tags
- Counts (12 active)

---

### Grids
```html
<!-- Auto-responsive grid (recommended) -->
<div class="grid-auto">
  <div class="card">Item 1</div>
  <div class="card">Item 2</div>
  <div class="card">Item 3</div>
</div>

<!-- Fixed 2-column grid -->
<div class="grid-2">
  <div class="card">Column 1</div>
  <div class="card">Column 2</div>
</div>
```

**When to use:**
- List of torrents
- Dashboard layout
- Settings panels

---

## 🔍 BIND-Specific Recommendations

### For Torrent List View
```html
<div class="container-lg">
  <div class="grid-auto">
    <!-- Each torrent as a card -->
    <div class="card">
      <h3 style="margin-bottom: var(--space-2);">Torrent Name</h3>
      <p style="font-size: var(--text-sm); color: var(--text-secondary);">
        Size: 1.2 GB • Seeds: 45 • Peers: 12
      </p>
      <div style="margin-top: var(--space-4); display: flex; gap: var(--space-2);">
        <span class="badge-success badge">Seeding</span>
        <button class="btn btn-primary btn-sm">Pause</button>
      </div>
    </div>
  </div>
</div>
```

### For RSS Feed Management
```html
<div class="container">
  <div class="card">
    <h2 style="margin-bottom: var(--space-4);">RSS Feeds</h2>
    <ul class="list-clean">
      <li class="list-item">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>Feed Name</strong>
            <span style="display: block; font-size: var(--text-sm); color: var(--text-secondary);">
              Last updated: 2 hours ago
            </span>
          </div>
          <button class="btn btn-primary btn-sm">Edit</button>
        </div>
      </li>
    </ul>
  </div>
</div>
```

### For Settings Page
```html
<div class="container">
  <h1 style="margin-bottom: var(--space-8);">Settings</h1>
  
  <div class="card" style="margin-bottom: var(--space-6);">
    <h3 style="margin-bottom: var(--space-4);">Download Settings</h3>
    
    <div style="margin-bottom: var(--space-4);">
      <label style="display: block; margin-bottom: var(--space-2); font-weight: var(--font-medium);">
        Download Directory
      </label>
      <input type="text" class="input" value="/downloads">
    </div>
    
    <button class="btn btn-primary">Save Changes</button>
  </div>
</div>
```

---

## ✅ Implementation Checklist

Before considering the implementation complete:

- [ ] All existing buttons use `.btn .btn-primary` classes
- [ ] All card/panel elements use `.card` class
- [ ] All form inputs use `.input` class
- [ ] Layout uses `.container` or `.container-lg`
- [ ] Lists of items use `.grid-auto` or `.grid-2`/`.grid-3`
- [ ] Status indicators use `.badge` with appropriate colors
- [ ] Page background is light gray (#f5f7f9)
- [ ] Text is dark gray (#2d3436)
- [ ] Blue accent color (#06a0ff) used for interactive elements
- [ ] Tested on mobile (375px width minimum)
- [ ] Focus states are visible (blue glow)
- [ ] Hover effects work on interactive elements

---

## 🎨 Color Usage Guidelines

| Color | Variable | Hex | Use For |
|-------|----------|-----|---------|
| Background | `var(--bg)` | #f5f7f9 | Page background |
| Card | `var(--white)` | #ffffff | Cards, panels |
| Text | `var(--text)` | #2d3436 | Primary text |
| Secondary Text | `var(--text-secondary)` | #636e72 | Labels, timestamps |
| Border | `var(--border)` | #e1e8ed | Card borders, dividers |
| Accent | `var(--accent)` | #06a0ff | Buttons, links, focus |
| Success | `var(--success)` | #1b5e20 | Seeding, active |
| Error | `var(--error)` | #c62828 | Failed, errors |

---

## 📝 Notes for BIND Agent

1. **Keep it simple** - Start with the basics (buttons, cards, inputs)
2. **Use variables** - Always use `var(--accent)` not `#06a0ff` directly
3. **Test mobile** - BIND might be used on phones/tablets
4. **Accessibility** - Maintain proper contrast ratios
5. **Consistency** - If something looks different from other projects, it's probably wrong

---

## 🆘 Troubleshooting

**Problem:** Colors don't look right  
**Solution:** Make sure CSS is in the `<head>` section, not at the end of body

**Problem:** Components don't have hover effects  
**Solution:** Check that you're using the exact class names (`.card` not `.torrent-card`)

**Problem:** Layout is broken on mobile  
**Solution:** Use `.grid-auto` instead of `.grid-3` for responsive layouts

**Problem:** Text is hard to read  
**Solution:** Use `var(--text)` for main text, `var(--text-secondary)` for labels

---

## 📞 Questions?

If anything is unclear during implementation:
1. Check the component reference section
2. Look at BIND-specific recommendations
3. Refer back to this document
4. The design system maintainer (Claude) can clarify

---

**Version:** 1.0  
**Last Updated:** 2026-01-03  
**Maintained By:** StarlightDaemon Design System

Good luck with the implementation! 🚀
