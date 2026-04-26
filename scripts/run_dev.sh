#!/usr/bin/env bash
# Run the integrated Apollo dev stack: real backend (uvicorn) + frontend (vite).
# Vite proxies /api -> http://localhost:8000 (see frontend/vite.config.ts).

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# ANSI colors (skipped if stdout isn't a tty).
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
  C_CYAN=$'\033[38;5;51m'; C_BLUE=$'\033[38;5;39m'
  C_MAGENTA=$'\033[38;5;201m'; C_YELLOW=$'\033[38;5;220m'
  C_GREEN=$'\033[38;5;46m'; C_ORANGE=$'\033[38;5;208m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""
  C_CYAN=""; C_BLUE=""; C_MAGENTA=""; C_YELLOW=""; C_GREEN=""; C_ORANGE=""
fi

cat <<EOF
${C_YELLOW}                    .                      .${C_RESET}
${C_YELLOW}         .            *        .       .         .       *${C_RESET}
${C_YELLOW}    *          .            .                .${C_RESET}
${C_ORANGE}                          ___${C_RESET}
${C_ORANGE}                       .-'   '-.${C_RESET}        ${C_DIM}.    *${C_RESET}
${C_ORANGE}                      /  ${C_YELLOW}.-~-.${C_ORANGE}  \\${C_RESET}    ${C_DIM}.${C_RESET}
${C_ORANGE}              .      |  ${C_YELLOW}/     \\${C_ORANGE}  |${C_RESET}     ${C_DIM}*${C_RESET}
${C_ORANGE}                     |  ${C_YELLOW}\\     /${C_ORANGE}  |${C_RESET}
${C_ORANGE}                      \\  ${C_YELLOW}'-~-'${C_ORANGE}  /${C_RESET}     ${C_DIM}.${C_RESET}
${C_ORANGE}                       '-.___.-'${C_RESET}
${C_DIM}        .          *               .           .${C_RESET}
${C_BOLD}${C_CYAN}     ___    ____   ___   _      _      ___${C_RESET}
${C_BOLD}${C_CYAN}    / _ \\  |  _ \\ / _ \\ | |    | |    / _ \\${C_RESET}
${C_BOLD}${C_BLUE}   | |_| | | |_) | | | || |    | |   | | | |${C_RESET}
${C_BOLD}${C_BLUE}   |  _  | |  __/| |_| || |___ | |___| |_| |${C_RESET}
${C_BOLD}${C_MAGENTA}   |_| |_| |_|    \\___/ |_____||_____|\\___/${C_RESET}
${C_DIM}        ~ integrated dev stack — backend + frontend ~${C_RESET}

${C_GREEN}  >>  backend  ${C_DIM}::${C_RESET} ${C_BOLD}http://localhost:${BACKEND_PORT}${C_RESET}  ${C_DIM}(uvicorn)${C_RESET}
${C_GREEN}  >>  frontend ${C_DIM}::${C_RESET} ${C_BOLD}http://localhost:${FRONTEND_PORT}${C_RESET}  ${C_DIM}(vite)${C_RESET}
${C_DIM}  >>  /api proxied frontend → backend${C_RESET}
${C_DIM}  >>  Ctrl-C to stop both${C_RESET}

EOF

backend_pid=""
frontend_pid=""

cleanup() {
  echo
  echo "[run_dev] shutting down..."
  # Kill whole process groups so uvicorn's reloader children + npm's vite child go too.
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill -TERM -"$frontend_pid" 2>/dev/null || kill -TERM "$frontend_pid" 2>/dev/null || true
  fi
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill -TERM -"$backend_pid" 2>/dev/null || kill -TERM "$backend_pid" 2>/dev/null || true
  fi
  # Give them a moment, then SIGKILL anything still alive.
  sleep 1
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill -KILL -"$frontend_pid" 2>/dev/null || kill -KILL "$frontend_pid" 2>/dev/null || true
  fi
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill -KILL -"$backend_pid" 2>/dev/null || kill -KILL "$backend_pid" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Stream child output through sed so each line is tagged. Using process substitution
# (>(...)) keeps $! pointing at the real child rather than a pipeline tail.
echo "[run_dev] starting backend on :$BACKEND_PORT (uvicorn apollo.api.app:app)"
PYTHONPATH=src uvicorn apollo.api.app:app --reload --port "$BACKEND_PORT" \
  > >(sed -u 's/^/[backend] /') 2> >(sed -u 's/^/[backend] /' >&2) &
backend_pid=$!

echo "[run_dev] starting frontend on :$FRONTEND_PORT (vite)"
( cd frontend && exec npm run dev -- --port "$FRONTEND_PORT" ) \
  > >(sed -u 's/^/[frontend] /') 2> >(sed -u 's/^/[frontend] /' >&2) &
frontend_pid=$!

echo "${C_DIM}[run_dev] backend pid=$backend_pid  frontend pid=$frontend_pid${C_RESET}"
echo

# bash 3.2 (macOS default) doesn't support `wait -n`, so poll instead.
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "$backend_pid" 2>/dev/null; then
  echo "[run_dev] backend exited first, tearing down frontend..."
else
  echo "[run_dev] frontend exited first, tearing down backend..."
fi
exit 1
