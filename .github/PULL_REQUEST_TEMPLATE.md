## Summary

What this change does and why, in two or three sentences.

## Linked issue

Closes #

## Version impact

PATCH, MINOR or MAJOR (see the versioning rules in CONTRIBUTING.md):

## Benchmark table changes

If any number in the benchmark table moved, list each change and say why. If nothing moved, write "No change".

| Caller | Variant type | Metric | Before | After | Change |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Reason for the change:

## Review checklist

- [ ] Linked issue
- [ ] `snakemake --lint` is clean
- [ ] `snakefmt --check` is clean
- [ ] `ruff` and `mypy` are clean
- [ ] `pytest` passed
- [ ] Test-profile workflow run passed
- [ ] Benchmark table changes are explained above (if accuracy moved, by how much and why)
- [ ] CHANGELOG.md entry added under Unreleased
- [ ] Docs updated (README, validation)
- [ ] No data files over 5 MB committed
- [ ] No credentials, tokens or keys committed
