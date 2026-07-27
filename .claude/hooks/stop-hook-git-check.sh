#!/bin/bash
#
# Copia corretta dello Stop hook di Claude Code sul web. L'originale vive in
# ~/.claude/stop-hook-git-check.sh, fuori dal repo, e l'ambiente lo riscrive a
# ogni avvio di sessione: per questo la correzione sta qui e session-start.sh la
# reinstalla ogni volta, ma solo finche' l'originale ha ancora il difetto.
#
# Rispetto all'originale cambiano due controlli, commentati sotto nel punto in
# cui mordono: la presenza della firma si legge dall'header gpgsig e non da %G?,
# e i commit non pushati si contano contro tutti i rami remoti invece che contro
# un solo upstream indovinato.

# Read the JSON input from stdin
input=$(cat)

# Check if stop hook is already active (recursion prevention)
stop_hook_active=$(echo "$input" | jq -r '.stop_hook_active')
if [[ "$stop_hook_active" = "true" ]]; then
  exit 0
fi

# Check if we're in a git repository - bail if not
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  exit 0
fi

# Bail if there's no remote to push to. Every error path below asks the user
# to "push to the remote branch" — meaningless without a remote, and
# unsatisfiable if signing also requires a source. This case arises when CCR
# was launched against a local repo with no github remote (sources=[]) and
# the container's cwd has a leftover .git from a cached resume.
if [[ -z "$(git remote)" ]]; then
  exit 0
fi

# Check for uncommitted changes (both staged and unstaged)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "There are uncommitted changes in the repository. Please commit and push these changes to the remote branch." >&2
  exit 2
fi

# Check for untracked files that might be important
untracked_files=$(git ls-files --others --exclude-standard)
if [[ -n "$untracked_files" ]]; then
  echo "There are untracked files in the repository. Please commit and push these changes to the remote branch." >&2
  exit 2
fi

current_branch=$(git branch --show-current)
if [[ -n "$current_branch" ]]; then
  # "Local" means: reachable from HEAD and from no remote-tracking ref at all.
  #
  # This used to resolve one upstream (origin/<branch>, else origin/HEAD) and
  # diff against it, which was wrong twice. A fresh CCR clone has no origin/HEAD,
  # so on a never-pushed branch every rev-list below failed and the `|| unpushed=0`
  # swallowed the error: the check went silent in exactly the case it exists for.
  # And a commit pushed to a DIFFERENT branch than the current one (the user asks
  # for master while HEAD sits on a feature branch) still counted as unpushed,
  # because origin/<branch> had never heard of it. `--not --remotes` asks the
  # question that actually matters: is this commit anywhere on the remote yet?
  mapfile -t local_commits < <(git log --format='%H %h %ce' HEAD --not --remotes 2>/dev/null)

  # Check for local commits that GitHub will show as "Unverified": either no
  # signature at all, or signed with a committer email other than
  # noreply@anthropic.com (the identity CCR's signing key is registered to).
  # Only run when commit signing is configured.
  #
  # Signature presence comes from the raw commit header, NOT from %G?. CCR signs
  # with SSH and does not configure gpg.ssh.allowedSignersFile, so git aborts
  # verification before it can classify anything and reports N, the same N as a
  # genuinely unsigned commit. (The B/U/E codes the old check relied on come from
  # GPG signatures whose key is unavailable. They never appear for SSH.) The
  # result was a hook that flagged every correctly signed commit it ever saw, and
  # asked for an --amend that could not change the outcome.
  if [[ "$(git config --type=bool commit.gpgsign 2>/dev/null)" == "true" ]]; then
    unverifiable=""
    for entry in "${local_commits[@]}"; do
      read -r sha short email <<<"$entry"
      [[ -z "$sha" ]] && continue
      # Stop at the first blank line: everything after it is the commit message,
      # where a quoted "gpgsig" would otherwise read as a signature.
      if ! git cat-file commit "$sha" | sed -n '/^$/q;p' | grep -q '^gpgsig '; then
        unverifiable+="$short unsigned $email"$'\n'
      elif [[ "$email" != "noreply@anthropic.com" ]]; then
        unverifiable+="$short wrong-committer $email"$'\n'
      fi
    done
    if [[ -n "$unverifiable" ]]; then
      echo "There are commit(s) on branch '$current_branch' that GitHub will show as Unverified (missing signature, or committer email is not noreply@anthropic.com):" >&2
      printf '%s' "$unverifiable" >&2
      echo "Please run 'git config user.email noreply@anthropic.com && git config user.name Claude', then 'git commit --amend --no-edit --reset-author' for the tip commit, or 'git rebase --exec \"git commit --amend --no-edit --reset-author\" <base>' for earlier commits, then push." >&2
      exit 2
    fi
  fi

  unpushed=${#local_commits[@]}
  if [[ "$unpushed" -gt 0 ]]; then
    if git rev-parse --verify --quiet "refs/remotes/origin/$current_branch" >/dev/null; then
      echo "There are $unpushed unpushed commit(s) on branch '$current_branch'. Please push these changes to the remote repository." >&2
    else
      echo "Branch '$current_branch' has $unpushed unpushed commit(s) and no remote branch. Please push these changes to the remote repository." >&2
    fi
    exit 2
  fi
fi

exit 0
