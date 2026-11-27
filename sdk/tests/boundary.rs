// SPDX-License-Identifier: Apache-2.0
//! ADR-171 D1 boundary: `athena-sdk` is a pure contract crate — **zero `athena-*` deps** (Phase 2
//! canonical: the v0.1 types are defined here and `athena-types` re-exports them), zero SQL. This
//! is a pure-stable dependency-boundary forcing function — no nightly / cargo-public-api needed.

#[test]
fn sdk_has_no_impl_or_sql_deps() {
    let manifest = include_str!("../Cargo.toml");
    let doc: toml::Value = toml::from_str(manifest).expect("Cargo.toml parses");

    let deps = doc
        .get("dependencies")
        .and_then(|d| d.as_table())
        .expect("[dependencies] table present");

    for name in deps.keys() {
        // Phase 2 (canonical): the SDK is a leaf — ZERO athena-* deps.
        assert!(
            !name.starts_with("athena-"),
            "athena-sdk (Phase 2 canonical) must have ZERO athena-* deps; found `{name}` (ADR-171 D1)"
        );
        // The SDK is contract-only: no SQL, ever.
        assert_ne!(name, "sqlx", "athena-sdk must be SQL-free (ADR-171 D1)");
    }
}
