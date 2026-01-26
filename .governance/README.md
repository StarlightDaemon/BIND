# Agent Handoff Protocol: The Reconstruction

**Version:** 2.0.0 (Greenfield Edition)
**Role:** Starlight Carbon Architect -> Builder Agents
**Strategy:** Radical Reconstruction (Rewrite First)

## Overview
This protocol is designed for the **complete reconstruction** of legacy interfaces. We operate under the assumption that existing projects have **0% compliance** with the Starlight Carbon Design System.
**Do not attempt to patch the old code.** Burn it down (figures of speech), and rebuild it correctly.

---

## 1. The Migration Kit
You identify as a **Builder Agent**. Your toolkit (`starlight-governance-kit`) contains:

1.  **README.md** (This file): Your instruction manual.
2.  **tokens/**: The *only* valid source of colors, spacing, and typography.
3.  **validator/**: A CLI tool to verify your work.
4.  **Drift Report**: Use this *only* if you must deviate from the system (rare).

## 2. The Reconstruction Workflow

### Phase 1: Tabula Rasa (Setup)
Start your target project by establishing a clean foundation.
1.  **Initialize**: Create a new framework instance (e.g., React/Vite or Next.js) if the old one is archaic.
2.  **Install**: `npm install @carbon/react` (or your framework equivalent).
3.  **Inject Governance**: Copy the `validator` folder into your project root (e.g., `/scripts/governance`).

### Phase 2: Logic Extraction
1.  Read the **OLD** source code to understand *functionality* (Business Logic, API calls, User Flows).
2.  **Ignore** the **OLD** styles. Do not copy CSS. Do not copy class names.
3.  Document the "Requirements" derived from the code.

### Phase 3: Assembly (The Build)
Rebuild the interface using Starlight Carbon Tokens.

- **Layout**: Use the `spacing` tokens (`spacing.05`, `spacing.07`) for margins/padding.
- **Colors**: Use **Semantic Tokens** (`layer.01`, `text.primary`, `interactive.01`).
    - ❌ **Forbidden**: `color: #333`, `background-color: white`
    - ✅ **Required**: `color: {text.primary}`, `background-color: {layer.01}`
- **Components**: Map functionality to Carbon Components (e.g., old "Grid" -> `DataTable`).

## 3. Validation
Before you finish, you must prove compliance.

1.  **Run Validator**: `npm run validate` (pointing to your new token usage if applicable, or just ensure you used the provided JSONs as source).
2.  **Self-Correction**: If you used a hardcoded hex value, the validator (or your own review) should catch it. **Fix it.**

## 4. Decision Matrix: When to Keep Old Code?

| Component State | Decision |
| :--- | :--- |
| Contains complex business algorithms | **Extract Logic** into a utility file (Keep TS/JS). |
| Contains generic UI Helpers | **Delete**. Use Carbon Utilities. |
| Custom CSS / SCSS files | **Delete**. |
| HTML Templates | **Delete**. Rewrite in JSX/TSX. |

> [!IMPORTANT]
> **Heuristic**: If it looks "kinda like" the old app, you might be doing it wrong. It should look like **IBM Carbon**.

---

## 5. Lifecycle Strategy (The Exit Plan)
The `starlight-governance-kit` folder is **Temporary Scaffolding**.

1.  **Phase 1 (Reconstruction)**: Keep the kit in your project (e.g., `/scripts/governance`). Commit it. Use it to bootstrap.
2.  **Phase 2 (Stabilization)**: Once the project hits 90% compliance, delete the local validator.
3.  **Phase 3 (Maturity)**: Install the official package: `npm install -D @starlight/governance` (when available).

**Do not modify the files in the kit.** If you need changes, request them from the Starlight Carbon Architect.
