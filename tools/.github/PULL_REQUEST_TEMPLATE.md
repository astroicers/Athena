## Tool contribution checklist

- [ ] I have signed the **CLA** (required before merge — see CONTRIBUTING.md).
- [ ] Each `<tool_name>.athena-tool.toml` validates against `schema/athena-tool.schema.json`.
- [ ] Layout `catalog/<container>/<tool_name>.athena-tool.toml`: the directory name equals the `container` field, and every `tool_name` is unique across the catalog.
- [ ] `techniques` are real MITRE ATT&CK IDs and accurately describe the tool.
- [ ] Phase 1: the tool is **targetless** (needs no victim-IP injection).
- [ ] `sensitive` is set correctly (`true` → gated/private catalog).
- [ ] This tool is for **authorized** security use only (I understand the dual-use restrictions).
- [ ] The container builds and speaks FastMCP streamable-http on the declared port.

## What does this tool do?

<!-- Short description: what it does, which techniques, typical authorized use. -->
