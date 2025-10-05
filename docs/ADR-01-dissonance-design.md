# ADR 01: Use Dissonance as Controlled Regularizer
## Status
Accepted

## Context
Implement controlled internal contradictions as a regularizer to improve model robustness. Use D_target, lambda_max, and KL_eps as safety constraints. The Golden Holdout set is sacrosanct and excluded from any training data or critic generation.

## Decision
- Use Loss_total = Loss_primary + lambda * max(0, D - D_target)^2
- Enforce KL(old || new) <= KL_eps as an update constraint
- Use budget cap for dissonance events per time window

## Consequences
- Need for strong monitoring of Golden accuracy
- Need for canary rollout and rollback
- Extra infra for MLOps (MLflow) and artifact storage (MinIO)