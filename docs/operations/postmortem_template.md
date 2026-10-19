# Postmortem: <short title of the incident>

Copy this file to `docs/operations/postmortems/YYYY-MM-DD-short-title.md`, where the date is the day the incident started. Fill in every section. If a section does not apply, write "None" and say why.

This postmortem is blameless. Describe what the systems, the workflow and the process did and what we know about why, not who made a mistake. People acted on the information they had at the time; the question is what let that information be wrong or missing.

Do not include credentials, tokens or non-public sample data.

| Field | Value |
| --- | --- |
| Incident start | YYYY-MM-DD HH:MM Pacific (UTC offset) |
| Incident end | YYYY-MM-DD HH:MM Pacific (UTC offset) |
| Author | |
| Date written | YYYY-MM-DD |
| Status | Draft, reviewed or closed |
| Affected versions | Release tags or commits |
| Linked issue and pull requests | |

## Summary

Three to five sentences. What went wrong, how long it lasted, who or what was affected, and how it was fixed. A reader who stops here should know the outcome.

## Impact

State the effect in measurable terms.

- Runs affected: which samples, profiles and releases, and how many runs.
- Outputs affected: which files or tables were missing, wrong or late. For a benchmark table, give the values that were wrong and the correct values.
- Published results affected: whether any report, release or document carried a wrong number, and whether it has been corrected.
- Duration: from the first affected run to the last.
- Data exposure: whether any credential or non-public data was involved. Write "None" if not.

## Timeline

Use absolute dates and Pacific time with the UTC offset. Include the events before the incident that mattered, such as the change that introduced the fault. Add one row per event, in order.

| Date | Time (Pacific, with UTC offset) | Event |
| --- | --- | --- |
| YYYY-MM-DD | HH:MM (UTC offset) | The change that introduced the fault was merged. |
| YYYY-MM-DD | HH:MM (UTC offset) | The first affected run started. |
| YYYY-MM-DD | HH:MM (UTC offset) | The problem was noticed. |
| YYYY-MM-DD | HH:MM (UTC offset) | The fix was merged. |
| YYYY-MM-DD | HH:MM (UTC offset) | The fix was verified (see below). |

## Detection

- How was the problem found: a failed rule, a failed check, a reviewer, a user report, or a number that looked wrong?
- How long after it began was it found?
- What check should have caught it earlier, and why did it not? Name the test, lint rule, review step or monitoring gap.

## Root cause

Describe the mechanism: the sequence from the original change or condition to the symptom. Then list the contributing conditions that allowed it, such as a missing test, an unpinned tool version, an unclear contract or a review that did not cover the affected path.

Stop at causes that the project can change. "A person was careless" is not a root cause.

## What went well

List the things that limited the damage or sped up recovery: a log that named the failing rule, a pinned environment that made the run reproducible, a quick revert, a clear contract that showed what was wrong.

## What went badly

List the things that made the incident longer or worse: a missing test, a vague error message, a slow feedback loop, an undocumented assumption, a release that went out before a check was run.

## Action items

Each action has one owner and a due date. Mark each as prevent (stops the cause), detect (finds it sooner) or mitigate (reduces the harm). Link the issue that tracks it.

| Action | Type | Owner | Due date | Issue | Status |
| --- | --- | --- | --- | --- | --- |
| | Prevent, detect or mitigate | | YYYY-MM-DD | # | Open |

## How the fix was verified

Give enough detail that someone else can repeat the check.

- The change that fixed it (pull request and commit).
- The test added or changed so the fault cannot return, and the command that runs it.
- The commands run after the fix (`make lint`, `make test`, `make test-workflow`) and their results.
- For a benchmark or accuracy fault: the vcfeval numbers before and after on HG002, and confirmation that the corrected table matches the expected values.
- The release that carries the fix, and the CHANGELOG entry that records it.

## Related links

- Issue:
- Pull requests:
- CHANGELOG entry:
- Earlier postmortems with the same cause:
