#!/usr/bin/env python3
"""
Container Smoke Test 檢查腳本 (Container Smoke Test)
===================================================

用於驗證 DesignShield Docker 容器叢集（前端、後端、資料庫）健康度與環境一致性。
特別檢測 Docker 容器內 /app/node_modules 與宿主機 package.json 依賴同步狀態，
防止因 Docker 隔離 Volume 導致的 Vite [plugin:vite:import-analysis] 套件遺失錯誤。

使用方式:
    python3 scripts/smoke_test_containers.py
    python3 scripts/smoke_test_containers.py --fix    # 若缺少套件自動執行容器內安裝
"""

import sys
import os
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Tuple

# ANSI 色彩常數
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_CONTAINER = "designshield-frontend-dev"
BACKEND_CONTAINER = "designshield-backend-dev"
POSTGRES_CONTAINER = "designshield-postgres"

FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "8080")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")


def log_header(title: str):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")


def log_pass(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def log_fail(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def log_warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def check_docker_available() -> bool:
    """檢查本地 Docker daemon 是否在線"""
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return res.returncode == 0
    except Exception:
        return False


def get_container_status(container_name: str) -> Tuple[bool, str]:
    """取得特定 Docker 容器運行狀態"""
    try:
        res = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}} (Health: {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}})", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            status_str = res.stdout.strip()
            is_running = "running" in status_str
            return is_running, status_str
        return False, "Not Found"
    except Exception as e:
        return False, str(e)


