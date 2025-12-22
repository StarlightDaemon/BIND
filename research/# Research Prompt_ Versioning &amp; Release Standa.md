<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# \# Research Prompt: Versioning \& Release Standards

**Role:** You are a Senior Release Engineer and DevOps Specialist with expertise in software versioning, changelog management, and release documentation.

**Objective:** Provide a comprehensive guide on "Best in Class" standards for version numbering, changelogs, and release notes, specifically tailored for a modern browser extension (Manifest V3) built with React and TypeScript.

**Requirements:**

1. **Version Numbering:**
    *   Compare **Semantic Versioning (SemVer)** vs. **Calendar Versioning (CalVer)**. Which is better for extensions?
    *   Explain how to handle major, minor, and patch increments in the context of extension updates (e.g., UI overhauls vs. bug fixes).
    *   Recommend a strategy for pre-release versions (alpha, beta, rc) and how they map to Chrome Web Store / AMO submission processes.
2. **Changelogs:**
    *   What is the "Gold Standard" format for a `CHANGELOG.md`? (e.g., Keep a Changelog).
    *   How should changes be categorized? (Added, Changed, Deprecated, Removed, Fixed, Security).
    *   Should we maintain separate changelogs for users (simplified) vs. developers (detailed)?
3. **Release Notes:**
    *   How to write compelling release notes for the Chrome Web Store / AMO listings.
    *   Best practices for communicating new features to users without overwhelming them.
    *   Examples of excellent release notes from top-tier extensions.
4. **Automation \& Tooling:**
    *   Suggest tools to automate version bumping and changelog generation (e.g., `standard-version`, `semantic-release`, `changesets`).
    *   How to integrate this into a CI/CD pipeline (GitHub Actions).

**Output:**
Please structure your response as a **Best Practices Guide** that we can immediately adopt for the "Torrent Control Reloaded" project. Include concrete examples and a proposed template for our `CHANGELOG.md`.

Perfect! Now I have all the resources created. Let me write the comprehensive best practices guide as the main response.

***

# Best Practices Guide: Versioning \& Release Standards for Browser Extensions

## Executive Summary

For **Torrent Control Reloaded**, the recommended approach combines **Semantic Versioning (SemVer)** with **Keep a Changelog** format and **Conventional Commits**, automated through **commit-and-tag-version** in a GitHub Actions CI/CD pipeline. This ensures professional, maintainable, and scalable release processes that meet Chrome Web Store and Mozilla AMO requirements.

***

## 1. Version Numbering: SemVer for Browser Extensions

### Why Semantic Versioning Over Calendar Versioning?

While CalVer (e.g., `2025.01.15`) provides release timing context, **SemVer is superior for browser extensions** because it communicates the **type and severity of changes** at a glance. This is critical for users deciding whether to upgrade immediately or defer.[^1_1][^1_2]

**SemVer Format:** `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`


