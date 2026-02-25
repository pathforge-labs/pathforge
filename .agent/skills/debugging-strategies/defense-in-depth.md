# Defense in Depth — Multi-Layer Validation

> **Purpose**: After finding and fixing a root cause, add validation at multiple layers to prevent the same class of bug from recurring.

---

## The Technique

A single fix addresses the immediate bug. Defense in depth ensures the **entire category** of similar failures is caught at multiple boundaries.

### Strategy

After fixing the root cause, add guards at **each layer boundary**:

| Layer             | Guard Type          | Example                                          |
| :---------------- | :------------------ | :----------------------------------------------- |
| API (input)       | Schema validation   | Pydantic model with `Field(ge=0, le=100)`        |
| Service (logic)   | Precondition checks | `if career_dna is None: raise`                   |
| DB (storage)      | Constraints         | `CheckConstraint("confidence <= 0.85")`          |
| Test (prevention) | Regression test     | `test_simulation_without_career_dna_returns_400` |

---

## Example: Confidence Score Overflow

After discovering that LLM-generated confidence scores can exceed 0.85:

```python
# Layer 1: API — Pydantic schema validation
class SimulationResponse(BaseModel):
    confidence: float = Field(ge=0.0, le=0.85, description="Confidence score, capped at 0.85")

# Layer 2: Service — Clamping in business logic
def _clamp_confidence(self, raw_score: float) -> float:
    return min(max(raw_score, 0.0), MAX_SIMULATION_CONFIDENCE)

# Layer 3: DB — CHECK constraint in migration
sa.CheckConstraint("confidence <= 0.85", name="ck_simulation_confidence_cap")

# Layer 4: Test — Regression test
async def test_confidence_cannot_exceed_cap():
    result = service._clamp_confidence(0.99)
    assert result == 0.85
```

---

## When to Apply

- After fixing any bug related to **data integrity** (values out of range, null where required, wrong types)
- After fixing **security issues** (input injection, auth bypass, privilege escalation)
- After fixing **state management bugs** (race conditions, stale data, inconsistent state)
- When the root cause involved **missing validation** at any layer

## Key Principle

> **One layer's check should never be the only thing preventing a category of failure.** Each layer should independently validate its invariants.
