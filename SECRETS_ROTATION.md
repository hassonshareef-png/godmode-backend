# Steps to purge sensitive files from git history

This file explains how to remove sensitive files (like DIRECTOR_MODE_SETUP.md)
from your repository's history. These operations rewrite history and are
destructive. Coordinate with all collaborators and rotate exposed credentials
immediately.

Recommended: use git-filter-repo (fast, supported)

1) Install git-filter-repo
   pip install git-filter-repo

2) Create a backup (optional but recommended)
   git clone --mirror https://github.com/OWNER/REPO.git repo-backup.git

3) Remove the file from history
   git clone https://github.com/OWNER/REPO.git repo-clean
   cd repo-clean
   git filter-repo --invert-paths --path DIRECTOR_MODE_SETUP.md

4) Force-push the cleaned repo (destructive)
   git remote add origin-clean https://github.com/OWNER/REPO.git
   git push origin-clean --force --all
   git push origin-clean --force --tags

5) Ask collaborators to re-clone the repo (their histories will diverge otherwise):
   git clone https://github.com/OWNER/REPO.git

Alternative: BFG Repo-Cleaner (Java-based) — see BFG docs.

After history rewrite:
- Rotate any exposed passwords, tokens, pins, and DB credentials.
- Check CI secrets and webhook tokens; rotate if necessary.

