#!/usr/bin/env bash
# netscan.sh — Recense les hôtes actifs d'un sous-réseau ou d'une plage IP
# Usage:
#   ./netscan.sh 192.168.1.0/24
#   ./netscan.sh 10.0.0.1-10.0.0.50
#   ./netscan.sh 10.110.0.1 10.110.0.254

set -euo pipefail

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Dépendances ───────────────────────────────────────────────────────────────
need() { command -v "$1" &>/dev/null || { echo -e "${RED}Erreur: '$1' introuvable. Installe-le et réessaie.${RESET}"; exit 1; }; }
need ping
need host   # ou dig/nslookup en fallback

# ── Aide ──────────────────────────────────────────────────────────────────────
usage() {
    echo -e "${BOLD}Usage:${RESET}"
    echo "  $0 <CIDR>               ex: $0 192.168.1.0/24"
    echo "  $0 <IP-début> <IP-fin>  ex: $0 10.0.0.1 10.0.0.50"
    echo "  $0 <IP-début>-<IP-fin>  ex: $0 10.0.0.1-10.0.0.50"
    echo ""
    echo -e "${BOLD}Options:${RESET}"
    echo "  -t <ms>   Timeout ping en ms (défaut: 300)"
    echo "  -j <n>    Jobs parallèles (défaut: 50)"
    echo "  -o <fic>  Fichier de sortie CSV (optionnel)"
    echo "  -q        Mode silencieux (résultats seulement)"
    exit 0
}

# ── Defaults ──────────────────────────────────────────────────────────────────
TIMEOUT_MS=300
JOBS=50
OUTPUT_FILE=""
QUIET=0

# ── Parse options ─────────────────────────────────────────────────────────────
while getopts "t:j:o:qh" opt; do
    case $opt in
        t) TIMEOUT_MS="$OPTARG" ;;
        j) JOBS="$OPTARG" ;;
        o) OUTPUT_FILE="$OPTARG" ;;
        q) QUIET=1 ;;
        h|*) usage ;;
    esac
done
shift $((OPTIND - 1))

[[ $# -eq 0 ]] && usage

# ── ip_to_int / int_to_ip ─────────────────────────────────────────────────────
ip_to_int() {
    local ip="$1"
    local a b c d
    IFS='.' read -r a b c d <<< "$ip"
    echo $(( (a << 24) | (b << 16) | (c << 8) | d ))
}

int_to_ip() {
    local n="$1"
    echo "$(( (n >> 24) & 255 )).$(( (n >> 16) & 255 )).$(( (n >> 8) & 255 )).$(( n & 255 ))"
}

# ── Calcul plage depuis CIDR ───────────────────────────────────────────────────
cidr_to_range() {
    local cidr="$1"
    local ip="${cidr%/*}"
    local prefix="${cidr#*/}"
    local mask=$(( 0xFFFFFFFF << (32 - prefix) & 0xFFFFFFFF ))
    local network=$(( $(ip_to_int "$ip") & mask ))
    local broadcast=$(( network | (~mask & 0xFFFFFFFF) ))
    # Exclure adresse réseau et broadcast
    START_INT=$(( network + 1 ))
    END_INT=$(( broadcast - 1 ))
}

# ── Déterminer la plage ────────────────────────────────────────────────────────
if [[ "$1" == *"/"* ]]; then
    cidr_to_range "$1"
elif [[ "$1" == *"-"* ]]; then
    IFS='-' read -r ip_start ip_end <<< "$1"
    START_INT=$(ip_to_int "$ip_start")
    END_INT=$(ip_to_int "$ip_end")
elif [[ $# -eq 2 ]]; then
    START_INT=$(ip_to_int "$1")
    END_INT=$(ip_to_int "$2")
else
    echo -e "${RED}Argument invalide: '$1'${RESET}"
    usage
fi

START_IP=$(int_to_ip "$START_INT")
END_IP=$(int_to_ip "$END_INT")
TOTAL=$(( END_INT - START_INT + 1 ))

# ── Résolution hostname ────────────────────────────────────────────────────────
resolve_hostname() {
    local ip="$1"
    local hostname=""

    # Tentative 1 : host (PTR record)
    if command -v host &>/dev/null; then
        hostname=$(host "$ip" 2>/dev/null | awk '/domain name pointer/ {sub(/\.$/, "", $NF); print $NF}' | head -1)
    fi

    # Tentative 2 : dig si host a échoué
    if [[ -z "$hostname" ]] && command -v dig &>/dev/null; then
        hostname=$(dig +short +time=1 +tries=1 -x "$ip" 2>/dev/null | sed 's/\.$//' | head -1)
    fi

    # Tentative 3 : nslookup
    if [[ -z "$hostname" ]] && command -v nslookup &>/dev/null; then
        hostname=$(nslookup "$ip" 2>/dev/null | awk '/name =/ {sub(/\.$/, "", $NF); print $NF}' | head -1)
    fi

    # Tentative 4 : nmblookup (NetBIOS/Windows)
    if [[ -z "$hostname" ]] && command -v nmblookup &>/dev/null; then
        hostname=$(nmblookup -A "$ip" 2>/dev/null | awk '/<00>/ && !/<GROUP>/ {print $1}' | head -1)
    fi

    echo "${hostname:-N/A}"
}
export -f resolve_hostname ip_to_int int_to_ip

# ── Scan d'une IP (appelé en parallèle) ──────────────────────────────────────
scan_ip() {
    local ip="$1"
    local timeout_ms="$2"

    # ping : -W timeout en secondes (Linux) — on convertit ms→s (min 1)
    local timeout_s=$(( timeout_ms / 1000 ))
    [[ $timeout_s -lt 1 ]] && timeout_s=1

    if ping -c 1 -W "$timeout_s" "$ip" &>/dev/null 2>&1; then
        local hostname
        hostname=$(resolve_hostname "$ip")
        printf "UP\t%s\t%s\n" "$ip" "$hostname"
    fi
}
export -f scan_ip resolve_hostname

# ── En-tête ───────────────────────────────────────────────────────────────────
if [[ $QUIET -eq 0 ]]; then
    echo -e "${BOLD}${CYAN}"
    echo "╔════════════════════════════════════════════════════╗"
    echo "║              netscan.sh — Scan réseau              ║"
    echo "╚════════════════════════════════════════════════════╝${RESET}"
    echo -e "  Plage   : ${BOLD}${START_IP}${RESET} → ${BOLD}${END_IP}${RESET}"
    echo -e "  Hôtes   : ${BOLD}${TOTAL}${RESET} adresses à sonder"
    echo -e "  Timeout : ${BOLD}${TIMEOUT_MS} ms${RESET}  |  Parallèles : ${BOLD}${JOBS}${RESET}"
    echo ""
fi

# ── CSV header ────────────────────────────────────────────────────────────────
if [[ -n "$OUTPUT_FILE" ]]; then
    echo "IP,Hostname,Timestamp" > "$OUTPUT_FILE"
fi

# ── Scan parallèle ────────────────────────────────────────────────────────────
RESULTS=()
ACTIVE=0
SCANNED=0

# Génère toutes les IPs et scanne en parallèle via xargs
mapfile -t RESULTS < <(
    seq "$START_INT" "$END_INT" | while read -r n; do
        int_to_ip "$n"
    done | xargs -P "$JOBS" -I{} bash -c 'scan_ip "$@"' _ {} "$TIMEOUT_MS"
)

# ── Affichage des résultats ───────────────────────────────────────────────────
if [[ $QUIET -eq 0 ]]; then
    printf "\n${BOLD}%-18s %-40s${RESET}\n" "IP" "Hostname"
    printf '%.0s─' {1..60}; echo ""
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Trier les résultats par IP
mapfile -t SORTED < <(
    for line in "${RESULTS[@]}"; do
        ip=$(echo "$line" | awk '{print $2}')
        echo "$(ip_to_int "$ip") $line"
    done | sort -n | awk '{$1=""; print substr($0,2)}'
)

for line in "${SORTED[@]}"; do
    status=$(echo "$line" | awk '{print $1}')
    ip=$(echo "$line" | awk '{print $2}')
    hostname=$(echo "$line" | awk '{print $3}')

    if [[ "$status" == "UP" ]]; then
        ACTIVE=$(( ACTIVE + 1 ))
        if [[ $QUIET -eq 0 ]]; then
            printf "${GREEN}%-18s${RESET} ${YELLOW}%-40s${RESET}\n" "$ip" "$hostname"
        else
            printf "%-18s %s\n" "$ip" "$hostname"
        fi
        if [[ -n "$OUTPUT_FILE" ]]; then
            echo "$ip,$hostname,$TIMESTAMP" >> "$OUTPUT_FILE"
        fi
    fi
done

# ── Résumé ────────────────────────────────────────────────────────────────────
if [[ $QUIET -eq 0 ]]; then
    printf '%.0s─' {1..60}; echo ""
    echo -e "\n${BOLD}Résumé :${RESET}"
    echo -e "  Adresses sondées : ${BOLD}${TOTAL}${RESET}"
    echo -e "  Hôtes actifs     : ${BOLD}${GREEN}${ACTIVE}${RESET}"
    echo -e "  Hôtes inactifs   : ${BOLD}${RED}$(( TOTAL - ACTIVE ))${RESET}"
    [[ -n "$OUTPUT_FILE" ]] && echo -e "  Résultats CSV    : ${BOLD}${OUTPUT_FILE}${RESET}"
    echo ""
fi
