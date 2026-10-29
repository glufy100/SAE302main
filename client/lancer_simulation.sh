#!/usr/bin/env bash

DOSSIER="$(cd "$(dirname "$0")" && pwd)"
DENSITE_VOITURES="${1:-3}"
DENSITE_URGENCES="${2:-0.4}"

if ! [[ "$DENSITE_VOITURES" =~ ^[0-9]+$ ]] || (( DENSITE_VOITURES < 1 )); then
    echo "La densite des voitures doit etre un entier positif." >&2
    exit 2
fi
if ! [[ "$DENSITE_URGENCES" =~ ^([0-9]+([.,][0-9]*)?|[.,][0-9]+)$ ]]; then
    echo "Usage : $0 [densite_voitures] [densite_ambulances entre 0 et 1]" >&2
    exit 2
fi
DENSITE_URGENCES="${DENSITE_URGENCES//,/.}"
if ! awk -v densite="$DENSITE_URGENCES" 'BEGIN { exit !(densite >= 0 && densite <= 1) }'; then
    echo "La densite des ambulances doit etre comprise entre 0 et 1." >&2
    exit 2
fi

CARREFOURS="${3:-TOUS}"
case "$CARREFOURS" in
    TOUS) CARREFOURS=(CROIX T) ;;
    CROIX|T) CARREFOURS=("$CARREFOURS") ;;
    *) echo "Le carrefour doit etre TOUS, CROIX ou T." >&2; exit 2 ;;
esac

cd "$DOSSIER"
CLIENTS_PIDS=()
arreter() {
    if (( ${#CLIENTS_PIDS[@]} > 0 )); then
        kill "${CLIENTS_PIDS[@]}" 2>/dev/null
    fi
}
trap arreter EXIT INT TERM

for CARREFOUR in "${CARREFOURS[@]}"; do
    python3 voiture.py "$DENSITE_VOITURES" --carrefour "$CARREFOUR" &
    CLIENTS_PIDS+=("$!")
done

echo "[INFO] Simulation en cours. Ctrl+C pour quitter."
sleep 8
for CARREFOUR in "${CARREFOURS[@]}"; do
    python3 urgence.py --generer "$DENSITE_URGENCES" --carrefour "$CARREFOUR" &
    CLIENTS_PIDS+=("$!")
done
wait "${CLIENTS_PIDS[@]}"
