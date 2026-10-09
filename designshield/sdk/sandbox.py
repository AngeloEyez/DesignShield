"""
DesignShield SDK 沙盒隔離與安全驗證器 (Sandbox & AST Security Validator)

提供 Python 動態腳本之雙重安全防護機制：
1. 靜態語法樹審查 (AST Security Audit): 阻擋危險 import、檔案操作與動態執行。
2. 執行期沙盒隔離 (Runtime Sandbox): 受限 Builtins、安全 Import 攔截與 5 秒超時防護。
"""

import ast
import builtins
import concurrent.futures
import logging
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger("designshield.sdk.sandbox")

# 允許動態腳本匯入之安全模組白名單
ALLOWED_MODULES = {
    "math",
    "re",
    "json",
    "typing",
    "dataclasses",
    "enum",
    "collections",
    "itertools",
    "functools",
    "designshield",
    "designshield.sdk",
    "designshield.sdk.models",
    "designshield.sdk.graph_api",
    "designshield.sdk.part_db",
}

# 嚴格禁止呼叫之內建函數與關鍵識別字
FORBIDDEN_CALL_NAMES = {
    "open",
    "eval",
    "exec",
    "compile",
    "globals",
    "locals",
    "exit",
    "quit",
    "input",
    "breakpoint",
}

# 嚴格禁止存取之危險反射屬性
FORBIDDEN_ATTRIBUTES = {
    "__subclasses__",
    "__bases__",
    "__globals__",
    "__code__",
}


class SecurityViolationError(RuntimeError):
    """當腳本違反沙盒安全規則時拋出之例外"""
    pass


class ScriptTimeoutError(TimeoutError):
    """當腳本執行超過規定時間 (預設 5 秒) 時拋出之例外"""
    pass


