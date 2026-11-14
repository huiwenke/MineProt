#!/usr/bin/env bash
# Shared pipeline for AlphaFold2 and ColabFold source-checkout entrypoints.
set -euo pipefail

system=$1
shift
scripts_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_path=python3
repo=
name_mode=0
site_url=http://127.0.0.1:8081
input_dir=
transform_args=()

usage() {
    echo "Usage: ai/$system/import.sh INPUT --repo NAME [options]"
    echo '--python PATH           Python interpreter (default: python3 from PATH)'
    echo '--scripts-dir PATH      Categorized toolkit/scripts directory'
    echo '--name-mode 0|1|2|3     Prefix, A3M name, random name, or prompt'
    echo '--url URL               MineProt base URL (default: http://127.0.0.1:8081)'
    if [[ $system == colabfold ]]; then
        echo '--zip                   Read zipped ColabFold results'
        echo '--relax                 Select relaxed models'
    fi
}
while (( $# )); do
    case $1 in
        --repo|--python|--scripts-dir|--name-mode|--url)
            if (( $# < 2 )); then
                echo "Error: $1 requires a value." >&2
                exit 2
            fi
            case $1 in
                --repo) repo=$2 ;;
                --python) python_path=$2 ;;
                --scripts-dir) scripts_dir=$2 ;;
                --name-mode) name_mode=$2 ;;
                --url) site_url=$2 ;;
            esac
            shift 2 ;;
        --zip|--relax)
            if [[ $system != colabfold ]]; then
                echo "Error: $1 is only supported for ColabFold." >&2
                exit 2
            fi
            if [[ $1 == --zip ]]; then transform_args+=(-z); else transform_args+=(-r); fi
            shift ;;
        -h|--help) usage; exit 0 ;;
        --*) echo "Error: unknown option $1" >&2; exit 2 ;;
        *)
            if [[ -n $input_dir ]]; then
                echo 'Error: provide exactly one input directory.' >&2
                exit 2
            fi
            input_dir=$1
            shift ;;
    esac
done
if [[ -z $input_dir || ! -d $input_dir || -z $repo || ! $name_mode =~ ^[0-3]$ ]]; then
    echo 'Error: provide an input directory, --repo and a name mode between 0 and 3.' >&2
    usage >&2
    exit 2
fi
site_url=${site_url%/}
temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/mineprot-$system.XXXXXX")
trap 'rm -rf -- "$temp_dir"' EXIT
log_path=$(mktemp "${TMPDIR:-/tmp}/mineprot-$system.XXXXXX.log")
echo "Log path: $log_path"
run_step() {
    printf 'Running:'
    printf ' %q' "$@"
    printf '\n'
    "$@" >> "$log_path" 2>&1 || {
        echo "Step failed; see $log_path" >&2
        return 1
    }
}
run_step "$python_path" "$scripts_dir/ai/$system/transform.py" \
    -i "$input_dir" -o "$temp_dir" -n "$name_mode" \
    --url "$site_url/api/pdb2alphacif/" "${transform_args[@]}"
run_step "$python_path" "$scripts_dir/batch/import_es.py" \
    -i "$temp_dir" -n "$repo" --url "$site_url/api/es" -a
run_step "$python_path" "$scripts_dir/batch/import_repo.py" \
    -i "$temp_dir" -n "$repo" --url "$site_url/api/import2repo/"
echo 'Done.'