def check_container_nodes_modules(auto_fix: bool = False) -> Tuple[bool, List[str]]:
    """比對宿主機 package.json 依賴與容器內 /app/node_modules 是否完整同步"""
    pkg_json_path = FRONTEND_DIR / "package.json"
    if not pkg_json_path.exists():
        return False, ["package.json 不存在"]

    try:
        with open(pkg_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"無法解析 package.json: {e}"]

    dependencies = list(data.get("dependencies", {}).keys())
    missing_pkgs = []

    for pkg in dependencies:
        check_cmd = [
            "docker", "exec", FRONTEND_CONTAINER,
            "test", "-e", f"/app/node_modules/{pkg}"
        ]
        res = subprocess.run(check_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            missing_pkgs.append(pkg)

    if missing_pkgs and auto_fix:
        print(f"\n{YELLOW}偵測到容器缺少套件: {missing_pkgs}，自動執行修復中...{RESET}")
        fix_cmd = ["docker", "exec", FRONTEND_CONTAINER, "npm", "install"]
        install_res = subprocess.run(fix_cmd)
        if install_res.returncode == 0:
            log_pass("容器內已成功完成 npm install 修復！重新啟動容器...")
            subprocess.run(["docker", "restart", FRONTEND_CONTAINER], stdout=subprocess.DEVNULL)
            # 重新檢查一次
            missing_pkgs = [
                pkg for pkg in dependencies
                if subprocess.run(["docker", "exec", FRONTEND_CONTAINER, "test", "-e", f"/app/node_modules/{pkg}"]).returncode != 0
            ]

    return len(missing_pkgs) == 0, missing_pkgs


def check_http_endpoint(url: str, timeout: int = 5) -> Tuple[bool, int, str]:
    """檢查 HTTP 端點狀態與內容"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ContainerSmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            content = resp.read().decode("utf-8", errors="ignore")
            return (200 <= status < 400), status, content
    except urllib.error.HTTPError as e:
        return False, e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return False, 0, str(e)


def run_smoke_test(auto_fix: bool = False) -> bool:
    """執行完整容器冒煙測試"""
    log_header("DesignShield 容器環境與依賴冒煙測試 (Container Smoke Test)")

    # 1. 檢查 Docker Daemon
    if not check_docker_available():
        log_fail("Docker 服務未啟動或無法連線，請確認 Docker Daemon 狀態。")
        return False
    log_pass("Docker Daemon 正常在線")

    overall_pass = True

    # 2. 容器生命週期檢查
    log_header("1. 核心容器運行狀態檢查")
    containers = [
        ("前端開發容器", FRONTEND_CONTAINER),
        ("後端 API 容器", BACKEND_CONTAINER),
        ("PostgreSQL 資料庫", POSTGRES_CONTAINER),
    ]

    for label, cname in containers:
        running, status_info = get_container_status(cname)
        if running:
            log_pass(f"{label} ({cname}): {status_info}")
        else:
            log_fail(f"{label} ({cname}) 未正常運行: {status_info}")
            overall_pass = False

    # 3. 前端容器依賴一致性檢查 (關鍵守門員)
    log_header("2. 前端容器 node_modules 依賴同步檢查")
    f_running, _ = get_container_status(FRONTEND_CONTAINER)
    if not f_running:
        log_fail(f"{FRONTEND_CONTAINER} 未運行，略過 node_modules 依賴檢查。")
        overall_pass = False
    else:
        in_sync, missing = check_container_nodes_modules(auto_fix=auto_fix)
        if in_sync:
            log_pass("容器內 /app/node_modules 與宿主機 package.json 依賴 100% 同步！")
        else:
            log_fail(f"容器內缺少依賴套件: {missing}")
            print(f"    {YELLOW}👉 請執行修復指令: docker exec {FRONTEND_CONTAINER} npm install{RESET}")
            overall_pass = False

    # 4. 前端 Vite Dev Server 轉譯冒煙檢查
    log_header("3. 前端 Vite Dev Server 模組轉譯冒煙檢查")
    critical_frontend_modules = [
        ("前端首頁 HTML", f"http://localhost:{FRONTEND_PORT}/"),
        ("前端主入口 (src/main.ts)", f"http://localhost:{FRONTEND_PORT}/src/main.ts"),
        ("拓撲排版核心 (src/utils/dagreTopologyLayout.ts)", f"http://localhost:{FRONTEND_PORT}/src/utils/dagreTopologyLayout.ts"),
        ("SVG 拓撲組件 (src/components/DifferentialTopologySvg.vue)", f"http://localhost:{FRONTEND_PORT}/src/components/DifferentialTopologySvg.vue"),
        ("佐證歷程組件 (src/components/EvidenceDetailsBlock.vue)", f"http://localhost:{FRONTEND_PORT}/src/components/EvidenceDetailsBlock.vue"),
    ]

    for desc, url in critical_frontend_modules:
        ok, code, content = check_http_endpoint(url)
        if ok and "Internal server error" not in content and "Failed to resolve import" not in content:
            log_pass(f"{desc} (HTTP {code}) 編譯與轉譯正常")
        else:
            log_fail(f"{desc} 失敗 (HTTP {code})！")
            if "Failed to resolve import" in content:
                # 擷取關鍵錯誤訊息
                for line in content.splitlines():
                    if "Failed to resolve import" in line:
                        print(f"      {RED}{line.strip()}{RESET}")
            overall_pass = False

    # 5. 後端 API 與健康狀態檢查
    log_header("4. 後端服務健康度檢查")
    backend_url = f"http://localhost:{BACKEND_PORT}/health"
    ok, code, content = check_http_endpoint(backend_url)
    if ok:
        try:
            health_json = json.loads(content)
            if health_json.get("status") == "healthy":
                log_pass(f"後端健康度端點 (HTTP {code}): 系統健康 (healthy)")
                components = health_json.get("components", {})
                for c_key, c_info in components.items():
                    log_pass(f"  └─ [{c_info.get('label', c_key)}]: {c_info.get('message', '正常')}")
            else:
                log_warn(f"後端狀態回傳非 healthy: {health_json.get('status')}")
        except Exception:
            log_pass(f"後端端點回應成功 (HTTP {code})")
    else:
        log_fail(f"無法存取後端健康端點: {backend_url} (HTTP {code})")
        overall_pass = False

    # 總結
    log_header("測試總結")
    if overall_pass:
        print(f"\n{BOLD}{GREEN}🎉 所有 Container Smoke Test 檢查全數通過！容器環境健康無虞。{RESET}\n")
    else:
        print(f"\n{BOLD}{RED}🚨 容器冒煙測試發現異常，請依照上方指引排查並修復。{RESET}\n")

    return overall_pass


if __name__ == "__main__":
    auto_fix = "--fix" in sys.argv or "--auto-fix" in sys.argv
    success = run_smoke_test(auto_fix=auto_fix)
    sys.exit(0 if success else 1)
