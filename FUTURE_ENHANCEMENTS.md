# BIND - Future Enhancements

## Priority 1: UI/UX Improvements

### StarlightDaemon Design System Implementation
**Status**: Design guide complete, ready to implement  
**File**: `BIND_IMPLEMENTATION_GUIDE.md`  
**Estimated Time**: 2-3 hours

**Current Web UI**: Purple gradient, basic layout  
**Target Design**: Clean, light theme based on AlternativeTo.net aesthetic

**Key Changes**:
- ✅ Replace purple gradient (#667eea/#764ba2) with light gray background (#f5f7f9)
- ✅ Change accent from purple to StarlightDaemon blue (#06a0ff)
- ✅ Add proper cards with borders and hover effects
- ✅ Implement design system CSS variables
- ✅ Update buttons to match design system
- ✅ Add badges for status indicators
- ✅ Improve mobile responsiveness
- ✅ Better typography (system fonts only)

**Benefits**:
- Professional, clean appearance
- Consistent with other StarlightDaemon projects
- Better accessibility (WCAG AA compliant)
- Improved mobile experience
- Easier to maintain

---

## Priority 2: Quick Wins (1-2 hours each)

### Keyword Filtering
- [ ] `--include "author1,author2"` option
- [ ] `--exclude "abridged,sample"` option
- [ ] Simple string matching
- **ROI**: High (4/5) - Focused archival

### Configurable Daemon Interval
- [ ] CLI option: `--interval 30`
- [ ] Remove hardcoded 60-minute default
- **ROI**: Medium (3/5) - User flexibility

### Magnet Deduplication
- [ ] Hash-based uniqueness check
- [ ] Skip already-collected magnets
- **ROI**: Medium (3/5) - Cleaner archives

---

## Priority 3: Nice to Have

### RSS Feed Enhancements
- [ ] Pagination support (>100 magnets)
- [ ] HTTPS support for RSS server
- [ ] Custom feed titles

### Configuration File
- [ ] `config.yaml` support
- [ ] Centralized settings
- [ ] Per-user configs

---

## Probably Never

These were evaluated and rejected due to low ROI:

- ❌ **Statistics dashboard** (200+ lines, 20% usage)
- ❌ **Desktop GUI** (incompatible with LXC deployment)
- ❌ **Complex category filtering** (50% effort, 30% value)
- ❌ **Search command** (already removed - redundant)

---

## Implementation Notes

**Design System**: Follow `BIND_IMPLEMENTATION_GUIDE.md` exactly
- Use CSS variables (`var(--accent)` not `#06a0ff`)
- Test on mobile (375px minimum)
- Maintain accessibility standards
- Keep HTML structure simple

**Testing Required**:
- Visual comparison with design guide
- Mobile responsiveness check
- Browser compatibility (Chrome, Firefox, Safari)
- Accessibility audit
