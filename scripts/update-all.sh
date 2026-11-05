#!/usr/bin/env bash
set -o errexit

main() {
  local -r root=$(dirname "${BASH_SOURCE[0]}")

  for country in "at" "be" "ch" "cz" "de" "ee" "es" "fi" "ge" "hr" "hu" "it" "li" "lv" "nl" "pl" "ro" "se" "si" "sk" "ua" "no" "gb"; do
    echo "---> Updating bank registry for: ${country}"
    python "${root}/get_bank_registry_${country}.py"
  done
}

main
