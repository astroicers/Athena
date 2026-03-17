#!/usr/bin/env python3
"""
update-project-description.py

從 ROADMAP.yaml + .ai_profile + SRS 自動產生 CLAUDE.md 的「專案概覽」區塊。
呼叫方式：
  - make autopilot-validate（驗證通過後自動呼叫）
  - autopilot 每次啟動時（Phase 1.5）

冪等：內容沒變則不寫入。
"""

import os
import re
import sys

START_MARKER = "<!-- ASP-AUTO-PROJECT-DESCRIPTION: START -->"
END_MARKER = "<!-- ASP-AUTO-PROJECT-DESCRIPTION: END -->"

CLAUDE_MD = "CLAUDE.md"
ROADMAP_FILE = "ROADMAP.yaml"
AI_PROFILE_FILE = ".ai_profile"


def load_yaml_simple(path):
    """簡易 YAML 解析，避免依賴 PyYAML（install.sh 不保證安裝）。
    只處理 key: value 和巢狀一層的 mapping。"""
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        pass

    # fallback: 手動解析扁平 + 一層巢狀
    result = {}
    current_section = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip()
            # 跳過空行和註解
            if not stripped or stripped.startswith("#"):
                continue
            # 偵測巢狀（兩格縮排）
            indent = len(line) - len(line.lstrip())
            # 去掉行內註解
            value_part = stripped.split("#")[0].rstrip()
            if ":" not in value_part:
                continue
            key, _, val = value_part.partition(":")
            key = key.strip()
            val = val.strip()
            if indent >= 2 and current_section is not None:
                if isinstance(result.get(current_section), dict):
                    result[current_section][key] = val if val else None
            else:
                if val == "" or val == "":
                    result[key] = {}
                    current_section = key
                else:
                    result[key] = val
                    current_section = None
    return result


def parse_ai_profile(path):
    """解析 .ai_profile（簡單 key: value 格式）。"""
    profile = {}
    if not os.path.exists(path):
        return profile
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                profile[key.strip()] = val.strip()
    return profile


def extract_srs_summary(roadmap):
    """從 SRS 提取第一段非標題非空行作為專案簡述。"""
    docs = roadmap.get("documents", {})
    srs_path = None
    if isinstance(docs, dict):
        srs_path = docs.get("srs")
    if not srs_path:
        srs_path = "docs/SRS.md"
    if not os.path.exists(srs_path):
        return None

    with open(srs_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 找第一個非空、非標題、非 frontmatter 的段落
    in_frontmatter = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(">"):
            continue
        if stripped.startswith("<!--"):
            continue
        return stripped
    return None


def get_val(data, section, key, default="N/A"):
    """安全取值。"""
    s = data.get(section, {})
    if isinstance(s, dict):
        v = s.get(key, default)
        return v if v else default
    return default


def generate_description(roadmap, profile):
    """組裝專案描述 markdown。"""
    project_name = roadmap.get("project", "（未設定）")
    if project_name == "PROJECT_NAME":
        project_name = "（未設定）"

    p_type = profile.get("type", "N/A")
    p_mode = profile.get("mode", "single")
    p_workflow = profile.get("workflow", "standard")

    # 技術棧
    stack_rows = []
    for label, section, key in [
        ("Frontend", "stack", "frontend"),
        ("Backend", "stack", "backend"),
        ("Database", "stack", "database"),
        ("Infra", "stack", "infra"),
        ("架構風格", "architecture", "style"),
        ("API 風格", "architecture", "api_style"),
        ("認證", "architecture", "auth"),
    ]:
        val = get_val(roadmap, section, key, "none")
        stack_rows.append(f"| {label} | {val} |")

    # 開發規範
    conv_items = []
    for label, key in [
        ("命名", "naming"),
        ("Commit", "commit_format"),
        ("分支策略", "branch_strategy"),
        ("錯誤處理", "error_handling"),
        ("註解語言", "language"),
    ]:
        val = get_val(roadmap, "conventions", key, "N/A")
        conv_items.append(f"- {label}：{val}")

    # 專案簡述
    srs_summary = extract_srs_summary(roadmap)
    summary_text = srs_summary if srs_summary else "（SRS 尚未建立或無內容）"

    lines = [
        f"> 此區塊由 autopilot 自動產生（`make autopilot-validate` 或 autopilot 啟動時），請勿手動編輯。",
        f"> 若需更新，修改 ROADMAP.yaml 後重新執行 `make autopilot-validate`。",
        "",
        f"**專案名稱**：{project_name}",
        f"**類型**：{p_type} | **模式**：{p_mode} | **工作流**：{p_workflow}",
        "",
        "### 技術棧",
        "",
        "| 層 | 技術 |",
        "|---|---|",
    ]
    lines.extend(stack_rows)
    lines.append("")
    lines.append("### 開發規範")
    lines.append("")
    lines.extend(conv_items)
    lines.append("")
    lines.append("### 專案簡述")
    lines.append("")
    lines.append(summary_text)

    return "\n".join(lines)


def main():
    # 檢查必要檔案
    if not os.path.exists(CLAUDE_MD):
        print("  ⚠️  CLAUDE.md 不存在，跳過專案描述產生")
        return 0

    if not os.path.exists(ROADMAP_FILE):
        print("  ⚠️  ROADMAP.yaml 不存在，跳過專案描述產生")
        return 0

    with open(CLAUDE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content:
        print("  ⚠️  CLAUDE.md 缺少 ASP-AUTO-PROJECT-DESCRIPTION 標記，跳過")
        return 0

    # 載入資料
    roadmap = load_yaml_simple(ROADMAP_FILE)
    profile = parse_ai_profile(AI_PROFILE_FILE)

    # 產生描述
    new_desc = generate_description(roadmap, profile)

    # 提取現有描述
    pattern = re.compile(
        re.escape(START_MARKER) + r"\n(.*?)\n" + re.escape(END_MARKER),
        re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        print("  ⚠️  無法解析 ASP-AUTO-PROJECT-DESCRIPTION 區塊，跳過")
        return 1

    existing = match.group(1)
    if existing.strip() == new_desc.strip():
        print("  ℹ️  CLAUDE.md 專案描述已是最新，無需更新")
        return 0

    # 替換
    new_content = content[: match.start(1)] + new_desc + "\n" + content[match.end(1) :]
    with open(CLAUDE_MD, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("  ✅ CLAUDE.md 專案描述已更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
