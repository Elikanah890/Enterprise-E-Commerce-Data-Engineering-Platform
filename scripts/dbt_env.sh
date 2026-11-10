#!/usr/bin/env bash

if [[ ! -f .env || ! -f .venv-dbt/bin/activate || ! -f dbt_project/ecommerce_dbt/dbt_project.yml ]]; then
    printf 'Run this script from the project root.\n' >&2
    return 1 2>/dev/null || exit 1
fi

source .venv-dbt/bin/activate
set -a
source .env
set +a
export DBT_PROJECT_DIR="$PWD/dbt_project/ecommerce_dbt"
export DBT_PROFILES_DIR="$PWD/dbt_project/ecommerce_dbt"
