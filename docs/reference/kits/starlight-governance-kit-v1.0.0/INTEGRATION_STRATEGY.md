# Governance Integration Strategy

**Context**: Starlight Carbon Architect (SCA) vs. Independent MIT Projects.
**Goal**: Ensure long-term compliance without bloating independent repositories.

## The Core Dilemma
You have independent projects ("Free Range") that need to follow strict design rules ("The Law").
- **If you embed the kit:** It becomes "dead code" and is hard to update.
- **If you delete the kit:** The project will drift (break rules) immediately upon the next edit.

## The Recommended Path: "DevDependency Evolution"

We recommend a 3-stage maturity model for these projects.

### Stage 1: The "Vendored" Phase (Current)
**Best for:** Initial Rewrite / Greenfield Construction.
**How:**
- Copy the `starlight-governance-kit` folder into `scripts/starlight-governance/`.
- **Status:** The code lives within the Project Repo.
- **Why:** The Builder Agent needs immediate, zero-latency access to tokens and local validation scripts to build the foundation.
- **License Impact:** Minimal. It's just a build tool script.

### Stage 2: The "CI/CD Gatekeeper" Phase (Intermediate)
**Best for:** Active Maintenance.
**How:**
- Configure GitHub Actions (or equivalent) to run the validator against Pull Requests.
- **Command:** `npm run validate` (executed from the local script).
- **Rule:** "You cannot merge code that breaks Carbon rules."
- **Why:** This enforces the "System of Record" rule automatically.

### Stage 3: The "Managed Package" Phase (Ideal / Future)
**Best for:** Long-term Stability across multiple projects.
**How:**
- Publish the SCA governance tool as a real NPM package: `@starlight/governance`.
- **Project Action:**
    1.  Delete `scripts/starlight-governance/`.
    2.  `npm install --save-dev @starlight/governance`.
    3.  Add script: `"validate": "starlight-governance validate"`.
- **Why:**
    - **Clean Repos:** Source code only contains project logic.
    - **Central Updates:** If Starlight updates a color token, you just bump the package version in the project.
    - **Open Source Friendly:** It's a standard dependency pattern, familiar to all MIT/OSS developers.

## Summary of Options

| Option | Setup | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **A. Embed (Current)** | Copy folder to repo | Zero deps, works now. | Hard to update. Bloats repo. |
| **B. Eject (Delete)** | Build then delete | Clean repo. | **Drift is guaranteed.** No safety net. |
| **C. Package (Future)** | `npm install -D` | Clean, Updatable, Standard. | Requires publishing package. |

## Recommendation
1.  **Start with Option A (Embed)** for the rebuild.
2.  **Plan for Option C (Package)**. Once the first project is successful, we should publish the governance tool so future updates are easy.