| Component | Purpose | Example |
| :-- | :-- | :-- |
| **MAJOR** | Breaking changes, complete redesigns | `1.0.0` → `2.0.0` (ITorrentClient interface redesigned) |
| **MINOR** | New backward-compatible features | `1.0.0` → `1.1.0` (Added qBittorrent support) |
| **PATCH** | Bug fixes, security patches | `1.1.0` → `1.1.1` (Fixed connection timeout bug) |
| **PRERELEASE** | Beta/RC versions for testing | `1.1.0-beta.1`, `1.1.0-rc.1` |
| **BUILD** | Build metadata (doesn't affect precedence) | `1.1.0+build.20250115` |

### Chrome Web Store \& Firefox AMO Compatibility

Both platforms accept numeric versioning:[^1_3]

**Chrome Web Store:**

```json
{
  "manifest_version": 3,
  "version": "1.2.3",
  "version_name": "1.2.3 Beta 1"
}
```

Chrome strips pre-release identifiers from the version field (must be numeric), but `version_name` provides user-facing context. This dual approach lets the store see clean `1.2.3` while users see "1.2.3 Beta 1."

### Pre-Release Progression Path

```
0.1.0-alpha.0 → 0.1.0-alpha.1 → 0.1.0-beta.0 → 0.1.0-beta.1 → 0.1.0-rc.1 → 1.0.0
```

**Publishing Strategy:**

- **Alpha releases**: Internal testing only (do not publish to stores)
- **Beta releases**: Publish with **1% gradual rollout** to catch critical bugs early
- **Release Candidates**: Expand rollout to 25-50% as confidence increases
- **Production releases**: Full 100% deployment[^1_4]

This staged approach has become standard practice at tech companies—it drastically reduces user-facing bugs in production while maintaining momentum.

***

## 2. Changelog Standards: Keep a Changelog Format

### The Gold Standard Format

**Keep a Changelog** is the industry standard for open-source projects. It solves the fundamental problem with changelogs: **they're rarely human-readable** because developers dump git logs.[^1_5][^1_6]

**Core Structure:**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
### Changed
### Fixed
### Security

## [1.0.0] - 2025-01-15

### Added
- New feature descriptions with context

### Fixed
- Bug fix with problem and solution
```


### Standard Categories Explained

| Category | When to Use | Extension Example |
| :-- | :-- | :-- |
| **Added** | New features or capabilities | "Added support for Deluge torrent client" |
| **Changed** | Modifications to existing functionality | "Improved error messages for failed connections" |
| **Deprecated** | Features marked for future removal | "Deprecated getRawStatus() method in favor of getStatusAsync()" |
| **Removed** | Previously deprecated features now removed | "Removed support for Transmission API v1" |
| **Fixed** | Bug fixes and corrections | "Fixed race condition in service worker initialization" |
| **Security** | Vulnerability patches and security hardening | "Patched XSS vulnerability in torrent name rendering" |

### Dual Changelog Strategy: Developers vs. Users

Maintain **two levels** of documentation:

**Technical Changelog** (`CHANGELOG.md` in repo):

- Audience: Developers, contributors, maintainers
- Detail: Comprehensive, includes implementation details
- Example: "Fixed race condition in `TorrentClientManager._initializeConnections()` when multiple clients connect simultaneously. Now uses semaphore lock pattern to serialize initialization."

**User-Facing Release Notes** (Chrome Web Store / Firefox AMO):

- Audience: End users
- Detail: Simplified, benefit-focused
- Example: "Fixed issue where adding multiple torrents rapidly could cause instability"

Generate public notes by filtering technical changelog entries to user-impacting items and rewording for clarity.

***

## 3. Release Notes for Web Stores

### Writing Compelling Release Notes

Top-tier extensions (Linear, Notion, Slack) follow these principles:[^1_7][^1_8]

**✅ Best Practices:**

- **Lead with the primary benefit**, not technical details
- **Use plain language** (avoid jargon)
- **Keep it concise** (3-5 key points per release)
- **Include visual context** where possible (before/after screenshots)
- **Highlight breaking changes** or required actions
- **Include support links** for complex features

**❌ Common Mistakes:**

- Dumping git commit logs
- Vague language: "various improvements," "bug fixes"
- Overly technical architectural details
- Overwhelming users with every minor change
- Forgetting about users still on previous versions


### Store Release Notes Template

```
**✨ What's New in v1.2.0 - February 2025**

[One-sentence hook about biggest user-facing change]

🚀 New Features
• Feature 1 with clear benefit
  (e.g., "Now supports 4 torrent clients for unified management")
• Feature 2 with context
  (e.g., "Right-click context menu for one-click torrent adding")

🐛 Fixes & Improvements
• Fixed issue where torrents wouldn't start downloading
• Improved performance when managing 100+ torrents
• Enhanced error messages for clearer troubleshooting

📌 Important Updates
[Only if applicable]
• Security fix: Update recommended immediately
• Breaking change: See documentation for migration steps

💡 Need Help?
Documentation: [link]
Report issues: [GitHub Issues]
```


***

## 4. Automation \& Tooling Stack

The modern standard for release automation combines three tools that work seamlessly together:[^1_9][^1_10][^1_11][^1_12]

### 4.1 Conventional Commits Specification

**Purpose:** Standardize commit messages so tools can automatically determine version bumps and generate changelogs.

**Format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Commit Types:**

- `feat`: New feature → triggers **MINOR** bump
- `fix`: Bug fix → triggers **PATCH** bump
- `feat!` or `BREAKING CHANGE:`: Breaking change → triggers **MAJOR** bump
- `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`: Non-version-bumping changes

**Scope Examples** (identifies component):

- `popup`, `background`, `storage`, `api`, `transmission`, `qbittorrent`, `deluge`, `rtorrent`

**Example Commits:**

```bash
# Feature
git commit -m "feat(popup): add dark mode support"

# Bug fix  
git commit -m "fix(background): resolve service worker state loss on restart"

# Breaking change
git commit -m "feat(api)!: redesign ITorrentClient interface

BREAKING CHANGE: getStatus() now returns Promise<TorrentStatus[]> instead of TorrentStatus[]"

# Performance
git commit -m "perf(storage): implement debounced writes reducing I/O by 80%"

# Security
git commit -m "fix(security): sanitize torrent metadata to prevent XSS"
```


### 4.2 commit-and-tag-version Tool

**Modern replacement for `npm version`** with automatic CHANGELOG generation.[^1_10]

**Installation:**

```bash
npm install --save-dev commit-and-tag-version
```

**What it does automatically:**

1. Parses commits since last tag using Conventional Commits format
2. Calculates appropriate version bump (MAJOR/MINOR/PATCH)
3. Updates `package.json` and `manifest.json` versions
4. Generates CHANGELOG.md entries
5. Creates git commit with version changes
6. Creates git tag with new version

**Usage:**

```bash
# Automatic bump based on commits
npm run release

# Explicit bump
npm run release:minor
npm run release:major

# Pre-releases for testing
npm run release:beta   # v1.2.0-beta.0
npm run release:rc     # v1.2.0-rc.1

# Preview without committing
npm run release:dry-run
```


### 4.3 GitHub Actions CI/CD Pipeline

Fully automated release workflow that:

- Validates code (lint, test, type-check, build)
- Generates release version and changelog
- Creates GitHub release with artifacts
- Deploys to Chrome Web Store and Firefox AMO

See  for complete workflow template.

***

## 5. Implementation for Torrent Control Reloaded

### Quick Start Setup

**Step 1: Install Dependencies**

```bash
npm install --save-dev commit-and-tag-version conventional-changelog-conventionalcommits
```

**Step 2: Create Configuration**

Create `.versionrc.json` in project root:

```json
{
  "types": [
    { "type": "feat", "section": "✨ Features", "hidden": false },
    { "type": "fix", "section": "🐛 Fixes", "hidden": false },
    { "type": "perf", "section": "⚡ Performance", "hidden": false },
    { "type": "security", "section": "🔒 Security", "hidden": false }
  ],
  "bumpFiles": [
    { "filename": "package.json", "type": "json" },
    { "filename": "manifest.json", "type": "json" }
  ],
  "packageFiles": [
    { "filename": "package.json", "type": "json" },
    { "filename": "manifest.json", "type": "json" }
  ],
  "releaseCommitMessageFormat": "chore(release): {{currentTag}} [skip-release]",
  "tagPrefix": "v",
  "infile": "CHANGELOG.md"
}
```

**Step 3: Update package.json Scripts**

```json
{
  "scripts": {
    "release": "commit-and-tag-version",
    "release:minor": "commit-and-tag-version --release-as minor",
    "release:beta": "commit-and-tag-version --prerelease beta",
    "release:dry-run": "commit-and-tag-version --dry-run"
  }
}
```

**Step 4: Set Up GitHub Actions**

Copy  to `.github/workflows/release.yml`. Configure GitHub Secrets for store deployments:

- `CHROME_EXTENSION_ID`
- `CHROME_CLIENT_ID`, `CHROME_CLIENT_SECRET`, `CHROME_REFRESH_TOKEN`
- `FIREFOX_API_KEY`, `FIREFOX_API_SECRET`

**Step 5: Add CHANGELOG.md**

Use template from  as starting point.

### Workflow in Action

**Day-to-day development:**

```bash
git commit -m "feat(popup): add quick-add context menu"
git commit -m "fix(background): resolve client connection timeout"
git push origin feature-branch
```

**After PR merge to main:**

```bash
# GitHub Actions automatically runs:
# 1. Lint, test, type-check, build
# 2. commit-and-tag-version updates versions and CHANGELOG
# 3. Pushes new tag
# 4. Creates GitHub release
# 5. (Optional) Deploys to Chrome Web Store & Firefox

# Locally, you can also trigger:
npm run release
```


***

## 6. Complete CHANGELOG Template

See  for a production-ready template specifically tailored for Torrent Control Reloaded.

Key features:

- Keep a Changelog format
- SemVer-aligned entries
- Pre-release section showing development stages
- Categories showing feature progression through dev → beta → RC → production
- Real-world examples relevant to browser extensions

***

## 7. Comprehensive Configuration Templates

All configuration files, commit examples, GitHub Actions workflow, and troubleshooting are in :

- `.versionrc.json` configuration
- `package.json` scripts
- `manifest.json` version fields
- Commit message examples (feat, fix, security, breaking changes)
- GitHub Actions workflow
- Pre-commit hooks (optional)
- GitHub Secrets setup
- Testing procedures

***

## 8. Best Practices Checklist

### Before Every Release

- [ ] All commits follow Conventional Commits format
- [ ] CHANGELOG.md entries are accurate and complete
- [ ] Version number follows SemVer
- [ ] Breaking changes documented in commit footer or CHANGELOG
- [ ] Tests pass, coverage maintained
- [ ] Extension builds successfully
- [ ] Manifest.json and package.json versions match
- [ ] Store listing updated with user-friendly release notes
- [ ] Pre-release notes prepared if applicable
- [ ] Gradual rollout percentages planned (for production)


### Browser Extension Specifics

- [ ] Manifest V3 compliance verified (CSP headers, service workers)
- [ ] Host permissions minimized and justified
- [ ] Chrome Web Store policy checklist completed
- [ ] Firefox AMO review criteria met
- [ ] Privacy policy updated (if data collection changed)
- [ ] Tested across Chrome, Edge, and Firefox (if supported)
- [ ] Screenshot and icon assets optimized
- [ ] Localization files updated


### Documentation

- [ ] README.md updated with new features
- [ ] API documentation reflects changes
- [ ] Migration guide provided for breaking changes
- [ ] Contributing guide reflects versioning practices

***

## 9. Common Pitfalls \& Solutions

| Pitfall | Impact | Solution |
| :-- | :-- | :-- |
| Skipping pre-releases | Untested features reach users | Always alpha → beta → RC → prod |
| Unclear commit messages | Unintelligible changelog | Enforce Conventional Commits strictly |
| Too frequent releases | User update fatigue, store complaints | Bundle fixes weekly, features monthly |
| Breaking changes unannounced | Users report crashes, support tickets spike | Use deprecation notices 1-2 releases prior |
| Vague store release notes | Low engagement, confusion | Focus on user benefits, not tech details |
| Manual version bumping | Human error, inconsistent versions | Automate with commit-and-tag-version |
| Not testing beta releases | Bugs still reach users | Use gradual rollout: 1% → 25% → 100% |
| Inconsistent changelog format | Loss of clarity over time | Use Keep a Changelog template religiously |


***

## 10. Reference Architecture

```
Conventional Commits
        ↓
(Developer workflow)
        ↓
GitHub Repository (main branch)
        ↓
GitHub Actions Trigger
        ↓
┌─────────────────────────────┐
│  Validate & Build            │
│  - Lint code                 │
│  - Run tests                 │
│  - Type-check                │
│  - Build extension           │
└─────────────────────────────┘
        ↓
┌─────────────────────────────┐
│  Generate Release            │
│  - Parse commits             │
│  - Bump version (SemVer)     │
│  - Update CHANGELOG          │
│  - Create git tag            │
│  - Create GitHub release     │
└─────────────────────────────┘
        ↓
┌─────────────────────────────┐
│  Deploy to Stores            │
│  - Chrome Web Store (staged) │
│  - Firefox AMO               │
└─────────────────────────────┘
        ↓
┌─────────────────────────────┐
│  User Notifications          │
│  - GitHub release page       │
│  - Changelog entry           │
│  - Extension update (user)   │
└─────────────────────────────┘
```


***

## Summary: Implementation Priorities

**Phase 1 (Week 1): Foundation**

- Adopt Semantic Versioning
- Implement Conventional Commits in your team's workflow
- Create CHANGELOG.md using Keep a Changelog format

**Phase 2 (Week 2): Automation**

- Install and configure commit-and-tag-version
- Create .versionrc.json and update package.json scripts
- Test locally with `npm run release:dry-run`

**Phase 3 (Week 3): CI/CD Integration**

- Set up GitHub Actions workflow
- Configure GitHub Secrets for store access
- Test end-to-end pipeline with beta release

**Phase 4 (Week 4+): Refinement**

- Monitor production releases for issues
- Adjust gradual rollout percentages based on learnings
- Document team practices in CONTRIBUTING.md

***

## Resources

- **Semantic Versioning:** https://semver.org[^1_2]
- **Keep a Changelog:** https://keepachangelog.com[^1_6]
- **Conventional Commits:** https://www.conventionalcommits.org[^1_11][^1_12]
- **commit-and-tag-version:** https://github.com/absolute-version/commit-and-tag-version[^1_10]
- **Chrome Web Store Publishing:** https://developer.chrome.com/docs/webstore/publish/[^1_4]
- **Firefox Add-ons Publishing:** https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Publishing_your_WebExtension
<span style="display:none">[^1_13][^1_14][^1_15][^1_16][^1_17][^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47]</span>

<div align="center">⁂</div>

[^1_1]: https://github.com/dbrock/semver-howto

[^1_2]: https://semver.org

[^1_3]: https://davestewart.co.uk/blog/extension-versioning/

[^1_4]: https://developer.chrome.com/docs/webstore/best-practices

[^1_5]: https://jobs-staging.ilipra.org/blog/creating-a-standard-changelog-md

[^1_6]: https://keepachangelog.com/en/1.1.0/

[^1_7]: https://www.candu.ai/blog/how-to-write-release-notes-best-practices-examples-templates

[^1_8]: https://www.launchnotes.com/blog/release-notes-examples

[^1_9]: https://blog.logrocket.com/using-semantic-release-automate-releases-changelogs/

[^1_10]: https://www.npmjs.com/package/commit-and-tag-version

[^1_11]: https://www.conventionalcommits.org/en/v1.0.0-beta.3/

[^1_12]: https://www.conventionalcommits.org/en/v1.0.0/

[^1_13]: https://callowayproject.github.io/bump-my-version/howtos/calver/

[^1_14]: https://gosink.in/versioning-strategies-explained-semver-to-calver-and-beyond-and-which-one-should-you-choose-2/

[^1_15]: https://stackoverflow.com/questions/67502840/see-previous-versions-of-an-extension-published-to-the-chrome-web-store

[^1_16]: https://talent500.com/blog/semantic-versioning-explained-guide/

[^1_17]: https://www.reddit.com/r/golang/comments/1jzucpw/scalable_calendar_versioning_calver_semver/

[^1_18]: https://stackoverflow.com/questions/11826207/user-specific-version-of-extensions-from-chrome-web-store

[^1_19]: https://www.tiny.cloud/blog/improving-our-engineering-best-practices-with-semantic-versioning/

[^1_20]: https://openchangelog.com/docs/getting-started/keep-a-changelog/

[^1_21]: https://www.uxpin.com/studio/blog/how-to-create-a-design-system-changelog/

[^1_22]: https://developer.wordpress.org/news/2025/11/the-importance-of-a-good-changelog/

[^1_23]: https://developer.chrome.com/docs/webstore/program-policies/best-practices

[^1_24]: https://openchangelog.com/blog/changelog-md

[^1_25]: https://userguiding.com/blog/changelog-best-practices

[^1_26]: https://userpilot.com/blog/release-notes-best-practices/

[^1_27]: https://github.com/changesets/changesets/discussions/974

[^1_28]: https://dev.to/vishnusatheesh/how-to-set-up-a-cicd-pipeline-with-github-actions-for-automated-deployments-j39

[^1_29]: https://github.com/semantic-release/semantic-release

[^1_30]: https://github.com/changesets/changesets/discussions/920

[^1_31]: https://dev.to/msrabon/automating-docker-image-versioning-build-push-and-scanning-using-github-actions-388n

[^1_32]: https://www.reddit.com/r/devops/comments/18jsdpr/newb_question_automatically_handling_semantic/

[^1_33]: https://gasket.dev/docs/changeset/

[^1_34]: https://www.reddit.com/r/devops/comments/1autjvw/github_action_versioning_workflow_automatically/

[^1_35]: https://github.com/semantic-release/changelog

[^1_36]: https://userguiding.com/blog/best-chrome-extensions

[^1_37]: https://dev.to/javediqbal8381/understanding-chrome-extensions-a-developers-guide-to-manifest-v3-233l

[^1_38]: https://www.browserstack.com/guide/chrome-extensions-for-web-developers

[^1_39]: https://discourse.mozilla.org/t/when-will-web-ext-support-manifest-v3/91514

[^1_40]: https://www.reddit.com/r/firefox/comments/1kypa7i/can_someone_explain_the_point_of_manifest_v3_and/

[^1_41]: https://amoeboids.com/blog/55-release-notes-examples-to-inspire-you/

[^1_42]: https://stackoverflow.com/questions/1456608/how-do-i-differentiate-between-beta-versions-and-normal-versions

[^1_43]: https://stackoverflow.com/questions/38460008/automate-git-commit-versioning-tag-by-npm-node

[^1_44]: https://github.com/absolute-version/commit-and-tag-version/blob/master/README.md

[^1_45]: https://eagerworks.com/blog/conventional-commits

[^1_46]: https://discourse.mozilla.org/t/changes-to-version-number-format-starting-in-firefox-108/108715

[^1_47]: https://www.npmjs.com/package/standard-version/v/4.4.0

