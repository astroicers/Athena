# Contributing to Athena SDK

歡迎貢獻！在合併任何 PR 之前，貢獻者必須簽署 **CLA（Contributor License Agreement）**。

## 為什麼需要 CLA

`athena-sdk` 採 Apache-2.0，而 Athena 的核心（`athena-core`）採 BSL 1.1 商業授權。CLA 授予必要權利，讓社群貢獻能被整合進商業核心並在需要時 relicense（精神對齊 Apache 個人/公司 CLA，ICLA/CCLA）。DCO 不足以達成此目的（不轉讓額外權利），故本專案採 CLA。詳見 Athena ADR-172。

## CLA 流程

> **目前暫不接受外部程式碼貢獻。** CLA 全文、法定受讓實體與簽署流程（CLA assistant bot）將於開放貢獻前一併正式發布。歡迎以 issue 回報問題與建議。

在 CLA 定稿並生效前，本 repo 不接受對外 PR 合併。

## 開發約定

- `cargo test` 與 `cargo clippy --all-targets -- -D warnings` 必須通過。
- SDK 是**純契約 crate**：零 impl、零 SQL、近零依賴（ADR-171 D1）。請勿在此加入實作或第三方重依賴。
- 契約表面變更需更新 [CHANGELOG.md](CHANGELOG.md) 並遵守 semver（0.x 期間破壞性變更需明記）。

## 行為準則

見 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 授權

提交即表示你的貢獻將以 Apache-2.0 授權，並在 CLA 生效後受其條款約束。
