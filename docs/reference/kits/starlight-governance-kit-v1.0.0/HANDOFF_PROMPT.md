# Standard Agent Handoff Prompt

**Context:** The Starlight Carbon Architect (SCA) has prepared/updated the Governance Kit.
**Target:** Any Builder/Implementation Agent.

---

## Instructions for the Agent
> [!IMPORTANT]
> The **Starlight Carbon Governance Kit** has been refreshed/deployed to the root of your workspace (typically in `/starlight-governance-kit`).
> 
> Your primary directive is to ensure 100% architectural compliance with the **Starlight Carbon Design System**.

### Required Actions
1.  **Initialize Context**: Open and read the `README.md` (Handoff Protocol) and `REMOTE_AUDIT.md` within the `starlight-governance-kit` directory.
2.  **Verify Setup**: Ensure the `validator/` dependency is linked or installed in your project.
3.  **Execute Task**: Proceed with your implementation/refactoring sub-tasks using ONLY the tokens provided in `tokens/*.json`.
4.  **Proof of Work**: Once complete, run `npm run collect-audit` within the kit and provide the resulting `compliance-evidence.json` to the Architect.

### Technical Constraint Summary
- **No Hardcoded Values**: All hex colors and pixel values must map to a Starlight Token.
- **Framework Standard**: Use `@carbon/react` (IBM Carbon v11) components where possible.
- **Drafting Drift**: If you find a gap in the tokens, you MUST draft a **Drift Report** using the provided template before proceeding.

**Status:** The system is live. Proceed with your assigned task.
