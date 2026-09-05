# Development

- This branch develops code2map 0.4.0 from the public repository history.
- Read README.md, spec.md and docs/context/architecture.md before changing the engine.
- Preserve the existing build command and INDEX.md / MAP.json / parts output contract.
- New reusable APIs live in code2map.context; language-specific parsing belongs in adapters.
- Verify with `uv run pytest` and `uv run ruff check .`.
- Do not execute input source code or access a database/LLM during indexing or packing.
