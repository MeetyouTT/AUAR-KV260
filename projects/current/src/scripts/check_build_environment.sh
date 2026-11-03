#!/usr/bin/env bash
# Check the selected toolchain only. Does not build or access a board.
set -eo pipefail

if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' \
        'Usage: bash scripts/check_build_environment.sh' \
        'Optional: AURA_VITIS_SETTINGS=/path/to/Vitis/2022.2/settings64.sh' \
        'Checks the AURA 2022.2 build baseline; does not certify reproducibility.'
    exit 0
fi
if [[ $# -ne 0 ]]; then
    printf '%s\n' 'ERROR: unknown argument; use --help.' >&2
    exit 2
fi

if [[ -n "${AURA_VITIS_SETTINGS:-}" ]]; then
    if [[ ! -r "$AURA_VITIS_SETTINGS" ]]; then
        printf '%s\n' 'ERROR: AURA_VITIS_SETTINGS is not readable.' >&2
        exit 2
    fi
    # Vendor settings scripts are loaded before nounset is enabled.
    source "$AURA_VITIS_SETTINGS"
fi
set -u

for tool in vivado v++; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'ERROR: %s is missing; load the verified Vitis settings64.sh or set AURA_VITIS_SETTINGS.\n' "$tool" >&2
        exit 2
    fi
done

if ! vivado_output=$(vivado -version 2>&1); then
    printf '%s\n' 'ERROR: vivado -version failed.' >&2
    exit 2
fi
if ! vitis_output=$(v++ --version 2>&1); then
    printf '%s\n' 'ERROR: v++ --version failed.' >&2
    exit 2
fi

if [[ "$vivado_output" =~ Vivado[[:space:]]+v([0-9]{4}\.[0-9]+) ]]; then
    vivado_version=${BASH_REMATCH[1]}
else
    printf '%s\n' 'ERROR: unable to identify the Vivado version.' >&2
    exit 2
fi
if [[ "$vitis_output" =~ v\+\+[[:space:]]+v([0-9]{4}\.[0-9]+) ]]; then
    vitis_version=${BASH_REMATCH[1]}
else
    printf '%s\n' 'ERROR: unable to identify the v++ version.' >&2
    exit 2
fi

printf 'Vivado=%s\nv++=%s\n' "$vivado_version" "$vitis_version"
if [[ "$vivado_version" != 2022.2 || "$vitis_version" != 2022.2 ]]; then
    printf '%s\n' 'ERROR: selected tools differ from the locked AURA 2022.2 baseline.' >&2
    exit 2
fi
printf '%s\n' \
    'PASS: Vivado/v++ release versions match the AURA 2022.2 baseline.' \
    'Scope: tool release versions only; licenses, IP, builds and board results remain separate checks.'
