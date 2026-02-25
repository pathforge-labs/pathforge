# Root Cause Tracing — Backward Call Stack Analysis

> **Purpose**: When a bug manifests deep in the call stack, trace backward to find the **original trigger** rather than patching the symptom.

---

## The Technique

Instead of fixing where the error appears, trace the bad value **backward** through the call chain until you find where it was first introduced.

### Step-by-Step

1. **Start at the error site** — note the exact bad value (null, wrong type, missing key)
2. **Identify the caller** — who passed this value? Check the function signature and the call site
3. **Trace one level up** — is the bad value computed here, or passed from further up?
4. **Repeat** until you find the **source** — the place where the value was first created incorrectly
5. **Fix at the source** — not at the symptom

---

## Example: FastAPI → Service → DB

```python
# ❌ Error appears here (Layer 3 — DB query)
# sqlalchemy.exc.IntegrityError: NOT NULL constraint on career_dna_id
async def create_simulation(self, session: AsyncSession, data: SimulationCreate) -> CareerSimulation:
    simulation = CareerSimulation(**data.model_dump())  # career_dna_id is None!
    session.add(simulation)
    ...

# Trace backward to Layer 2 — Service method
# Who calls create_simulation and what does it pass?
async def run_simulation(self, user_id: UUID, request: RunSimulationRequest) -> SimulationResponse:
    career_dna = await self._get_career_dna(session, user_id)
    data = SimulationCreate(
        career_dna_id=career_dna.id if career_dna else None,  # ← BUG: allows None
        ...
    )
    return await self.create_simulation(session, data)

# Trace backward to Layer 1 — API endpoint
# Should the endpoint guard against missing Career DNA?
@router.post("/simulate")
async def simulate(request: RunSimulationRequest, current_user: User = Depends(get_current_user)):
    return await service.run_simulation(current_user.id, request)
    # No pre-check for Career DNA existence!

# ✅ Fix at the SOURCE (Layer 2 — Service), not at Layer 3
async def run_simulation(self, user_id: UUID, request: RunSimulationRequest) -> SimulationResponse:
    career_dna = await self._get_career_dna(session, user_id)
    if career_dna is None:
        raise HTTPException(status_code=400, detail="Career DNA profile required before simulation")
    ...
```

---

## Example: React Hook → Provider → Token Manager

```typescript
// ❌ Error appears here (Layer 3 — API call)
// 401 Unauthorized on every request after page refresh

// Trace to Layer 2 — Hook
const { data } = useCareerDNA();
// useCareerDNA calls fetchWithAuth → which reads token from tokenManager

// Trace to Layer 1 — Token Manager
// getAccessToken() returns null after page refresh
// Because: token was stored in memory only, not restored from localStorage on init

// ✅ Fix at the SOURCE (Token Manager init), not in the hook or API layer
```

---

## When to Use

- Error message points to a low-level layer (DB, file system, external API)
- The bad value is clearly wrong but you don't know where it was introduced
- Multiple layers of abstraction between the trigger and the symptom
- Fixing the symptom would require adding a workaround (null check, try/catch)

## Key Principle

> **Fix at the source, not at the symptom.** A null check at the crash site hides the bug — finding out why it's null prevents the entire class of failure.
