# Scrubbing Sensitive History (manual step)

This repository may contain sensitive files (cookies, credentials, builds) in previous history. Rewriting git history is destructive and will require a forced push, which affects all collaborators.

DO NOT RUN THESE UNLESS YOU UNDERSTAND THE RISKS.

Recommended approach using `git filter-repo` (preferred over BFG):

1. Install `git-filter-repo` (follow the official instructions).
2. Run (example to remove `www.youtube.com_cookies.txt` and `startpageshared_cookies.txt`):

```bash
git clone --mirror https://github.com/USERNAME/REPO.git
cd REPO.git
git filter-repo --invert-paths --paths startpageshared_cookies.txt --paths www.youtube.com_cookies.txt
git push --force --all
git push --force --tags
```

If you prefer the BFG Repo-Cleaner, see: https://rtyley.github.io/bfg-repo-cleaner/

If you want, I can prepare an exact scrub plan and run it for you — reply with `CONFIRM SCRUB` to proceed and include the exact filenames to remove from history.
