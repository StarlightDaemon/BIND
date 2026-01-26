# BIND CircuitBreaker Precedence Fix (v1.2.1)

**Date**: 2026-01-26
**Version**: v1.2.1 (Maintenance)
**Scope**: Bugfix (CircuitBreaker Initialization Logic)
**Status**: **FIXED & VERIFIED**

---

## 1. Executive Summary

A logic bug was identified in the `CircuitBreaker` class where environment variables were incorrectly overriding explicit constructor arguments. This caused tests that relied on custom thresholds or cooldowns to fail when global configuration was present in the environment. This fix restores the correct precedence order: **Explicit Arguments > Environment Variables > Defaults**.

## 2. Root Cause

In the original implementation of `CircuitBreaker.__init__`, the constructor arguments were used as the *default* values for `os.getenv`. This meant that if an environment variable was set (e.g., in a production environment or a stale CI session), it would always override whatever was passed to the constructor, breaking isolation for unit tests and granular configuration control.

## 3. Fix Description

The `CircuitBreaker.__init__` method was updated to use `Optional` (None) defaults in the method signature. This allows the logic to explicitly detect if a value was provided by the caller.

**New Logic**:
- If a value is passed to `__init__`, use it (Highest Priority).
- If no value is passed, check `os.environ` for `CIRCUIT_BREAKER_THRESHOLD` or `CIRCUIT_BREAKER_COOLDOWN`.
- If neither is present, fall back to hardcoded defaults (3 failures, 300s cooldown).

## 4. Verification Evidence

### 4.1 Unit Testing
*   **Command**: `pytest -k circuit_breaker`
*   **Result**: All 6 circuit breaker tests passed, including the previously failing `test_cooldown_allows_retry`.
*   **Regression**: Reverted previous test-layer workarounds (mocking environment) to confirm the logic fix is sufficient.

### 4.2 Integration Testing
*   **Command**: `pytest`
*   **Result**: **39/39 tests passed (100%)**.

### 4.3 Code Quality
*   **Command**: `ruff check src/ tests/`
*   **Result**: No linting issues found.

## 5. Scope Confirmation

*   **Version**: Remaining at **v1.2.1**.
*   **Features**: No new features introduced.
*   **Stability**: Fix specifically improves CI stability and runtime configuration reliability.

---

**Signed**: BIND Maintenance & CI Stabilization Agent
