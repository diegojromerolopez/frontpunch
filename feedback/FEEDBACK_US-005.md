# FEEDBACK_US-005: Noctifab Tool Evaluation Report

This report evaluates the performance, behavior, and limitations of the `noctifab` tool
during the attempt to implement User Story Five (US-005: Graceful Worker Shutdown &
Task Re-queueing) in the `frontpunch` codebase.

---

## 1. Summary of Execution

- **Target Specification**: `roadmap/US-005.md` (Graceful Worker Shutdown & Task Re-queueing)
- **Base Branch (Configured)**: `noctifab/feature-US-004`
- **Noctifab Binary**: `$HOME/bin/noctifab` (built from `feat/simplified-permission-profiles`)
- **Result**: **FAILED TO START**. The tool's planning phase was immediately blocked by a
  Gemini API daily quota error (HTTP 429) on the `gemini-2.5-pro` model. The daemon then
  entered a ~58-minute sleep to honour the API-provided `retryDelay`, making the tool
  completely non-operational for the duration of the session.
- **Code generated**: 0 lines
- **Tests written**: 0

---

## 2. What Went Well

### A. Pre-flight Checks Pass Cleanly

Noctifab's startup sequence correctly validated all external dependencies before spawning
the daemon:

```
Running pre-flight checks...
- Git CLI: OK
- Database connectivity (sqlite): OK
- LLM provider (gemini) ping: OK
- Sandbox mode (host): OK
Pre-flight checks passed successfully.
```

This structured pre-flight is well-designed and gives the user immediate confidence that
the environment is correctly set up before any long-running work begins.

### B. Correct API Backoff Behaviour

When the 429 was received, the daemon correctly read the `retryDelay` field from the
Google API's response body (`3526s ≈ 58m46s`) and backed off precisely that amount of
time rather than blindly hammering the API with exponential backoff. This is the correct
and respectful behaviour toward the provider's rate-limit headers.

### C. Structured Story Logging

The daemon created a dedicated per-story log file at
`.noctifab/logs/roadmap/US-005.log`, separate from the main daemon log. This separation
is a well-considered design choice for observability — operators can `tail -f` a single
story without wading through unrelated daemon events.

### D. Base Branch Update Was Smooth

Manually updating `config.yaml`'s `base_branch` from `noctifab/feature-US-001-clean`
to `noctifab/feature-US-004` was the correct operation to layer US-005 on top of all
prior work. The mechanism itself — a single field in a YAML file — is clear and simple.

---

## 3. What Went Wrong

### A. Silent Model Override: `gemini-1.5-pro` → `gemini-2.5-pro`

**The Issue**: The `config.yaml` file was explicitly set to `model: gemini-1.5-pro`.
However, the actual API call was made to `gemini-2.5-pro`. No warning or log message
informed the user of this substitution.

