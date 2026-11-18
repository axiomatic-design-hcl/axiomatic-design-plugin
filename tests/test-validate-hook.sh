#!/usr/bin/env bash
# Tests for plugins/adhcl/hooks/validate-adhcl.sh.
# A fake adhcl records its arguments, so the tests need no Go build.
# Run from the repository root: bash tests/test-validate-hook.sh

set -u

root="$(cd "$(dirname "$0")/.." && pwd)"
hook="$root/plugins/adhcl/hooks/validate-adhcl.sh"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

failures=0

# The fake adhcl writes its arguments to $work/args.
# It exits with the code in $work/code (default 0).
mkdir -p "$work/bin"
cat >"$work/bin/adhcl" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$FAKE_DIR/args"
echo "fake report for $*"
exit "$(cat "$FAKE_DIR/code" 2>/dev/null || echo 0)"
FAKE
chmod +x "$work/bin/adhcl"

# A project with a manifest model and a separate directory model.
proj="$work/proj"
mkdir -p "$proj/model" "$proj/plain"
printf 'core_files = ["design.ad.hcl"]\nattachment_files = ["bindings.ad.ext.hcl"]\n' >"$proj/model/model.ad.project.hcl"
touch "$proj/model/design.ad.hcl" "$proj/model/bindings.ad.ext.hcl" "$proj/model/other.ad.ext.hcl"
touch "$proj/plain/a.ad.hcl" "$proj/README.md"

# run FILE CODE [ENV...]: run the hook for FILE with fake exit CODE.
run() {
  local file="$1" code="$2"
  shift 2
  rm -f "$work/args"
  printf '%s' "$code" >"$work/code"
  printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$file" \
    | env PATH="$work/bin:$PATH" FAKE_DIR="$work" CLAUDE_PROJECT_DIR="$proj" "$@" \
      bash "$hook" >"$work/stdout" 2>"$work/stderr"
  status=$?
  args="$(cat "$work/args" 2>/dev/null || true)"
}

expect() {
  local name="$1" want_status="$2" want_args="$3"
  if [ "$status" != "$want_status" ] || [ "$args" != "$want_args" ]; then
    echo "FAIL $name: status=$status (want $want_status) args='$args' (want '$want_args')"
    sed 's/^/  stderr: /' "$work/stderr"
    failures=$((failures + 1))
  else
    echo "ok   $name"
  fi
}

run "$proj/README.md" 0
expect "ignores other files" 0 ""

run "$proj/plain/a.ad.hcl" 0
expect "core file without manifest selects its directory" 0 "validate -- $proj/plain"

run "$proj/model/design.ad.hcl" 0
expect "core file listed in a manifest selects the manifest" 0 "validate -- $proj/model/model.ad.project.hcl"

run "$proj/model/bindings.ad.ext.hcl" 0
expect "listed attachment selects the manifest" 0 "validate -- $proj/model/model.ad.project.hcl"

run "$proj/model/other.ad.ext.hcl" 0
expect "unlisted attachment is skipped" 0 ""

run "$proj/model/model.ad.project.hcl" 0
expect "manifest selects itself" 0 "validate -- $proj/model/model.ad.project.hcl"

run "$proj/plain/a.ad.hcl" 1
expect "error findings give exit 2" 2 "validate -- $proj/plain"
grep -q "fake report" "$work/stderr" || { echo "FAIL report missing from stderr"; failures=$((failures + 1)); }

run "$proj/plain/a.ad.hcl" 2
expect "usage error gives exit 1" 1 "validate -- $proj/plain"

run "$proj/plain/a.ad.hcl" 0 ADHCL_PROFILE=architecture
expect "profile from the environment" 0 "validate --profile architecture -- $proj/plain"

# A jq that fails makes the hook use its plain pattern.
mkdir -p "$work/nojq"
printf '#!/bin/sh\nexit 1\n' >"$work/nojq/jq"
chmod +x "$work/nojq/jq"
run "$proj/model/design.ad.hcl" 0 PATH="$work/nojq:$work/bin:$PATH"
expect "file path without jq" 0 "validate -- $proj/model/model.ad.project.hcl"

run "$proj/plain/a.ad.hcl" 0 ADHCL_HOOK_DISABLE=1
expect "hook can be turned off" 0 ""

run "$proj/plain/a.ad.hcl" 0 ADHCL_BIN=adhcl-missing
expect "missing binary is not an error" 0 ""

if [ "$failures" -ne 0 ]; then
  echo "$failures test(s) failed"
  exit 1
fi
echo "all tests passed"