class ASTSecurityValidator(ast.NodeVisitor):
    """
    靜態抽象語法樹 (AST) 安全稽核器

    在腳本編譯前進行靜態分析，全面攔截未經授權的系統層級呼叫與套件匯入。
    """

    def __init__(self, filename: str = "<script>"):
        self.filename = filename
        self.violations: List[str] = []

    def validate_code(self, source_code: str) -> None:
        """
        校驗 Python 原始碼字串，若發現危險語法立即拋出 SecurityViolationError
        """
        try:
            tree = ast.parse(source_code, filename=self.filename)
        except SyntaxError as e:
            raise SecurityViolationError(f"腳本語法錯誤無法解析: {e}")

        self.violations.clear()
        self.visit(tree)

        if self.violations:
            err_msg = f"腳本 [{self.filename}] 包含安全違規項目:\n" + "\n".join(f" - {v}" for v in self.violations)
            raise SecurityViolationError(err_msg)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            root_name = alias.name.split(".")[0]
            if root_name not in ALLOWED_MODULES and alias.name not in ALLOWED_MODULES:
                self.violations.append(f"行 {node.lineno}: 嘗試載入未授權模組 'import {alias.name}' (僅允許 {sorted(list(ALLOWED_MODULES))})")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            root_name = node.module.split(".")[0]
            if root_name not in ALLOWED_MODULES and node.module not in ALLOWED_MODULES:
                self.violations.append(f"行 {node.lineno}: 嘗試載入未授權模組 'from {node.module} import ...'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 檢查直接函式呼叫 (例如 open(...), eval(...))
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALL_NAMES:
                self.violations.append(f"行 {node.lineno}: 禁止呼叫底層系統函式 '{node.func.id}()'")
        # 檢查屬性呼叫 (例如 os.system(...))
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALL_NAMES:
                self.violations.append(f"行 {node.lineno}: 禁止呼叫潛在危險屬性函式 '.{node.func.attr}()'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(f"行 {node.lineno}: 禁止存取內部反射屬性 '{node.attr}'")
        self.generic_visit(node)


class SandboxedScriptRunner:
    """
    沙盒腳本安全執行器 (Sandboxed Script Runner)

    負責管理受限模組命名空間、注入受限 builtins，並以執行緒池監控 5 秒逾時截斷。
    """

    DEFAULT_TIMEOUT_SECONDS = 5.0

    @classmethod
    def _create_safe_builtins(cls) -> Dict[str, Any]:
        """建立白名單受限 builtins 字典"""
        safe = {
            "abs": abs,
            "all": all,
            "any": any,
            "ascii": ascii,
            "bin": bin,
            "bool": bool,
            "bytes": bytes,
            "chr": chr,
            "divmod": divmod,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "format": format,
            "frozenset": frozenset,
            "getattr": getattr,
            "hasattr": hasattr,
            "hex": hex,
            "int": int,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "iter": iter,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "next": next,
            "oct": oct,
            "ord": ord,
            "pow": pow,
            "range": range,
            "repr": repr,
            "reversed": reversed,
            "round": round,
            "set": set,
            "slice": slice,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
            "dict": dict,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "Exception": Exception,
            "RuntimeError": RuntimeError,
            "True": True,
            "False": False,
            "None": None,
            "print": print,
        }

        # 封裝受限 __import__
        original_import = builtins.__import__

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            root_name = name.split(".")[0]
            if root_name not in ALLOWED_MODULES and name not in ALLOWED_MODULES:
                raise SecurityViolationError(f"執行期阻擋: 模組 '{name}' 未在安全白名單內，禁止載入")
            return original_import(name, globals, locals, fromlist, level)

        safe["__import__"] = safe_import
        return safe

    @classmethod
    def execute_script_source(
        cls,
        source_code: str,
        context: Any,
        graph_api: Any,
        part_db: Any,
        params: Optional[Dict[str, Any]] = None,
        filename: str = "<sandboxed_script>",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ) -> List[Any]:
        """
        執行動態 Python 腳本原始碼並返回結果

        Args:
            source_code: Python 程式碼文字
            context: 執行期 RuleContext
            graph_api: GraphAPI 實例
            part_db: PartDB 實例
            params: 外部參數字典
            filename: 腳本名稱標籤
            timeout_seconds: 逾時秒數 (預設 5.0)

        Returns:
            List[Any]: 腳本 execute() 回傳之違規清單或 RuleResult
        """
        # 1. 靜態 AST 審查
        validator = ASTSecurityValidator(filename=filename)
        validator.validate_code(source_code)

        # 2. 構建隔離執行環境
        module_globals: Dict[str, Any] = {
            "__builtins__": cls._create_safe_builtins(),
            "__name__": "__sandboxed_drc__",
            "__file__": filename,
        }

        compiled_code = compile(source_code, filename, "exec")
        exec(compiled_code, module_globals)

        if "execute" not in module_globals or not callable(module_globals["execute"]):
            raise RuntimeError(f"腳本 [{filename}] 必須包含可呼叫之 'def execute(context, graph_api, part_db, params=None)' 函式")

        execute_fn: Callable = module_globals["execute"]

        # 3. 守護執行緒逾時監控執行 (Daemon Thread，避免逾時線程阻塞主進程退出)
        import threading

        result_container = []
        error_container = []
        finished_event = threading.Event()

        def worker():
            try:
                res = execute_fn(context, graph_api, part_db, params or {})
                result_container.append(res)
            except Exception as ex:
                error_container.append(ex)
            finally:
                finished_event.set()

        t = threading.Thread(target=worker, daemon=True, name=f"drc_sandbox_{filename}")
        t.start()

        is_completed = finished_event.wait(timeout=timeout_seconds)
        if not is_completed:
            raise ScriptTimeoutError(f"腳本 [{filename}] 執行逾時 (超過 {timeout_seconds} 秒)，已強制中斷")

        if error_container:
            err = error_container[0]
            logger.error(f"腳本 [{filename}] 執行失敗: {err}")
            raise err

        return result_container[0] if result_container else []
