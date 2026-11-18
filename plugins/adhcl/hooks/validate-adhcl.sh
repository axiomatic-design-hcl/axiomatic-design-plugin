#!/usr/bin/env bash
# Run `adhcl validate` after Claude edits a RequirementsHCL file.
#
# Claude Code sends the PostToolUse event as JSON on stdin.
# The script reads tool_input.file_path from it.
#
# Exit codes, as Claude Code reads them for PostToolUse:
#   0  nothing to report (not an .ad file, no adhcl, or no error findings)
#   1  a problem that the user sees but Claude does not (for example a bad adhcl version)
#   2  error findings; Claude Code shows stderr to Claude
#
# Configuration through environment variables:
#   ADHCL_HOOK_DISABLE=1          turn the hook off
#   ADHCL_PROFILE=source|architecture  select the profile (adhcl default: source)
#   ADHCL_BIN=/path/to/adhcl      use this binary instead of the one on PATH

set -u

if [ "${ADHCL_HOOK_DISABLE:-}" = "1" ]; then
  exit 0
fi

input_json="$(cat)"

# Read tool_input.file_path. Use jq when it works, else a plain pattern.
file=""
if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$input_json" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
fi
if [ -z "$file" ]; then
  file="$(printf '%s' "$input_json" \
    | tr -d '\n' \
    | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
fi

case "$file" in
  *.ad.project.hcl | *.ad.ext.hcl | *.ad.hcl) ;;
  *) exit 0 ;;
esac

adhcl="${ADHCL_BIN:-adhcl}"
if ! command -v "$adhcl" >/dev/null 2>&1; then
  # The plugin must not fail for people who do not have the tool.
  exit 0
fi

case "$file" in
  /*) ;;
  *) file="${CLAUDE_PROJECT_DIR:-$PWD}/$file" ;;
esac

if [ ! -f "$file" ]; then
  exit 0
fi

# Select the inputs to validate.
# 1. An edited manifest selects itself.
# 2. Otherwise, use each manifest that lists the edited file. Search the
#    directory of the file and its parents, up to the project directory.
# 3. Otherwise, a core file selects its directory, because adhcl merges the
#    immediate *.ad.hcl files of a directory into one model.
# 4. An attachment file without a manifest cannot be validated alone.
inputs=()
case "$file" in
  *.ad.project.hcl)
    inputs+=("$file")
    ;;
  *)
    stop="${CLAUDE_PROJECT_DIR:-/}"
    dir="$(dirname "$file")"
    while :; do
      for manifest in "$dir"/*.ad.project.hcl; do
        [ -f "$manifest" ] || continue
        rel="${file#"$dir"/}"
        if grep -Fq "\"$rel\"" "$manifest"; then
          inputs+=("$manifest")
        fi
      done
      if [ "${#inputs[@]}" -gt 0 ] || [ "$dir" = "$stop" ] || [ "$dir" = "/" ]; then
        break
      fi
      dir="$(dirname "$dir")"
    done
    if [ "${#inputs[@]}" -eq 0 ]; then
      case "$file" in
        *.ad.ext.hcl) exit 0 ;;
        *) inputs+=("$(dirname "$file")") ;;
      esac
    fi
    ;;
esac

profile_args=()
case "${ADHCL_PROFILE:-}" in
  source | architecture) profile_args=(--profile "$ADHCL_PROFILE") ;;
  "") ;;
  *)
    echo "adhcl hook: ignoring ADHCL_PROFILE='${ADHCL_PROFILE}'. Use source or architecture." >&2
    ;;
esac

status=0
report=""
for target in "${inputs[@]}"; do
  out="$("$adhcl" validate ${profile_args[@]+"${profile_args[@]}"} -- "$target" 2>&1)"
  code=$?
  case "$code" in
    0) ;;
    1)
      status=2
      report="${report}adhcl validate found errors in ${target} after the edit of ${file}:
$(printf '%s\n' "$out" | head -n 200)

"
      ;;
    *)
      [ "$status" -eq 2 ] || status=1
      report="${report}adhcl validate stopped with exit code ${code} for ${target}. The installed adhcl may not support this command line:
$(printf '%s\n' "$out" | head -n 40)

"
      ;;
  esac
done

if [ "$status" -ne 0 ]; then
  printf '%s' "$report" >&2
fi
exit "$status"
