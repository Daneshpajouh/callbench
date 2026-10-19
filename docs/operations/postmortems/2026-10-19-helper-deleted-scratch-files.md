# Postmortem: a helper deleted files outside the repository

Date: 2026-10-19. Author: Amir Daneshpajouh.

A helper deleted files in a scratch folder outside the repository; contents
were temporary.

## Rule adopted

Nothing outside this repository is deleted, and nothing is deleted with a
wildcard. Unwanted files are moved into a discards folder instead.
