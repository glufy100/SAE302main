#!/usr/bin/env bash

RACINE="$(cd "$(dirname "$0")" && pwd)"
DENSITE="${1:-3}"

if [[ "$DENSITE" == "--clients-only" ]]; then
    exec bash "$RACINE/client/lancer_simulation.sh" "${2:-3}" "${3:-0.4}" "${4:-TOUS}"
fi

bash "$RACINE/server/lancer_serveur.sh" &
SERVEUR_PID=$!

arreter() {
    kill "$SERVEUR_PID" 2>/dev/null
    kill "${CLIENTS_PID:-}" 2>/dev/null
}
trap arreter EXIT INT TERM

sleep 3
bash "$RACINE/client/lancer_simulation.sh" "$DENSITE" "${2:-0.4}" "${3:-TOUS}" &
CLIENTS_PID=$!
wait "$SERVEUR_PID"