**Root cause confirmed in source** ([`helpers.go`](../../noctifab/pkg/infrastructure/llm/helpers.go#L39-L44)):

```go
func normalizeModel(model string) string {
    trimmed := strings.TrimPrefix(strings.ToLower(model), "models/")
    if trimmed == "" || trimmed == "gemini-1.5-pro" {
        return "gemini-2.5-pro"  // ← silent upgrade, no warning
    }
    return trimmed
}
```

**The Consequences**:
- `gemini-1.5-pro` is a legacy model that had essentially unlimited free-tier API quota.
- `gemini-2.5-pro` has a strict 1,000 requests/day free-tier limit, shared across all
  projects using the same API key.
- The previous US-001 through US-004 runs already exhausted this daily quota.
- US-005 was blocked on the very first API call with no actionable error for the user
  other than "wait 58 minutes."

**User Impact**: A developer who carefully configures `gemini-1.5-pro` to stay within
free-tier quotas gets silently upgraded to a model that exhausts quota in a single session,
then faces a full work-hour of downtime with no workaround.

---

### B. No Model Fallback Chain Activation

The `modelHierarchy` map in `helpers.go` defines a fallback chain for Gemini:

```go
"gemini": {
    "gemini-2.5-pro",
    "gemini-2.5-flash",   // ← this should activate on 429
},
```

The test file confirms this fallback is intended:
```
name: "gemini-2.5-pro falls back to gemini-2.5-flash"
```

However, in the actual run, **the fallback to `gemini-2.5-flash` did not trigger**.
Instead, the daemon printed a warning and slept for 58 minutes. This means either the
fallback code path is not connected to the 429 handler, or it only applies in certain
contexts (e.g. a different code path is used for the planner phase).

**The Consequences**: 58+ minutes of complete tool downtime for a condition that could
have been transparently handled by switching to the flash model.

---

### C. 58-Minute Hard Block During Planning — Tool Becomes Completely Unresponsive

**The Issue**: When the 429 hit during the planning phase, the daemon printed one warning
and then entered a 58-minute `time.Sleep`. During this entire window:
- The daemon did not respond to any commands.
- The REPL showed no progress indicators.
- There was no way to cancel the sleep and retry with a different model without killing
  the process.
- The daemon log received zero updates during the entire sleep period.

**The Consequences**: The tool is opaque and uncontrollable during a quota wait. A
developer cannot tell whether the tool is frozen, crashed, or actively waiting. The only
observable evidence that the daemon was alive was the `lsof` output showing an open file
handle. From the user's perspective, the tool is completely dead.

---

### D. No Interactive Override During Backoff

Related to the above: there was no way to send the daemon a command like:
```
> switch-model gemini-2.5-flash
```
or:
```
> abort-retry
```
to interrupt the sleep and proceed with a fallback model. The command channel
(`command_channel.go`) exists in the architecture but does not appear to be polled during
the backoff sleep.

---

### E. `config.yaml` `base_branch` Drift Requires Manual Intervention — Again

As documented in `FEEDBACK_US-004.md`, the `config.yaml` `base_branch` field does not
auto-update after each run. Before running US-005, `base_branch` was still pointing to
`noctifab/feature-US-001-clean` (from the initial setup). Manual editing was required to
set it to `noctifab/feature-US-004`.

This is a persistent UX friction point that becomes more acute as the number of completed
user stories grows. By US-010 or US-015, the engineer must remember the exact branch name
from the last successful run and manually update the YAML before each run.

---

### F. REPL `start` vs. `--input` Flag Inconsistency

Invoking `noctifab start --input roadmap/US-005.md` from the command line enters
**interactive REPL mode** and waits for input, even though `--input` was provided. The
user story is queued only after the operator manually types `start roadmap/US-005.md` at
the prompt:

```
noctifab ready. Type a command (e.g. 'start roadmap/US-0001.md' or 'status').
> ▶ Queuing user story: roadmap/US-005.md
```

This is confusing: passing `--input` at the CLI level suggests non-interactive operation,
but the daemon still blocks on an interactive prompt. The `start-one` subcommand exists
precisely for this non-interactive use-case, but `start --input` silently ignores the
flag until a human types in the REPL.

---

## 4. Proposals for Fixes

### Fix A: Remove the Silent `gemini-1.5-pro` → `gemini-2.5-pro` Upgrade

**Current behaviour**: `normalizeModel("gemini-1.5-pro")` silently returns `"gemini-2.5-pro"`.

**Proposed fix**:
```go
func normalizeModel(model string) string {
    trimmed := strings.TrimPrefix(strings.ToLower(model), "models/")
    if trimmed == "" {
        return modelHierarchy["gemini"][0] // use first in hierarchy as default
    }
    // Warn if a legacy model is encountered instead of silently upgrading
    legacyModels := map[string]string{
        "gemini-1.5-pro":   "gemini-2.5-pro",
        "gemini-1.5-flash": "gemini-2.5-flash",
    }
    if replacement, ok := legacyModels[trimmed]; ok {
        log.Warnf("Model %q is deprecated. Upgrading to %q. Update your config.yaml to suppress this warning.", trimmed, replacement)
        return replacement
    }
    return trimmed
}
```

The warning allows the user to make a conscious choice rather than being surprised by
unexpected quota exhaustion.

---

### Fix B: Wire the Model Fallback Chain to the 429 Handler

The `modelHierarchy` map and the test coverage for fallback suggest the intent exists.
The implementation needs to activate the fallback on `RESOURCE_EXHAUSTED`:

```go
// In the LLM retry loop:
case http.StatusTooManyRequests:
    nextModel := getNextFallbackModel(currentModel, provider)
    if nextModel != "" {
        log.Warnf("Quota exhausted for %q. Falling back to %q.", currentModel, nextModel)
        currentModel = nextModel
        continue // retry immediately with new model
    }
    // Only sleep if no fallback model is available
    sleepDuration := parseRetryDelay(resp)
    log.Warnf("No fallback model available. Sleeping %s as requested by API.", sleepDuration)
    time.Sleep(sleepDuration)
```

This would have allowed US-005 to proceed immediately using `gemini-2.5-flash` without
any human intervention or wait.

---

### Fix C: Poll Command Channel During Backoff Sleep

Replace the raw `time.Sleep(retryDelay)` with a select-based interruptible wait:

```go
select {
case <-time.After(retryDelay):
    // Backoff complete, retry
case cmd := <-commandChannel:
    // Process urgent operator command (e.g. switch-model, abort)
    handleCommand(cmd)
case <-ctx.Done():
    return ctx.Err()
}
```

This would allow the operator to type `switch-model gemini-2.5-flash` or `abort` at the
REPL during the backoff window, and the daemon would respond immediately.

---

### Fix D: Auto-Advance `base_branch` After Successful Run

After a story is successfully completed and merged, noctifab should write the new
integration branch name back into `config.yaml`:

```go
// After successful PR merge:
cfg.VCS.BaseBranch = state.Metadata.IntegrationBranch
if err := cfg.WriteToFile(".noctifab/config.yaml"); err != nil {
    log.Warnf("Could not auto-update base_branch in config.yaml: %v", err)
}
```

Alternatively, expose a `noctifab set-base <branch>` command that the operator can call
after verifying a run succeeded, reducing the mental overhead of manually tracking which
branch to build on top of.

---

### Fix E: Honour `--input` Flag as Non-Interactive `start-one` Equivalent

When `noctifab start --input <path>` is invoked from the shell, automatically queue the
story and begin execution without waiting for REPL input:

```go
if cfg.Input != "" {
    // Non-interactive: queue the story immediately and run
    if err := daemon.QueueStory(cfg.Input); err != nil {
        return err
    }
    return daemon.WaitForCompletion()
}
// Otherwise: enter interactive REPL
return runREPL(daemon)
```

This makes `start --input` behave identically to `start-one` for scripting and CI use-cases.

---

## 5. Observations on the noctifab Architecture

### A. `helpers.go` Contains Hard-Coded Business Logic for a Specific Project

The `getProjectContext()` function in `helpers.go` contains explicit strings like
`"frontpunch"`, `"todo_app"`, directory paths, and project-specific CRITICAL instructions
baked directly into the binary:

```go
func getProjectContext() projectContext {
    ctx := projectContext{
        PackageName: "frontpunch",
        Instructions: "2. The package name is 'frontpunch'. All implementation files
            MUST be created or modified inside the 'frontpunch/' directory...",
        ...
    }
    if strings.Contains(specStr, "Todo CLI") {
        ctx.PackageName = "todo_app"
        ...
    }
    return ctx
}
```

This is a significant architectural concern: the general-purpose dark factory platform
is hard-coded for specific known projects it has been tested on. New projects that don't
match these patterns will not receive these CRITICAL prompt injections, leading to
potentially different (and likely worse) code generation quality. The fix is to move
these project-specific instructions into the `.noctifab/config.yaml` or a
`.noctifab/context.md` file that is read at runtime, making the binary truly general-purpose.

### B. The `--llm-model` CLI Default Is `gpt-4o`, Not `gemini-*`

The `--help` output shows:
```
-m, --llm-model string   LLM Model Identifier (default "gpt-4o")
```

But the config uses `provider: gemini`. The CLI default and the YAML default are
mismatched. A user who doesn't specify `--llm-model` on the CLI expects the YAML's
`model: gemini-1.5-pro` to take effect, which it does — but the silent upgrade then
changes it. The compounded effect of two non-obvious overrides (CLI default → YAML
override → silent normalization upgrade) makes model selection extremely hard to reason
about.

---

## 6. Roadmap to Level 4 Autonomy

In addition to the fixes proposed above, the following capabilities are needed before
noctifab can operate as a true Level 4 Dark Factory:

### 1. Multi-Provider Failover

Configure fallback across providers, not just models:
```yaml
llm:
  provider: gemini
  model: gemini-2.5-pro
  fallbacks:
    - provider: anthropic
      model: claude-3-5-haiku-latest
    - provider: openai
      model: gpt-4o-mini
```

This way, even a full daily quota exhaustion on one provider does not block all work.

### 2. Quota Budget Tracking Across Sessions

Add a persistent token/request counter per model per calendar day in the SQLite database.
Before making an LLM call, check if the daily budget for that model is near exhaustion
and proactively switch to the fallback model before hitting a 429.

### 3. Real-Time Progress Reporting via REPL

During active task execution, the REPL should stream live status lines:
```
[Task 1/4] Implement signal handlers... ✓  (12s, 1,203 tokens)
[Task 2/4] Write unit tests for shutdown... ⟳ (running)
```
Currently the operator has no visibility into what the daemon is doing between log file
reads.

### 4. Resumable Sessions

If the daemon is killed mid-run (e.g., by SIGKILL or power loss), it should be possible
to run `noctifab resume` to pick up from the last successful task checkpoint rather than
starting the entire planning cycle from scratch.

---

## 7. Adoption Assessment: Can a user leverage Noctifab today?

### Verdict: **Not yet — blocked by infrastructure fragility (Level 2, with caveats)**

**Capability**:
Noctifab's architecture is sound and its previous US-001 through US-004 results showed
genuine ability to plan, implement, and test well-scoped Python features. The tool is
conceptually mature.

**For US-005 specifically**:
The feature requested — graceful signal handling with `threading.Event`, timeout-based
grace periods, and Redis re-queuing via `LPUSH` — is well within the capability of any
modern LLM code generator. The implementation would have been straightforward. The failure
was entirely due to infrastructure issues (quota exhaustion + silent model override), not
any limitation of the LLM's coding ability.

**Key Blockers for Adoption**:

| Blocker | Severity | Status |
|---|---|---|
| Silent `gemini-1.5-pro` → `gemini-2.5-pro` model upgrade | 🔴 Critical | Unresolved |
| No model fallback on 429 | 🔴 Critical | Unresolved |
| 58-minute uninterruptible sleep on quota exhaustion | 🔴 Critical | Unresolved |
| `base_branch` drift requires manual YAML edits between runs | 🟡 High | Unresolved |
| `--input` flag does not suppress REPL prompt | 🟡 Medium | Unresolved |
| Project-specific logic hard-coded in binary | 🟡 Medium | Unresolved |

**Recommendations for Developers Evaluating Noctifab Today**:

1. **Use a paid LLM API plan** with a high daily quota, or configure a provider with
   no hard daily limit (e.g. Anthropic, OpenAI with billing enabled) to avoid the 429
   block entirely.
2. **Use the `start-one` subcommand** rather than `start --input` for scripted, CI-style
   invocations to avoid the interactive REPL ambiguity.
3. **Always manually verify `base_branch`** in `config.yaml` before each run, confirming
   it points to the branch from the last successfully merged user story.
4. **Monitor `.noctifab/logs/roadmap/<story>.log`** in real-time with `tail -f` rather
   than waiting for the REPL to print a result, as the REPL output lags significantly
   behind the actual daemon state.
5. **Do not run consecutive user stories in the same calendar day** if using the free
   Gemini tier — each story consumes hundreds of API requests and the 1,000 req/day
   limit is exhausted quickly.

**Bottom line**: Noctifab is a promising tool that is capable of generating correct code
for well-scoped Python tasks, but it cannot be used reliably for day-to-day feature
development until the silent model upgrade, 429 fallback, and REPL/non-interactive mode
issues are resolved. The recommended adoption path is **Level 2 (interactive assistant)**:
run noctifab on isolated task branches, review every commit manually, and treat its output
as a high-quality first draft rather than production-ready code.
