# Phase 3: Concurrent Registration - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning
**Mode:** Codebase analysis + requirements

<domain>
## Phase Boundary

Параллельная регистрация на多个 платформах — parallel task execution, worker pool, task prioritization, resource-aware limits.

</domain>

<decisions>
## Implementation Decisions

### 1. Parallel Task Execution
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Keep existing threading | Simple, works | Limited scalability | ✅ Optimize first |
| Add asyncio for tasks | Modern, scalable | Requires major refactor | ❌ Too much change |
| Celery/RQ | Production-ready | External dependency | ❌ Overkill for now |

**Decision:** Optimize existing threading model, add priority queue and resource-aware limits.

### 2. Worker Pool
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Keep custom TaskRuntime | Already works | Not standard | ✅ Enhance with priority |
| Use ThreadPoolExecutor | Standard Python | Less control | ⏳ Future refactor |
| Use ProcessPoolExecutor | True parallelism | IPC complexity | ❌ Not needed |

**Decision:** Enhance existing TaskRuntime with priority queue and resource tracking.

### 3. Task Prioritization
| Priority Levels | Use Case | Implementation |
|-----------------|----------|----------------|
| HIGH | Urgent registrations, retries | Priority field on TaskModel |
| NORMAL | Standard registrations | Default priority |
| LOW | Batch jobs, background checks | Lowest priority |

**Decision:** Add priority field to TaskModel, use priority queue in dispatcher.

### 4. Resource-Aware Limits
| Resource | Limit | Enforcement |
|----------|-------|-------------|
| Global tasks | Configurable (default 3) | TaskRuntime.max_parallel_tasks |
| Per-platform | Configurable (default 1) | claim_next_runnable_task() |
| Per-account | 1 (serialized) | Account key locking |
| Per-task concurrency | Configurable (default 1, max 5) | ThreadPoolExecutor |

**Decision:** Keep existing limits, add resource monitoring and dynamic adjustment.

</decisions>

<code_context>
## Existing Code Insights

### Current Task Execution Model
- **TaskRuntime:** `services/task_runtime.py` — Custom dispatcher with worker threads
- **TaskRunner:** `application/tasks/task_runner.py` — Inner ThreadPoolExecutor for registrations
- **TaskRepository:** `application/tasks/task_repository.py` — FIFO claiming, no priority
- **TaskScheduler:** `application/tasks/task_scheduler.py` — Retry mechanism

### Current Concurrency Control
- **Global limit:** 3 tasks max (task_runtime.py:22)
- **Per-platform:** 1 task max (task_runtime.py:24)
- **Per-account:** Serialized via account key locking
- **Per-task:** 1-5 concurrent registrations (task_runner.py:344)

### Current Patterns to Enhance
1. **Priority queue:** Currently FIFO, need priority-based ordering
2. **Resource monitoring:** Currently static limits, need dynamic adjustment
3. **Worker pool:** Currently custom dict of threads, need better management
4. **Task scheduling:** Currently polling-based, need event-driven option

### Key Files to Modify
1. `core/db/models.py` — Add priority field to TaskModel
2. `services/task_runtime.py` — Enhance with priority queue
3. `application/tasks/task_repository.py` — Priority-based claiming
4. `application/tasks/task_runner.py` — Resource-aware execution

</code_context>

<specifics>
## Specific Ideas

### Phase 3 Deliverables
1. **CONC-01:** Parallel task execution across platforms (optimize existing threading)
2. **CONC-02:** Worker pool for concurrent registrations (enhance TaskRuntime)
3. **CONC-03:** Task prioritization and scheduling (add priority queue)
4. **CONC-04:** Resource-aware concurrency limits (dynamic adjustment)

### Key Changes
- `core/db/models.py` — Add priority field to TaskModel
- `services/task_runtime.py` — Priority queue, resource tracking
- `application/tasks/task_repository.py` — Priority-based claiming
- `application/tasks/task_runner.py` — Resource-aware execution
- `core/db/migrations.py` — Add priority column migration

### Success Criteria
1. Tasks execute in priority order (HIGH > NORMAL > LOW)
2. Worker pool manages threads efficiently
3. Resource limits are enforced and monitored
4. System handles increased load without degradation

</specifics>

<deferred>
## Deferred Ideas

- **Asyncio task execution** — Major refactor, future milestone
- **External task queue (Celery/RQ)** — Overkill for current scale
- **ProcessPoolExecutor** — IPC complexity, not needed yet

</deferred>
