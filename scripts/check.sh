#!/usr/bin/env bash
# Fails fast with the fix, before a playbook waits minutes on an unreachable host.
set -uo pipefail

env="${1:-dev}"
root="$(cd "$(dirname "$0")/.." && pwd)"
inventory="$root/ansible/inventories/$env"
failed=0

fail() {
  echo "check: $1"
  failed=1
}

command -v uv >/dev/null || fail "uv is missing. Install it from https://docs.astral.sh/uv/."
[ -d "$inventory" ] || fail "ansible/inventories/$env doesn't exist. Copy inventories/dev and edit it."
[ -d "$root/ansible/collections" ] || fail "Ansible collections aren't installed. Run make install."

vault="$inventory/group_vars/all/vault.yml"
if [ ! -f "$vault" ]; then
  fail "No vault for $env. Run make vault-init ENV=$env and fill it from vault.yml.example."
elif ! head -1 "$vault" | grep -q '^\$ANSIBLE_VAULT;'; then
  fail "$vault isn't encrypted. Run: cd ansible && uv run ansible-vault encrypt ${vault#"$root/ansible/"}"
fi

if ! command -v tailscale >/dev/null; then
  fail "tailscale is missing. This machine must be on the tailnet to reach the servers."
elif ! tailscale status >/dev/null 2>&1; then
  fail "Tailscale isn't running here. Run tailscale up, then retry."
fi

exit "$failed"
