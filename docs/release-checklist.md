# Checklist di rilascio — lasagna v3

Usata dal nodo `close_version` della pipeline `project-manager`.

- [ ] `uv run pytest` verde (la suite include la validazione di `.lasagna/` di questo repo)
- [ ] `uv run ruff check` pulito
- [ ] CI verde su Ubuntu e Windows, Python 3.11 e 3.15
- [ ] `uv run lasagna validate --strict` sul repo
- [ ] le copie in `.lasagna/pipelines/` e `.lasagna/rules.md` riallineate a `src/lasagna/builtin/` e `src/lasagna/protocol/rules.md`, con approvazione (D11): `diff -r` vuoto (AC-V3-039)
- [ ] i blocchi YAML di spec §10.1–10.3 e §11.1 identici ai file (nessun test li controlla ancora: verifica a mano)
- [ ] tabella di tracciabilità completa: ogni AC della spec → ticket chiuso → verifica (test, check o review) con la sua evidenza
- [ ] `uv build` e installazione in un ambiente pulito; `lasagna init` funziona fuori dal repo (AC-V3-043)
- [ ] README.md e README.it.md aggiornati (AC-V3-042, review)
- [ ] licenze: `LICENSE` (Apache-2.0), `LICENSES/MIT-0.txt`, `NOTICE` e `REUSE.toml` coerenti con il contenuto del pacchetto
- [ ] `CHANGELOG.md`: sezione Unreleased spostata sotto la versione
- [ ] versione aggiornata in `pyproject.toml` e `src/lasagna/__init__.py`
- [ ] tag della versione e merge su `main` solo dopo l'approvazione del maintainer
