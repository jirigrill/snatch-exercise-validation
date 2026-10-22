#!/bin/bash
# Scripted cases for require-evidence.sh (.scratch/plan/review-skill.md, "Stop hook"): a temp git
# repo with a bare origin, a stub `gh` on PATH serving canned PR comments, the real hook and
# commit_kind.sh copied in. Exit 0 = all pass. Not pytest: outside the CLAUDE.md R1-R5 rule.
src=$(cd "$(dirname "$0")/../.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'STUB'
#!/bin/bash
# stub: gh pr view [<pr>] --json <f> -q <jq filter>; state from $GH_COMMENTS (file) / $GH_NOPR
f=""; prev=""; for a in "$@"; do [[ $prev == -q ]] && f=$a; prev=$a; done
[[ -n ${GH_NOPR:-} ]] && exit 1
if [[ " $* " == *" comments "* ]]; then jq -r "$f" "$GH_COMMENTS"
else echo '{"number":7,"state":"OPEN"}' | jq -r "$f"; fi
STUB
chmod +x "$T/bin/gh"
export PATH="$T/bin:$PATH"
fails=0 n=0
CHK='checks: pytest 12 passed, 0 failed · pyright 0 errors'

setup() { # fresh repo: main + feat branch with one prototype commit, pushed
  R=$T/repo; rm -rf "$R" "$T/origin.git"
  git init -q --bare "$T/origin.git"
  git init -q -b main "$R"; cd "$R" || exit 1
  git config user.email t@t; git config user.name t
  mkdir -p prototype/src/snatch docs .claude/hooks .claude/skills/review/scripts
  echo a > prototype/src/snatch/a.py; echo d > docs/d.md
  cp "$src/.claude/hooks/require-evidence.sh" .claude/hooks/
  cp "$src/.claude/skills/review/scripts/commit_kind.sh" .claude/skills/review/scripts/
  git add -A; git commit -q -m base
  git remote add origin "$T/origin.git"; git push -q origin main
  git checkout -q -b feat; echo b > prototype/x.py; git add -A; git commit -q -m c1
  git push -q -u origin feat 2>/dev/null
  echo '[]' > "$T/comments.json"; unset GH_NOPR
}
commit() { # commit <msg> <file>...
  local m=$1; shift
  for f in "$@"; do mkdir -p "$(dirname "$f")"; echo "$RANDOM" >> "$f"; done
  git add -A; git commit -q -m "$m"; git push -q origin feat 2>/dev/null
}
verify_c() { # verify_c <sha> [checks line]
  printf '## /verify evidence: `root` ✅ OK\ncommit %s T1\n%s\n' "$1" "${2-$CHK}"
}
review_c() { # review_c <sha> <body after header>
  printf '## /review: %s — 2 findings\n%s\n' "$1" "$2"
}
ANS=$'### F1 · Important · c · `a.py:1`\ntext\n**Answer:** fixed (abc1234): done\n\n### F2 · Nit · c · `a.py:2`\ntext'
DET=$'<details><summary>Reviewer prompt</summary>\n### F1 · Important · example\n</details>'
post() { # post <body>...: canned comments file
  printf '%s\0' "$@" | jq -Rs '[split("\u0000")[:-1][] | {body: .}] | {comments: .}' > "$T/comments.json"
}
run() { # run <stdin json> -> sets code, err
  err=$(echo "${1:-{\}}" | CLAUDE_PROJECT_DIR=$R GH_COMMENTS=$T/comments.json bash "$R/.claude/hooks/require-evidence.sh" 2>&1 >/dev/null); code=$?
}
expect() { # expect <name> <block|allow>
  n=$((n + 1))
  if [[ $2 == allow && $code -eq 0 ]] || [[ $2 == block && $code -eq 2 ]]; then echo "PASS $1"
  else echo "FAIL $1: expected $2, got exit $code: $err"; fails=$((fails + 1)); fi
}
H() { git rev-parse HEAD; }

setup; post "$(verify_c "$(H)")"; run; expect "1 no /review comment" block
setup; post "$(verify_c "$(H)")" "$(review_c "$(H)" "$ANS"$'\n'"$DET")"; run; expect "2 review for HEAD, Important answered (details example ignored)" allow
setup; post "$(verify_c "$(H)")" "$(review_c "$(H)" $'### F1 · Important · c · `a.py:1`\ntext\n\n### F2 · Nit · c · `a.py:2`\ntext')"; run; expect "3 review for HEAD, Important unanswered" block
case3=$err; [[ $case3 == *F1* ]] || { echo "FAIL 3b message names F1: $case3"; fails=$((fails + 1)); }
setup; old=$(H); commit big prototype/a1.py prototype/a2.py prototype/a3.py prototype/a4.py
post "$(verify_c "$(H)")" "$(review_c "$old" "$ANS")"; run; expect "4 review for older sha + later non-trivial commit" block
setup; old=$(H); commit docs-only docs/e.md; commit tiny prototype/x.py
post "$(verify_c "$(H)")" "$(review_c "$old" "$ANS")"; run; expect "5 review for older sha + only docs/trivial after" allow
setup; post "$(review_c "$(H)" "$ANS")" "$(verify_c "$(H)" '')"; run; expect "6a /verify lacks checks line" block
setup; post "$(review_c "$(H)" "$ANS")" "$(verify_c "$(H)" 'checks: pytest 12 passed, 1 failed · pyright 0 errors')"; run; expect "6b /verify pytest failed" block
setup; post "$(review_c "$(H)" "$ANS")" "$(verify_c "$(H)" 'checks: pytest 12 passed, 0 failed · pyright 3 errors')"; run; expect "6c /verify pyright errors" block
setup; post "$(verify_c "$(H)")"; run '{"stop_hook_active": true}'; expect "7 stop_hook_active" allow
setup; git checkout -q main; post; run; expect "8a on main" allow
setup; GH_NOPR=1; export GH_NOPR; run; expect "8b no open PR" allow; unset GH_NOPR
setup; git reset -q --hard main; git push -q -f origin feat 2>/dev/null; commit docs-only docs/e.md; post; run; expect "9 docs-only PR, no /review" allow

setup; git reset -q --hard main; git push -q -f origin feat 2>/dev/null; commit h .claude/hooks/h.sh; post; run; expect "10a hooks-only PR, no /review" block
post "$(review_c "$(H)" "$ANS")"; run; expect "10b hooks-only PR, answered /review, no /verify needed" allow
setup; post "$(verify_c "$(H)")" "$(review_c "$(H)" $'### F1 · Important · c · `a.py:1`\nquotes <details> mid-text\n**Answer:** fixed (abc1234): done\n\n### F2 · Important · c · `a.py:2`\ntext'$'\n'"$DET")"; run; expect "12 <details> quoted mid-text, F1 answered after it, F2 unanswered" block
[[ $err == *F2* && $err != *F1* ]] || { echo "FAIL 12b message names F2 and not F1: $err"; fails=$((fails + 1)); }
setup; old=$(H); git checkout -q main; commit m1 prototype/m1.py prototype/m2.py prototype/m3.py prototype/m4.py; git push -q origin main 2>/dev/null
git checkout -q feat; git merge -q --no-edit main; git push -q origin feat 2>/dev/null
post "$(verify_c "$(H)")" "$(review_c "$old" "$ANS")"; run; expect "13 main merged into branch after review" allow
setup; post "$(verify_c "$(H)")" "$(review_c "$(H)" '0 Important, 0 Nit, 0 Pre-existing. Nothing to fix.')"; run; expect "16 0-findings comment for HEAD" allow
setup; rm .claude/skills/review/scripts/commit_kind.sh; post "$(verify_c "$(H)")" "$(review_c "$(H)" "$ANS")"; run; expect "17 commit_kind.sh missing" block
setup; commit big prototype/a1.py prototype/a2.py prototype/a3.py prototype/a4.py; big=$(H)
post "$(verify_c "$(H)")" "$(review_c "$(H)" "$ANS")" "$(review_c "$(git rev-parse HEAD~1)" "$ANS")"; run; expect "18 newest comment for HEAD wins over older" allow
post "$(verify_c "$(H)")" "$(review_c "$(git rev-parse HEAD~1)" "$ANS")"; run; expect "19 only older comment, non-trivial commit after" block
[[ $err == *"$(git rev-parse --short "$big")"* ]] || { echo "FAIL 19b message names the commit: $err"; fails=$((fails + 1)); }

# commit_kind.sh
setup; K="bash $R/.claude/skills/review/scripts/commit_kind.sh"
kind() { n=$((n + 1)); got=$($K "$2"); [[ $got == "$3" ]] && echo "PASS K$n commit_kind $1" || { echo "FAIL K$n commit_kind $1: expected $3, got $got"; fails=$((fails + 1)); }; }
commit d docs/e.md .scratch/p.md; kind docs "$(H)" docs
commit t prototype/x.py; kind trivial "$(H)" trivial
commit f4 prototype/a1.py prototype/a2.py prototype/a3.py prototype/a4.py; kind "4 files" "$(H)" full
commit nf prototype/src/snatch/new.py; kind "new file in prototype/src" "$(H)" full
commit h .claude/hooks/h.sh; kind "deep path 1 file" "$(H)" full
commit df prototype/a1.py prototype/a2.py; kind "2 files" "$(H)" diff
n=$((n + 1)); got=$($K deep main HEAD); [[ $got == yes ]] && echo "PASS K$n commit_kind deep yes" || { echo "FAIL K$n deep yes: $got"; fails=$((fails + 1)); }
n=$((n + 1)); got=$($K deep HEAD~1 HEAD); [[ $got == no ]] && echo "PASS K$n commit_kind deep no" || { echo "FAIL K$n deep no: $got"; fails=$((fails + 1)); }
n=$((n + 1)); got=$(printf 'docs/a.md\n.claude/skills/review/scripts/x.sh\n' | $K deep-files); [[ $got == yes ]] && echo "PASS K$n deep-files yes" || { echo "FAIL K$n deep-files yes: $got"; fails=$((fails + 1)); }
n=$((n + 1)); got=$(printf 'docs/a.md\nprototype/x.py\n' | $K deep-files); [[ $got == no ]] && echo "PASS K$n deep-files no" || { echo "FAIL K$n deep-files no: $got"; fails=$((fails + 1)); }
exit $((fails > 0))
