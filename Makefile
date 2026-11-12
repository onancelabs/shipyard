ENV ?= dev
VAULT ?= --ask-vault-pass
INVENTORY := inventories/$(ENV)
PLAY := cd ansible && uv run ansible-playbook -i $(INVENTORY) $(VAULT)
export SSL_CERT_FILE ?= $(shell uv run --frozen python -m certifi 2>/dev/null)

.PHONY: help install lint test check vault-init vault provision configure up verify diag destroy

help:
	@echo "make install | lint | test | check | vault-init | vault | provision | configure | up | verify | diag | destroy  (ENV=$(ENV))"

install:
	uv sync --frozen
	cd ansible && uv run ansible-galaxy collection install -r requirements.yml -p ./collections

lint:
	uv run yamllint .
	uv run ansible-lint ansible
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest -q

check:
	@./scripts/check.sh $(ENV)

vault-init:
	cd ansible && uv run ansible-vault create $(INVENTORY)/group_vars/all/vault.yml

vault:
	cd ansible && uv run ansible-vault edit $(INVENTORY)/group_vars/all/vault.yml

provision: check
	$(PLAY) playbooks/provision.yml

configure: check
	$(PLAY) playbooks/configure.yml

up: check
	$(PLAY) playbooks/site.yml

verify:
	$(PLAY) playbooks/verify.yml

diag:
	$(PLAY) playbooks/diag.yml

destroy:
	@test "$(CONFIRM)" = "$(ENV)" || { echo "This deletes the $(ENV) servers. Re-run with CONFIRM=$(ENV)."; exit 1; }
	$(PLAY) playbooks/destroy.yml
