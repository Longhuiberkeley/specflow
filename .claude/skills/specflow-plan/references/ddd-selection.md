# DDD Selection Decision Tree

Use this checklist during plan Step 4 to decide whether an ARCH component needs a DDD (Detailed Design Document).

## The 6-Question Decision Checklist

For each ARCH component, answer these questions:

### 1. Does it contain a state machine?
If the component transitions between discrete states with rules governing transitions, a DDD is needed to specify states, transitions, guards, and actions.

**Examples:** workflow engines, order status machines, protocol handlers, session managers.

### 2. Does it perform non-trivial data transformations?
If the component converts, maps, filters, or aggregates data beyond simple CRUD operations, a DDD should specify input schemas, output schemas, transformation rules, and edge cases.

**Examples:** ETL pipelines, report generators, data normalizers, format converters.

### 3. Does it implement an external protocol or interface?
If the component communicates with an external system using a defined protocol (API, file format, message bus), a DDD should document the protocol details, message formats, error codes, and versioning strategy.

**Examples:** REST API clients, message queue consumers, file format parsers, authentication integrations.

### 4. Does it contain complex calculations or algorithms?
If the component implements logic where correctness depends on mathematical properties, algorithmic complexity, or domain-specific rules, a DDD should specify the algorithm, complexity bounds, and validation approach.

**Examples:** pricing engines, scheduling algorithms, scoring systems, constraint solvers.

### 5. Does it manage concurrent access to shared resources?
If multiple actors (threads, processes, users) access shared state, a DDD should specify locking strategy, isolation levels, deadlock prevention, and consistency guarantees.

**Examples:** connection pools, cache managers, file locks, distributed locks.

### 6. Does it implement error recovery or resilience logic?
If the component must detect failures, retry operations, circuit-break, or gracefully degrade, a DDD should specify failure modes, recovery strategies, and backoff policies.

**Examples:** retry wrappers, circuit breakers, fallback handlers, transaction managers.

## Decision Rules

- **All answers NO** → The ARCH's interface-level description is sufficient. No DDD needed. The component is simple enough that its ARCH captures all necessary detail.
- **Any answer YES** → A DDD artifact is recommended. The YES answers identify which sections the DDD should prioritize.

## DDD Section Mapping

| Question answered YES | DDD sections to include |
|-----------------------|------------------------|
| State machine | Data Structures (state model), Algorithm (transition logic), Invariants (state constraints) |
| Data transformation | Data Structures (input/output schemas), Algorithm (transformation rules), Error Handling |
| External protocol | Function Signatures (protocol API), Error Handling (protocol errors), Preconditions |
| Complex calculations | Algorithm (with complexity analysis), Invariants (mathematical properties), Preconditions |
| Concurrent access | Data Structures (shared state), Invariants (consistency guarantees), Error Handling (deadlock/timeout) |
| Error recovery | Algorithm (recovery logic), Error Handling (failure catalog), Preconditions (retry conditions) |

## Anti-Patterns to Avoid

- **Creating DDDs for simple CRUD components** — if the ARCH already fully describes the component's behavior, a DDD adds noise.
- **Skipping DDDs for "obvious" algorithms** — if it took you 10 minutes to explain how it works to a colleague, it needs a DDD.
- **DDD content that duplicates the ARCH** — DDDs add implementation-level detail (signatures, data structures, error handling), not structural description.
