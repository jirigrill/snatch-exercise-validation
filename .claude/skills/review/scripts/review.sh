#!/bin/bash
# Prepare a /review round and post the /review comment. Reads the diff, runs nothing else.
# usage:
#   review.sh prep full|diff [<git diff args>] [--item <file>] [--prior <findings.md>]
#     full: main...HEAD plus uncommitted changes (default); diff: uncommitted changes vs HEAD (default);
#     explicit <git diff args> (e.g. `77cddcb^ 77cddcb -- prototype/src/snatch/video.py`) replace the default.
#     .scratch/ and docs/results/ are excluded. Writes .scratch/review/<branch>/<HEAD sha 7>/round<k>/prompt.md and prints its
#     path; the 4th round on the same HEAD prints STOP and exits 3. Env REVIEW_STUB=<file>: also copies it to
#     round<k>/findings.md and prints a `stub:` line (the reviewer is not spawned; the skill's only test hook).
#   review.sh comment <sha> <findings.md> <prompt.md>
#     takes <sha> as given (no check that it is the reviewed code); reads the round meta beside <prompt.md>; validates the findings file (count line = the findings, every Important answered with one of
#     fixed (<sha>) / wrong / intentional / didn't matter) and posts the /review comment on the branch's open PR.
#     DRY_RUN=1 prints it and posts nothing.
set -e
fail() { echo "FAIL: $1"; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
# comment's file args may be relative to the caller's cwd: absolutize before cd to the repo root
if [ "$1" = comment ]; then
  for i in 3 4; do
    [ -f "${!i}" ] && set -- "${@:1:$((i-1))}" "$(cd "$(dirname "${!i}")" && pwd)/$(basename "${!i}")" "${@:$((i+1))}"
  done
fi
root=$(git rev-parse --show-toplevel) || fail 'not in a git repo'
cd "$root"
EXCL=(':!.scratch' ':!docs/results')

kind=$here/commit_kind.sh
[ -x "$kind" ] || kind=$(command -v commit_kind.sh || true)

case "$1" in
prep)
  mode=$2
  [[ $mode == full || $mode == diff ]] || fail 'usage: review.sh prep full|diff [<git diff args>] [--item <file>] [--prior <findings.md>]'
  shift 2
  args=() item= prior=
  while [ $# -gt 0 ]; do
    case "$1" in
      --item) item=$2; shift 2 ;;
      --prior) prior=$2; shift 2 ;;
      *) args+=("$1"); shift ;;
    esac
  done
  [ -z "$item" ] || [ -f "$item" ] || fail "no such item file: $item"
  [ -z "$prior" ] || [ -f "$prior" ] || fail "no such prior findings file: $prior"
  [ -n "$kind" ] || fail 'commit_kind.sh not found'
  branch=$(git rev-parse --abbrev-ref HEAD)
  head=$(git rev-parse HEAD)
  state=.scratch/review/${branch//\//-}/${head:0:7}
  mkdir -p "$state"
  n=$(cat "$state/count" 2>/dev/null || echo 0)
  if [ "$n" -ge 3 ]; then
    echo "STOP: 3 find-and-fix rounds on ${head:0:7} and still not clean; ask the user whether the approach is right"
    exit 3
  fi
  k=$((n + 1))
  rd=$state/round$k
  mkdir -p "$rd"
  # the diff: a temp index holds the worktree (tracked + new files), so the real index is untouched
  tmpidx=$(mktemp)
  cp "$(git rev-parse --git-path index)" "$tmpidx"
  GIT_INDEX_FILE=$tmpidx git add -A -- . "${EXCL[@]}"
  if [ ${#args[@]} -eq 0 ]; then
    if [ $mode = full ]; then base=$(git merge-base origin/main HEAD); else base=HEAD; fi
    GIT_INDEX_FILE=$tmpidx git diff --cached "$base" -- . "${EXCL[@]}" >"$rd/diff.patch"
    dargs=("$base")
  else
    dargs=("${args[@]}")
    if printf '%s\n' "${args[@]}" | grep -qx -e '--'; then
      git diff "${args[@]}" "${EXCL[@]}" >"$rd/diff.patch"
    else
      git diff "${args[@]}" -- . "${EXCL[@]}" >"$rd/diff.patch"
    fi
  fi
  # base = where the diff starts
  cs=()
  for a in "${args[@]}"; do
    [ "$a" = -- ] && break
    case "$a" in
      *...*) cs+=("${a%%...*}" "${a##*...}") ;;
      *..*) cs+=("${a%%..*}" "${a##*..}") ;;
      -*) ;;
      *) git rev-parse --verify -q "$a^{commit}" >/dev/null && cs+=("$a") ;;
    esac
  done
  if [ ${#args[@]} -eq 0 ]; then
    base=$(git rev-parse "$base")
  else
    [ ${#cs[@]} -ge 1 ] || fail "no commit among the git diff args: ${args[*]}"
    base=$(git rev-parse --verify "${cs[0]}^{commit}")
  fi
  rm -f "$tmpidx"
  if [ -z "$item" ]; then
    item=$rd/item.md
    grep -m1 -e '- \[ \]' .scratch/plan/README.md >"$item" || echo '(no unchecked item in .scratch/plan/README.md)' >"$item"
  fi
  # deep comes from the file names in the very diff the reviewer gets (both sides of each `diff --git a/X b/Y`)
  deep=$(while IFS= read -r l; do
      l=${l#diff --git a/}
      printf '%s\n%s\n' "${l%% b/*}" "${l#* b/}"
    done < <(grep '^diff --git a/' "$rd/diff.patch" || true) | "$kind" deep-files)
  [[ $deep == yes || $deep == no ]] || fail "commit_kind.sh deep printed '$deep', expected yes or no"
  bp=(--repo "$root" --diff "$rd/diff.patch" --item "$item" --deep "$deep" --out "$rd/prompt.md")
  [ -z "$prior" ] || bp+=(--prior "$prior")
  python3 -I "$here/build_prompt.py" "${bp[@]}"
  echo "$k" >"$state/count"
  { echo "mode=$mode"; echo "base=$base"; echo "round=$k"; echo "head=$head"; echo "deep=$deep"; echo "args=${dargs[*]}"; } >"$rd/meta"
  echo "$rd/prompt.md"
  if [ -n "$REVIEW_STUB" ]; then
    [ -f "$REVIEW_STUB" ] || fail "REVIEW_STUB is not a file: $REVIEW_STUB"
    cp "$REVIEW_STUB" "$rd/findings.md"
    echo "stub: reviewer output from $REVIEW_STUB, do not spawn the reviewer"
  fi
  ;;
comment)
  sha=$2 findings=$3 prompt=$4
  [[ $sha =~ ^[0-9a-f]{7,40}$ ]] && [ -f "$findings" ] && [ -f "$prompt" ] || fail 'usage: review.sh comment <sha 7+ hex> <findings.md> <prompt.md>'
  body=$(mktemp)
  trap 'rm -f "$body"' EXIT
  pd=$(cd "$(dirname "$prompt")" && pwd)
  [ -f "$pd/meta" ] || fail "no round meta in $pd (expected meta from \`review.sh prep\`)"
  python3 -I - "$sha" "$findings" "$prompt" "$body" "$pd" <<'PY' || exit 1
from __future__ import annotations
import re, sys
sha, findings, prompt, out, pdir = sys.argv[1:6]
LIMIT = 65000
SENTINEL = re.compile(r"^<details><summary>Reviewer prompt</summary>", re.M)  # only this exact line starts the prompt part
text = open(findings).read()
meta = {}
try:
    for line in open(pdir + "/meta"):
        k, _, v = line.rstrip("\n").partition("=")
        meta[k] = v
except OSError:
    pass

def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)

if meta.get("mode") not in ("full", "diff") or not meta.get("round") or not meta.get("base"):
    fail("no readable round meta next to the prompt file (expected <round dir>/meta from `review.sh prep`)")

count_re = re.compile(r"^(\d+) Important, (\d+) Nit, (\d+) Pre-existing(\. Nothing to fix\.)?\s*$", re.M)
m = count_re.search(text)
if not m:
    fail("count line missing (`<a> Important, <b> Nit, <c> Pre-existing`)")
a, b, c = (int(m.group(i)) for i in (1, 2, 3))
first = re.search(r"^### F\d+ ·", text, re.M)
if first and m.start() > first.start():
    fail("count line must come before the first finding")
head_re = re.compile(r"^### (F\d+) · (Important|Nit|Pre-existing) · (.+?) · `([^`]+)`\s*$", re.M)
heads = list(head_re.finditer(text))
if len(heads) != len(re.findall(r"^### F\d+\b", text, re.M)):
    fail("a finding heading does not match `### F<n> · <Important|Nit|Pre-existing> · <class> · `file:line``")
tags = [h.group(2) for h in heads]
got = (tags.count("Important"), tags.count("Nit"), tags.count("Pre-existing"))
if got != (a, b, c):
    fail(f"count line says {a} Important, {b} Nit, {c} Pre-existing but the findings are {got[0]}, {got[1]}, {got[2]}")
if len({h.group(1) for h in heads}) != len(heads):
    fail("duplicate finding ids")
cat_re = re.compile(r"^\*\*Answer:\*\* (fixed \([0-9a-f]{7,40}\)|wrong|intentional|didn't matter): \S", re.M)
cats = {"fixed": 0, "wrong": 0, "intentional": 0, "didn't matter": 0}
for i, h in enumerate(heads):
    seg = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
    seg = SENTINEL.split(seg)[0]
    ans = re.findall(r"^\*\*Answer:\*\*.*$", seg, re.M)
    if not ans:
        if h.group(2) == "Important":
            fail(f"{h.group(1)} (Important) has no **Answer:**")
        continue
    am = cat_re.match(ans[0])
    if not am:
        fail(f"{h.group(1)}: answer must be `**Answer:** fixed (<sha>): <reason>` or wrong / intentional / didn't matter, then `: <reason>`")
    cats[am.group(1).split(" (")[0]] += 1

first_h = re.search(r"^### ", text, re.M)
hs = None
for hm in re.finditer(r"^> \*\*Human should read:\*\*.*$", text, re.M):
    if not first_h or hm.start() < first_h.start():  # only before the first finding
        hs = hm
        break
deep = meta.get("deep") == "yes"
if deep and not hs:
    fail("deep review (verify scripts, hooks or the S8 judge touched) but the findings have no `> **Human should read:**` line")
rnd = meta["round"]
rng = f"{meta['base'][:7]}..{sha[:7]} ({meta['mode']})"
body_start = text[first.start():] if first else ""
body_start = SENTINEL.split(body_start)[0].rstrip()
n = a + b + c
lines = [f"## /review: {sha} — {n} findings",
         f"{a} Important, {b} Nit, {c} Pre-existing" + (". Nothing to fix." if a == 0 else "")]
if hs:
    lines.append(hs.group(0))
lines.append(f"Review: {rng}, round {rnd} of 3")
dm = cats["didn't matter"]
lines.append(f"Answers: {cats['fixed']} fixed, {cats['wrong']} wrong, {cats['intentional']} intentional, {dm} didn't matter")
head = "\n".join(lines) + ("\n\n" + body_start if body_start else "") + "\n"
p = open(prompt).read()
longest = max([len(r) for r in re.findall(r"`+", p)] + [2])
fence = "`" * (longest + 1)
pre = "\n<details><summary>Reviewer prompt</summary>\n\n"
post = "\n</details>\n"
budget = LIMIT - len(head) - len(pre) - len(post) - 2 * (len(fence) + 2) - 200
note = ""
if len(p) > budget:
    p = p[: max(budget, 0)]
    note = f"[prompt truncated to {len(p)} characters to fit GitHub's comment limit]\n"
open(out, "w").write(head + pre + note + fence + "\n" + p.rstrip("\n") + "\n" + fence + "\n" + post)
PY
  if [ -n "$DRY_RUN" ]; then
    cat "$body"
  else
    gh pr view --json number >/dev/null 2>&1 || fail "no open PR for branch $(git rev-parse --abbrev-ref HEAD)"
    gh pr comment --body-file "$body"
  fi
  rm -f "$body"
  ;;
*)
  fail 'usage: review.sh prep full|diff [<git diff args>] | review.sh comment <sha> <findings.md> <prompt.md>'
  ;;
esac
