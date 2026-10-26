#!/usr/bin/env python3
"""AI Master Engineer Automation Tools — Binh 13 Analyzer (macOS).

Provides automated commands for AI agents and developers:
- status: Display active task, current state, git status, and checkpoint info.
- audit: Comprehensive integrity audit of directories, core files, and python syntax.
- resume: Extract exact in-flight task resumption point and instructions.
- validate-docs: Verify all markdown links across .ai/ and root files to prevent dead links.
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path
import py_compile
import re
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_DIR = REPO_ROOT / ".ai"


def color(text: str, code: str) -> str:
    """Applies ANSI terminal color codes."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(text: str) -> str:
    return color(text, "1")


def green(text: str) -> str:
    return color(text, "32")


def yellow(text: str) -> str:
    return color(text, "33")


def red(text: str) -> str:
    return color(text, "31")


def cyan(text: str) -> str:
    return color(text, "36")


# =============================================================================
# COMMAND: status (ai:status)
# =============================================================================
def cmd_status() -> int:
    """Displays active task, verified state, git status, and latest test status."""
    print(bold(cyan("\n=== [AI:STATUS] BINH 13 MASTER ENGINEER STATUS ===")))

    # 1. Active Task
    active_task_file = AI_DIR / "state" / "ACTIVE_TASK.md"
    if active_task_file.exists():
        content = active_task_file.read_text(encoding="utf-8")
        task_match = re.search(r"\*\*Nhiệm vụ hiện tại:\*\*\s*(.+)", content)
        status_match = re.search(r"\*\*Trạng thái nhiệm vụ:\*\*\s*(.+)", content)
        task_name = task_match.group(1).strip() if task_match else "Unknown"
        task_status = status_match.group(1).strip() if status_match else "Unknown"
        print(f"\n{bold('Nhiệm vụ hiện tại:')} {task_name}")
        print(f"{bold('Trạng thái:')}        {task_status}")
    else:
        print(f"\n{yellow('Cảnh báo:')} Không tìm thấy .ai/state/ACTIVE_TASK.md")

    # 2. Checkpoint
    checkpoint_file = AI_DIR / "state" / "CHECKPOINT.md"
    if checkpoint_file.exists():
        content = checkpoint_file.read_text(encoding="utf-8")
        step_match = re.search(r"## 4\. BƯỚC TIẾP THEO.*?\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if step_match:
            first_lines = [line.strip() for line in step_match.group(1).strip().splitlines() if line.strip()][:3]
            print(f"{bold('Điểm tiếp tục:')}    " + " ".join(first_lines))

    # 3. Git Status
    try:
        git_res = subprocess.run(["git", "status", "--short"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
        changes = git_res.stdout.strip().splitlines()
        if changes:
            print(f"\n{bold('Git Working Tree:')} {yellow(f'{len(changes)} thay đổi chưa commit')}")
            for c in changes[:5]:
                print(f"  {c}")
            if len(changes) > 5:
                print(f"  ... và {len(changes) - 5} file khác.")
        else:
            print(f"\n{bold('Git Working Tree:')} {green('Sạch sẽ (Clean - Không có thay đổi chưa commit)')}")
    except Exception as e:
        print(f"\n{red('Lỗi kiểm tra Git:')} {e}")

    # 4. Test Status
    test_status_file = AI_DIR / "state" / "TEST_STATUS.md"
    if test_status_file.exists():
        content = test_status_file.read_text(encoding="utf-8")
        res_match = re.search(r"\*\*Kết quả chung:\*\*\s*(.+)", content)
        time_match = re.search(r"\*\*Thời gian chạy:\*\*\s*(.+)", content)
        if res_match:
            print(f"\n{bold('Kiểm thử gần nhất:')} {green(res_match.group(1).strip())}")
        if time_match:
            print(f"{bold('Thời gian chạy:')}   {time_match.group(1).strip()}")

    print(bold(cyan("===================================================\n")))
    return 0


# =============================================================================
# COMMAND: audit (ai:audit)
# =============================================================================
def cmd_audit() -> int:
    """Comprehensive integrity audit of directory layout, key files, and python syntax."""
    print(bold(cyan("\n=== [AI:AUDIT] BINH 13 SYSTEM INTEGRITY AUDIT ===")))
    errors = 0
    warnings = 0

    # 1. Directory Structure Audit
    required_dirs = [
        "app/core",
        "app/vision",
        "app/ui",
        "app/ui/components",
        "app/services",
        "app/database",
        "config",
        "scripts",
        "tests",
        ".ai",
        ".ai/state",
        ".ai/plans",
        ".ai/workflows",
        ".ai/modules",
        ".ai/logs",
    ]
    print(f"\n{bold('1. Kiểm tra cấu trúc thư mục:')}")
    for d in required_dirs:
        p = REPO_ROOT / d
        if p.is_dir():
            print(f"  {green('✓')} {d}")
        else:
            print(f"  {red('✗ THIẾU THƯ MỤC:')} {d}")
            errors += 1

    # 2. Key Master Documents Audit
    required_docs = [
        "MASTER_CONTEXT.md",
        "GEMINI.md",
        "AGENTS.md",
        ".ai/MASTER_RULES.md",
        ".ai/PROJECT_VISION.md",
        ".ai/PROJECT_INVENTORY.md",
        ".ai/ARCHITECTURE.md",
        ".ai/MODULE_MAP.md",
        ".ai/DATA_FLOW.md",
        ".ai/GAME_RULES.md",
        ".ai/DECISIONS.md",
        ".ai/state/CURRENT_STATE.md",
        ".ai/state/ACTIVE_TASK.md",
        ".ai/state/NEXT_ACTIONS.md",
        ".ai/state/KNOWN_ISSUES.md",
        ".ai/state/TEST_STATUS.md",
        ".ai/state/CHECKPOINT.md",
        ".ai/plans/ROADMAP.md",
        ".ai/plans/IMPLEMENTATION_PLAN.md",
        ".ai/plans/BACKLOG.md",
        ".ai/workflows/SESSION_WORKFLOW.md",
        ".ai/workflows/CHANGE_APPROVAL_POLICY.md",
        ".ai/workflows/NEW_FEATURE.md",
        ".ai/workflows/DEBUG_WORKFLOW.md",
        ".ai/workflows/REFACTOR_WORKFLOW.md",
        ".ai/workflows/TESTING_WORKFLOW.md",
        ".ai/workflows/RELEASE_WORKFLOW.md",
        ".ai/workflows/RESUME_TASK.md",
        ".ai/modules/CORE_DOMAIN.md",
        ".ai/modules/VISION_PIPELINE.md",
        ".ai/modules/UI_PRESENTATION.md",
        ".ai/modules/DATABASE_PERSISTENCE.md",
        ".ai/modules/SERVICES_ORCHESTRATION.md",
        ".ai/logs/CHANGELOG.md",
    ]
    print(f"\n{bold('2. Kiểm tra tài liệu hệ thống (.ai & Root):')}")
    for doc in required_docs:
        p = REPO_ROOT / doc
        if p.is_file() and p.stat().st_size > 50:
            print(f"  {green('✓')} {doc}")
        else:
            print(f"  {red('✗ THIẾU HOẶC RỖNG:')} {doc}")
            errors += 1

    # 3. Python Syntax Compilation Check
    print(f"\n{bold('3. Kiểm tra cú pháp Python (Syntax Validation):')}")
    py_files = list((REPO_ROOT / "app").rglob("*.py")) + list((REPO_ROOT / "tests").rglob("*.py"))
    syntax_errs = 0
    for pf in py_files:
        try:
            py_compile.compile(str(pf), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"  {red('✗ LỖI CÚ PHÁP:')} {pf.relative_to(REPO_ROOT)}: {e}")
            syntax_errs += 1
            errors += 1

    if syntax_errs == 0:
        print(f"  {green('✓')} Toàn bộ {len(py_files)} files Python biên dịch hợp lệ không có lỗi cú pháp.")

    # 4. Summary
    print(f"\n{bold('Kết Quả Audit:')}")
    if errors == 0:
        print(f"  {green(bold('HOÀN TOÀN HỢP LỆ — Hệ thống đạt chuẩn 100% không có lỗi.'))}")
    else:
        print(f"  {red(bold(f'PHÁT HIỆN {errors} LỖI CẦN XỬ LÝ.'))}")

    print(bold(cyan("===================================================\n")))
    return 0 if errors == 0 else 1


# =============================================================================
# COMMAND: resume (ai:resume)
# =============================================================================
def cmd_resume() -> int:
    """Extracts in-flight task resumption point and instructions."""
    print(bold(cyan("\n=== [AI:RESUME] ĐIỂM TIẾP TỤC NHIỆM VỤ DỞ DANG ===")))

    checkpoint_file = AI_DIR / "state" / "CHECKPOINT.md"
    active_task_file = AI_DIR / "state" / "ACTIVE_TASK.md"

    if not checkpoint_file.exists():
        print(f"{yellow('Không tìm thấy CHECKPOINT.md.')} Vui lòng đọc .ai/state/ACTIVE_TASK.md để xác định nhiệm vụ.")
        return 1

    content = checkpoint_file.read_text(encoding="utf-8")
    print(content)
    print(bold(cyan("===================================================\n")))
    return 0


# =============================================================================
# COMMAND: validate-docs (ai:validate-docs)
# =============================================================================
def cmd_validate_docs() -> int:
    """Scans all markdown files in .ai/ and root, extracts links, and verifies targets exist."""
    print(bold(cyan("\n=== [AI:VALIDATE-DOCS] KIỂM TRA TÍNH TOÀN VẸN LIÊN KẾT TÀI LIỆU ===")))

    md_files = list(AI_DIR.rglob("*.md")) + [
        REPO_ROOT / "MASTER_CONTEXT.md",
        REPO_ROOT / "GEMINI.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
    ]

    total_links = 0
    broken_links = 0

    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md in md_files:
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8")
        rel_path = md.relative_to(REPO_ROOT)

        for match in link_pattern.finditer(text):
            total_links += 1
            label = match.group(1)
            raw_url = match.group(2).strip()

            # Ignore external web URLs or mailto
            if raw_url.startswith("http://") or raw_url.startswith("https://") or raw_url.startswith("mailto:"):
                continue

            # Strip anchors (e.g. #L10-L20)
            url_no_anchor = raw_url.split("#")[0].strip()

            if url_no_anchor.startswith("file://"):
                target_clean = url_no_anchor[7:]
            else:
                target_clean = url_no_anchor

            if not target_clean:
                continue

            target_path = Path(target_clean)
            if not target_path.is_absolute():
                resolved_target = (md.parent / target_path).resolve()
            else:
                resolved_target = target_path.resolve()

            if not resolved_target.exists():
                print(f"  {red('✗ LIÊN KẾT GÃY')} trong [{rel_path}]:")
                print(f"    Label:  '{label}'")
                print(f"    Target: '{target_clean}'")
                broken_links += 1

    print(f"\n{bold('Kết Quả Kiểm Tra:')} Đã quét {total_links} liên kết trong {len(md_files)} tài liệu Markdown.")
    if broken_links == 0:
        print(f"  {green(bold('100% LIÊN KẾT HỢP LỆ — Không có liên kết gãy nào!'))}")
        print(bold(cyan("===================================================\n")))
        return 0
    else:
        print(f"  {red(bold(f'PHÁT HIỆN {broken_links} LIÊN KẾT GÃY CẦN SỬA!'))}")
        print(bold(cyan("===================================================\n")))
        return 1


# =============================================================================
# CLI ROUTER
# =============================================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="AI Master Engineer Automation Tools")
    parser.add_argument("command", choices=["status", "audit", "resume", "validate-docs"], help="Subcommand to execute")
    args = parser.parse_args()

    if args.command == "status":
        return cmd_status()
    elif args.command == "audit":
        return cmd_audit()
    elif args.command == "resume":
        return cmd_resume()
    elif args.command == "validate-docs":
        return cmd_validate_docs()
    return 0


if __name__ == "__main__":
    sys.exit(main())
