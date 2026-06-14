import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from tiance.clients.mock_tianyan import MockTianyanClient, Security
from tiance.errors import TianyanUnavailable


class TianyanClient:
    def __init__(self, timeout_seconds: int = 60) -> None:
        self.timeout_seconds = timeout_seconds
        self._security_cache: dict[str, _SecurityMeta] = {}
        self._opencli = _find_opencli()

    def list_securities(self) -> list[Security]:
        rows = self._sql(
            """
            SELECT SECUCODE, SECUABBR
            FROM jydb.secumain
            WHERE SECUCATEGORY = 1
            ORDER BY LISTEDDATE DESC
            LIMIT 200
            """
        )
        return [self._security_from_row(row) for row in rows]

    def search_security(self, query: str) -> Security | None:
        meta = self._find_security(query)
        if meta is None:
            return None
        return Security(secucode=meta.secucode, secuname=meta.secuname)

    def get_daily_kline(self, secucode: str, start: date, end: date) -> list[dict]:
        wind_code = _normalize_secucode(secucode)
        start_text = _yyyymmdd(start)
        end_text = _yyyymmdd(end)
        rows = self._sql(
            f"""
            SELECT
              TRADE_DT,
              S_DQ_OPEN,
              S_DQ_HIGH,
              S_DQ_LOW,
              S_DQ_CLOSE,
              S_DQ_VOLUME,
              S_DQ_ADJCLOSE_BACKWARD,
              S_DQ_ADJFACTOR
            FROM wind_admin.ASHAREEODPRICES
            WHERE S_INFO_WINDCODE = '{_sql_literal(wind_code)}'
              AND TRADE_DT >= '{start_text}'
              AND TRADE_DT <= '{end_text}'
            ORDER BY TRADE_DT ASC
            LIMIT 2000
            """
        )
        return [
            {
                "date": datetime.strptime(str(_get(row, "TRADE_DT")), "%Y%m%d").date(),
                "open": _number(_get(row, "S_DQ_OPEN")),
                "high": _number(_get(row, "S_DQ_HIGH")),
                "low": _number(_get(row, "S_DQ_LOW")),
                "close": _number(_get(row, "S_DQ_CLOSE")),
                "volume": _number(_get(row, "S_DQ_VOLUME")),
                "adj_close_backward": _number(_get_optional(row, "S_DQ_ADJCLOSE_BACKWARD")),
                "adj_factor": _number(_get_optional(row, "S_DQ_ADJFACTOR")),
            }
            for row in rows
        ]

    def get_announcements(self, secucode: str, since: date) -> list[dict]:
        meta = self._find_security(secucode)
        if meta is None:
            return []
        since_text = _date_text(_coerce_date(since))
        rows = self._sql(
            f"""
            SELECT
              ID,
              INNERCODE,
              INFOPUBLDATE,
              INFOTITLE,
              CATEGORYLEVEL1,
              CATEGORYLEVEL2,
              MEDIANAME,
              FILENAME,
              ANNOUNCEMENTID,
              INSERTTIME
            FROM jydb.lc_announcementinfo
            WHERE INNERCODE = {meta.innercode}
              AND INFOPUBLDATE >= '{since_text}'
            ORDER BY INFOPUBLDATE DESC, ID DESC
            LIMIT 200
            """
        )
        return [
            {
                "ann_id": str(_get(row, "ID")),
                "secucode": meta.secucode,
                "title": _get(row, "INFOTITLE") or "",
                "ann_type": _get_optional(row, "CATEGORYLEVEL2"),
                "category_l1": _get_optional(row, "CATEGORYLEVEL1"),
                "category_l1_label": None,
                "publish_at": _get_optional(row, "INFOPUBLDATE") or _get_optional(row, "INSERTTIME"),
                "source": "tianyan",
                "url": None,
                "local_path": _get_optional(row, "FILENAME"),
                "raw_payload": row,
            }
            for row in rows
        ]

    def get_stock_concepts(self, secucode: str) -> list[dict]:
        meta = self._find_security(secucode)
        if meta is None:
            return []
        today_text = date.today().isoformat()
        rows = self._sql(
            f"""
            SELECT
              c.CONCEPTCODE,
              l.CONCEPTNAME,
              l.CLASSNAME,
              l.SUBCLASSNAME
            FROM jydb.lc_coconcept c
            JOIN jydb.lc_conceptlist l ON l.CONCEPTCODE = c.CONCEPTCODE
            WHERE c.INNERCODE = {meta.innercode}
              AND (c.OUTDATE IS NULL OR c.OUTDATE > '{today_text}')
              AND l.CONCEPTSTATE = 1
            ORDER BY l.CLASSNAME, l.SUBCLASSNAME, l.CONCEPTNAME
            LIMIT 80
            """
        )
        return [
            {
                "concept_code": int(_get(row, "CONCEPTCODE")),
                "concept_name": str(_get(row, "CONCEPTNAME") or ""),
                "class_name": str(_get_optional(row, "CLASSNAME") or ""),
                "subclass_name": str(_get_optional(row, "SUBCLASSNAME") or ""),
            }
            for row in rows
        ]

    def get_concept_moneyflow(self, concept_codes: list[int]) -> dict:
        codes = [int(code) for code in concept_codes[:16]]
        if not codes:
            return {"latest_trade_date": None, "items": []}

        trade_dates = [
            str(_get(row, "TRADE_DT"))
            for row in self._sql(
                f"""
                SELECT DISTINCT TRADE_DT
                FROM wind_admin.ASHAREMONEYFLOW
                WHERE TRADE_DT <= '{date.today().strftime("%Y%m%d")}'
                ORDER BY TRADE_DT DESC
                LIMIT 20
                """
            )
        ]
        if not trade_dates:
            return {"latest_trade_date": None, "items": []}

        dt1 = trade_dates[0]
        dt5 = trade_dates[min(4, len(trade_dates) - 1)]
        dt20 = trade_dates[-1]
        today_text = date.today().isoformat()
        items = []
        for code in codes:
            try:
                rows = self._sql(
                    f"""
                    SELECT
                      SUM(CASE WHEN mf.TRADE_DT = '{dt1}' THEN mf.S_MFD_INFLOW ELSE 0 END) AS FLOW_1D,
                      SUM(CASE WHEN mf.TRADE_DT >= '{dt5}' THEN mf.S_MFD_INFLOW ELSE 0 END) AS FLOW_5D,
                      SUM(mf.S_MFD_INFLOW) AS FLOW_20D,
                      COUNT(DISTINCT mf.S_INFO_WINDCODE) AS STOCK_COUNT,
                      MAX(mf.TRADE_DT) AS LATEST_DT
                    FROM wind_admin.ASHAREMONEYFLOW mf
                    WHERE mf.TRADE_DT >= '{dt20}'
                      AND mf.S_INFO_WINDCODE IN (
                        SELECT CONCAT(sm.SECUCODE, CASE WHEN LEFT(sm.SECUCODE, 1) = '6' THEN '.SH' ELSE '.SZ' END)
                        FROM jydb.lc_coconcept cc
                        JOIN jydb.secumain sm ON sm.INNERCODE = cc.INNERCODE AND sm.SECUCATEGORY = 1
                        WHERE cc.CONCEPTCODE = {code}
                          AND (cc.OUTDATE IS NULL OR cc.OUTDATE > '{today_text}')
                      )
                    """
                )
            except TianyanUnavailable:
                continue
            if not rows:
                continue
            row = rows[0]
            items.append(
                {
                    "concept_code": code,
                    "flow_1d": _number(_get_optional(row, "FLOW_1D")) or 0,
                    "flow_5d": _number(_get_optional(row, "FLOW_5D")) or 0,
                    "flow_20d": _number(_get_optional(row, "FLOW_20D")) or 0,
                    "stock_count": int(_number(_get_optional(row, "STOCK_COUNT")) or 0),
                    "latest_trade_date": _get_optional(row, "LATEST_DT"),
                }
            )
        return {"latest_trade_date": dt1, "items": items}

    def _find_security(self, query: str) -> "_SecurityMeta | None":
        normalized = query.strip().upper()
        if not normalized:
            return None
        cache_key = normalized
        if cache_key in self._security_cache:
            return self._security_cache[cache_key]

        six_digit_code = normalized.split(".", maxsplit=1)[0]
        text = _sql_literal(query.strip())
        code_clause = ""
        if re.fullmatch(r"\d{6}", six_digit_code):
            code_clause = f"SECUCODE = '{six_digit_code}' OR"
        text_expr = _sql_text_expr(query.strip())

        rows = self._sql(
            f"""
            SELECT SECUCODE, SECUABBR, CHINAME, INNERCODE, COMPANYCODE
            FROM jydb.secumain
            WHERE SECUCATEGORY = 1
              AND (
                {code_clause}
                SECUABBR = {text_expr}
                OR CHINAME = {text_expr}
                OR SECUABBR LIKE CONCAT('%', {text_expr}, '%')
                OR CHINAME LIKE CONCAT('%', {text_expr}, '%')
              )
            ORDER BY
              CASE
                WHEN SECUCODE = '{_sql_literal(six_digit_code)}' THEN 0
                WHEN SECUABBR = {text_expr} THEN 1
                WHEN CHINAME = {text_expr} THEN 2
                WHEN SECUABBR LIKE CONCAT({text_expr}, '%') THEN 3
                WHEN CHINAME LIKE CONCAT('%', {text_expr}, '%') THEN 4
                ELSE 4
              END,
              LISTEDDATE DESC
            LIMIT 10
            """
        )
        if not rows:
            return None

        meta = self._meta_from_row(rows[0])
        self._security_cache[cache_key] = meta
        self._security_cache[meta.secucode.upper()] = meta
        self._security_cache[meta.secucode.split(".", maxsplit=1)[0]] = meta
        return meta

    def _security_from_row(self, row: dict[str, Any]) -> Security:
        meta = self._meta_from_row(row)
        return Security(secucode=meta.secucode, secuname=meta.secuname)

    def _meta_from_row(self, row: dict[str, Any]) -> "_SecurityMeta":
        code = str(_get(row, "SECUCODE"))
        return _SecurityMeta(
            secucode=_normalize_secucode(code),
            secuname=str(_get(row, "SECUABBR") or _get(row, "CHINAME") or code),
            innercode=int(_get(row, "INNERCODE")),
            companycode=int(_get(row, "COMPANYCODE")),
        )

    def _sql(self, sql: str) -> list[dict[str, Any]]:
        sql = _compact_sql(sql)
        try:
            completed = subprocess.run(
                [
                    self._opencli,
                    "tianyan",
                    "sql",
                    sql,
                    "-f",
                    "json",
                    "--site-session",
                    "persistent",
                    "--keep-tab",
                    "true",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=_tianyan_env(),
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TianyanUnavailable(f"\u5929\u7814\u547d\u4ee4\u4e0d\u53ef\u7528\uff1a{exc}") from exc

        if completed.returncode != 0:
            message = (completed.stdout or completed.stderr or "").strip()
            raise TianyanUnavailable(f"\u5929\u7814\u67e5\u8be2\u5931\u8d25\uff1a{message}")
        return _parse_json_payload(completed.stdout)


def create_tianyan_client(settings):
    if settings.use_mock_tianyan:
        return MockTianyanClient()
    return TianyanClient()


@dataclass(frozen=True)
class _SecurityMeta:
    secucode: str
    secuname: str
    innercode: int
    companycode: int


def _parse_json_payload(output: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char not in "[{":
            continue
        try:
            payload, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
    raise TianyanUnavailable("\u5929\u7814\u8fd4\u56de\u4e0d\u662f\u6709\u6548 JSON")


def _get(row: dict[str, Any], key: str) -> Any:
    if key in row:
        return row[key]
    lower = key.lower()
    if lower in row:
        return row[lower]
    raise KeyError(key)


def _get_optional(row: dict[str, Any], key: str) -> Any:
    try:
        return _get(row, key)
    except KeyError:
        return None


def _find_opencli() -> str:
    command = shutil.which("opencli") or shutil.which("opencli.cmd")
    if command is None:
        raise TianyanUnavailable("\u672a\u627e\u5230 opencli\uff0c\u8bf7\u5148\u5b89\u88c5\u5e76\u914d\u7f6e\u5929\u7814 CLI")
    return command


def _tianyan_env() -> dict[str, str]:
    env = os.environ.copy()
    no_proxy_values = [
        "localhost",
        "127.0.0.1",
        "::1",
        "tianyan.cmschina.com.cn",
        ".cmschina.com.cn",
        "cmschina.com.cn",
    ]
    current = env.get("NO_PROXY") or env.get("no_proxy")
    if current:
        no_proxy_values.extend(part.strip() for part in current.split(",") if part.strip())
    no_proxy = ",".join(dict.fromkeys(no_proxy_values))
    env["NO_PROXY"] = no_proxy
    env["no_proxy"] = no_proxy
    return env


def _compact_sql(sql: str) -> str:
    return " ".join(sql.split())


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _sql_text_expr(value: str) -> str:
    if value.isascii():
        return f"'{_sql_literal(value)}'"
    hex_value = value.encode("utf-8").hex().upper()
    return f"CAST(0x{hex_value} AS CHAR CHARACTER SET utf8mb4)"


def _normalize_secucode(code: str) -> str:
    value = code.strip().upper()
    if "." in value:
        return value
    if value.startswith(("6", "5", "9")):
        return f"{value}.SH"
    if value.startswith(("0", "2", "3")):
        return f"{value}.SZ"
    if value.startswith(("4", "8")):
        return f"{value}.BJ"
    return value


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _yyyymmdd(value: date | datetime | str) -> str:
    return _coerce_date(value).strftime("%Y%m%d")


def _date_text(value: date | datetime | str) -> str:
    return _coerce_date(value).isoformat()


def _number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
