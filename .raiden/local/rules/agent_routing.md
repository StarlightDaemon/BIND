# Agent Routing Rule — Do It Here vs. Handoff

When a code change is needed, choose the execution path based on cost, not habit.

## Do it in the current Claude session when:
- The relevant files are already read and in context this session
- The change is ≤ ~20 lines across ≤ 2 files
- No design ambiguity — the what and where are already known
- Prompt-writing overhead would exceed the edit itself

Writing a Gemini/Claude prompt, the agent reading it, and reviewing the diff
costs more total tokens than just making the edit when the context is already warm.

## Hand off to Gemini 3.1 Pro when:
- Change spans 3+ files or requires reading files not yet in context
- Moderate design judgment needed (cross-file consistency, interface decisions)
- The operator wants an independent implementation without Claude's context
- Current session context is nearly full

## Hand off to Gemini 3 Flash when:
- Purely mechanical: rename, extract, move, reorder
- Pattern is explicit and repetitive (no judgment required)
- Single file, clear before/after spec

## Hand off to a second Claude agent when:
- Architectural judgment required (design trade-offs, test strategy)
- Test authoring for complex business logic
- The task benefits from a fresh context with no prior assumptions

## Default model names (always use these exactly):
- `Gemini 3.1 Pro` — moderate/complex multi-file work
- `Gemini 3 Flash` — mechanical single-file refactors
- `Claude Sonnet 4.6` — architectural judgment, test authoring

Never use Gemini 2.x model names. Training data cutoff predates the current
Gemini generation; always use what the operator specifies.
