# Frontend Test Gap Analysis Report

This report evaluates the `react-frontend-template` against 2026 industry standards for high-integrity, contract-first applications.

## 1. Contract & Type Integrity

### Gap: Decoupled SDK Mocks

Current tests manually mock SDK responses (e.g., in `UserTaskView.test.tsx`). If the backend `openapi.json` changes (property renames or type shifts), these mocks remain static, allowing tests to pass while the production UI crashes.

### Improvement: Schema-Driven Mocking

Transition from manual object mocks to **Type-Validated Factories**. By using the generated types from `@hey-api/openapi-ts` directly in mock definitions, TypeScript will catch contract drifts at compile-time.

**Recommended Pattern:**

```typescript
import { TodoPublic } from "../../client/types.gen";

// Type-safe factory ensures mock matches current OpenAPI schema
const createMockTodo = (overrides: Partial<TodoPublic> = {}): TodoPublic => ({
  id: "1",
  title: "Default Task",
  status: "pending",
  priority: "medium",
  created_at: new Date().toISOString(),
  ...overrides,
});

it("renders task details correctly", () => {
  const mockTodo = createMockTodo({ title: "Specific Task" });
  // ... test logic
});
```

---

## 2. Component Logic & UX States

### Gap: Asynchronous State Neglect

Components like `SuperAdminDashboard` and `UserTaskView` primarily test the "Happy Path" (successful data load). Loading, Empty, and Error states are largely untested.

### Improvement: Triple-State Verification

Every component fetching data must have explicit tests for `isLoading`, `isEmpty`, and `isError`.

**Recommended Pattern (Vitest/RTL):**

```typescript
it("displays empty state when no tasks are returned", async () => {
  vi.mocked(readTodosApiV1TodosGet).mockResolvedValue({ data: { data: [] } });
  render(<UserTaskView />);

  await waitFor(() => {
    expect(screen.getByText(/no tasks found/i)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /empty box/i })).toBeInTheDocument();
  });
});

it("displays FastAPI-specific error messages", async () => {
  vi.mocked(readTodosApiV1TodosGet).mockResolvedValue({
    error: { detail: "Database connection timeout" }
  } as any);

  render(<UserTaskView />);

  await waitFor(() => {
    expect(screen.getByText("Database connection timeout")).toBeInTheDocument();
  });
});
```

---

## 3. Security & Role-Based Access (RBAC)

### Gap: Missing Negative Permission Tests

Current tests verify that Admins _can_ see admin tools. They do not verify that standard Users _cannot_ see them or that the UI gracefully handles unauthorized API attempts.

### Improvement: Cross-Role Assertions

Implement a "Role Matrix" test suite for shared components.

**Recommended Pattern:**

```typescript
describe("RBAC UI Guards", () => {
  const roles = [Role.USER, Role.ADMIN, Role.SUPER];

  it.each(roles)("handles visibility for %s role", (currentRole) => {
    vi.mocked(useAuth).mockReturnValue({ role: currentRole, user: {} } as any);
    render(<AdminDashboardView />);

    if (currentRole === Role.USER) {
      expect(screen.queryByText("Provision Admin")).not.toBeInTheDocument();
    } else {
      expect(screen.getByText("Provision Admin")).toBeInTheDocument();
    }
  });
});
```

---

## 4. CI/CD Integration

### Gap: Loose Quality Gates

The current pipeline checks for API client sync but doesn't enforce coverage or strictly fail on type mismatches during the test phase.

### Improvement: Fail-Fast Coverage & Sync

Update `package.json` and `.github/workflows/frontend.yml` to enforce strict thresholds.

**GitHub Actions Enhancement:**

```yaml
- name: Run Tests with Strict Coverage
  run: npm run test:run
  env:
    # Fail if coverage drops below 92%
    VITEST_COVERAGE_THRESHOLD: 92

- name: Strict Type Check
  run: npm run type-check
```

---

## Summary of Immediate Actions

1. **[FIXED]** Created `src/lib/error-handler.test.ts` to validate FastAPI error mapping.
2. **[FIXED]** Updated `package.json` with 92% coverage thresholds.
3. **[PENDING]** Refactor `UserTaskView.test.tsx` to include Loading/Empty states.
4. **[PENDING]** Implement Role Matrix tests in `Sidebar.test.tsx`.
