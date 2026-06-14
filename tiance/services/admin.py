from datetime import datetime
from threading import Lock
from pathlib import Path

from tiance.db.sqlite import connect, rows_to_dicts
from tiance.errors import TaskRunning
from tiance.scheduler.runtime import run_tracked


DATA_SOURCES_META = [
    {
        "name": "公告",
        "section_name": "公告",
        "source_tables": ["jydb.lc_announcementinfo"],
        "task_name": "fetch_announcements",
        "schedule_desc": "每小时第 5 分钟",
        "can_refresh": True,
    },
    {
        "name": "龙虎榜",
        "section_name": "龙虎榜",
        "source_tables": ["jydb.lc_7percentchange", "jydb.lc_stiboptradinfo"],
        "task_name": "fetch_rank_list",
        "schedule_desc": "每交易日 16:30",
        "can_refresh": True,
    },
    {
        "name": "主力资金流",
        "section_name": "主力资金流",
        "source_tables": ["wind_admin.ASHAREMONEYFLOW"],
        "task_name": "fetch_money_flow",
        "schedule_desc": "每交易日 16:30",
        "can_refresh": True,
    },
    {
        "name": "K线行情",
        "section_name": "K线行情",
        "source_tables": ["wind_admin.ASHAREEODPRICES"],
        "task_name": None,
        "schedule_desc": "查询时按需获取",
        "can_refresh": False,
    },
    {
        "name": "概念标签",
        "section_name": "概念标签",
        "source_tables": ["jydb.lc_coconcept", "jydb.lc_conceptlist"],
        "task_name": None,
        "schedule_desc": "添加股票时自动打标",
        "can_refresh": False,
    },
    {
        "name": "证券基础信息",
        "section_name": "证券基础信息",
        "source_tables": ["jydb.secumain"],
        "task_name": "reload_securities",
        "schedule_desc": "服务启动时加载到内存",
        "can_refresh": True,
    },
]


class AdminService:
    def __init__(self, db_path: Path, scheduler) -> None:
        self.db_path = db_path
        self.scheduler = scheduler
        self.running_tasks: set[str] = set()
        self.job_functions = {}
        self._task_lock = Lock()

    def trigger_refresh(self, task_name: str) -> dict:
        if not self._can_refresh(task_name):
            return {
                "accepted": False,
                "run_at": None,
                "message": f"任务 {task_name} 不可刷新",
            }

        run_at = datetime.now()
        if self.scheduler is None:
            self._ensure_not_running(task_name)
            return {
                "accepted": True,
                "run_at": run_at.isoformat(timespec="seconds"),
                "message": "测试模式已接收刷新请求",
            }

        self._reserve_task(task_name)
        try:
            self.scheduler.add_job(
                lambda: self._run_reserved_task(task_name),
                trigger="date",
                run_date=run_at,
                id=f"manual_{task_name}_{run_at.timestamp()}",
                replace_existing=False,
            )
        except Exception:
            self._release_task(task_name)
            raise
        return {
            "accepted": True,
            "run_at": run_at.isoformat(timespec="seconds"),
            "message": "已触发刷新",
        }

    def run_task(self, task_name: str, work) -> int:
        self._reserve_task(task_name)
        return self._run_reserved_task(task_name, work)

    def list_data_sources(self) -> list[dict]:
        rows = []
        for item in DATA_SOURCES_META:
            row = dict(item)
            last_run = self._last_run(item["task_name"]) if item["task_name"] else None
            row["last_run"] = last_run
            row["last_status"] = last_run["status"] if last_run else None
            row["last_rows_affected"] = last_run["rows_affected"] if last_run else None
            rows.append(row)
        return rows

    def _last_run(self, task_name: str | None) -> dict | None:
        if not task_name:
            return None
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT *
                FROM task_runs
                WHERE task_name = ?
                ORDER BY started_at DESC, id DESC
                LIMIT 1
                """,
                (task_name,),
            ).fetchone()
        return dict(row) if row else None

    def list_tables(self) -> list[str]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_rows(self, table_name: str, limit: int = 200, offset: int = 0) -> list[dict]:
        if table_name not in self.list_tables():
            return []
        safe_limit = max(0, min(limit, 1000))
        safe_offset = max(0, offset)
        quoted_table_name = table_name.replace('"', '""')
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f'SELECT * FROM "{quoted_table_name}" LIMIT ? OFFSET ?',
                (safe_limit, safe_offset),
            ).fetchall()
        return rows_to_dicts(rows)

    def _can_refresh(self, task_name: str) -> bool:
        return any(
            item["task_name"] == task_name and item["can_refresh"]
            for item in DATA_SOURCES_META
        )

    def _ensure_not_running(self, task_name: str) -> None:
        with self._task_lock:
            if task_name in self.running_tasks:
                raise TaskRunning(f"任务 {task_name} 正在运行中")

    def _reserve_task(self, task_name: str) -> None:
        with self._task_lock:
            if task_name in self.running_tasks:
                raise TaskRunning(f"任务 {task_name} 正在运行中")
            self.running_tasks.add(task_name)

    def _release_task(self, task_name: str) -> None:
        with self._task_lock:
            self.running_tasks.discard(task_name)

    def _run_reserved_task(self, task_name: str, work=None) -> int:
        try:
            task_work = work or self.job_functions.get(task_name) or (lambda: 0)
            return run_tracked(self.db_path, task_name, task_work)
        finally:
            self._release_task(task_name)
