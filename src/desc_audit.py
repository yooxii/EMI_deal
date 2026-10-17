"""测试描述审查：让描述里的「输入电压 / 输出负载」与实际测量数据一致。

描述里的测试条件是从 ORT Plan 抄来的，未必和数据对上，典型有三类：

- 电压写成 ``115VAC&230VAC``，而数据其实是 ``110VAC`` / ``220VAC``；
- 负载写成 ``min load, 50% load and 100% load``，而数据只有 ``25%`` / ``50%`` / ``100%``；
- 负载只写了 ``full load``，而数据有三档，需要补齐。

这里按「数据为准」重写描述里的电压与负载，返回改写后的文本、逐条改动说明与
需要人工确认的提示（一行里出现多段电压 / 负载时不敢乱改，只提示）。
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

# 电压：单个数 + 单位（115VAC / 220Vac / 110V），以及「110&220 VAC」这种单位只写一次的形式
VOLTAGE_PATTERN = re.compile(
    r"(?P<num>\d{1,3})\s*(?P<v>V)\s*(?P<unit>AC|ac|Ac|a\.c\.|A\.C\.)?"
)
SHARED_VOLTAGE_PATTERN = re.compile(
    r"(?P<nums>\d{1,3}(?:\s*(?:&|,|/|and|or)\s*\d{1,3})+)(?P<gap>\s*)(?P<unit>V\s*(?:AC|ac|Ac)?)"
)
# 负载：min load / Min. load / full load / 25% / 25% load
LOAD_PATTERN = re.compile(
    r"(?P<rank>min(?:imum)?\.?|max(?:imum)?\.?|full\.?|nominal)\s*load"
    r"|(?P<pct>\d{1,3}(?:\.\d+)?)\s*%(?:\s*(?P<word>load))?",
    re.IGNORECASE,
)
SEPARATOR_PATTERN = re.compile(r"^\s*(?:[&,、/]|and|or|to)\s*$|^\s*$", re.IGNORECASE)
LOAD_SEPARATOR_PATTERN = re.compile(
    r"^[\s,&/.;]*(?:(?:load|and|or|to)[\s,&/.;]*)*$", re.IGNORECASE
)
DEFAULT_SEPARATORS = (", ", " and ")
VOLTAGE_SEPARATORS = ("&",)  # 描述里只有一个电压、实际有多档时用 & 连接
CONDITION_START = re.compile(r"1\.\s*Test\s*Condition", re.IGNORECASE)
CONDITION_END = re.compile(r"2\.\s*Pass\s*/\s*Fail", re.IGNORECASE)


def _numbers(values: Iterable) -> list[float]:
    """把 ``"220V"`` / ``"25%"`` 之类的字符串取成数值并去重、升序。"""
    result: list[float] = []
    for value in values:
        if value is None:
            continue
        match = re.search(r"\d+(?:\.\d+)?", str(value))
        if not match:
            continue
        number = float(match.group(0))
        if number not in result:
            result.append(number)
    return sorted(result)


def _fmt(number: float) -> str:
    if abs(number - round(number)) < 1e-9:
        return "%d" % int(round(number))
    return ("%s" % number).rstrip("0").rstrip(".")


def _is_separator(text: str) -> bool:
    return bool(SEPARATOR_PATTERN.match(text))


def _is_load_separator(text: str) -> bool:
    """负载枚举之间允许夹着 ``load`` 字样（``25% load, 50%``）。"""
    return bool(LOAD_SEPARATOR_PATTERN.match(text))


def _join_items(
    items: Sequence[str],
    separators: Sequence[str],
    default: Sequence[str] = DEFAULT_SEPARATORS,
) -> str:
    """按原有的分隔符把若干项连起来。

    项数与分隔符个数对不上时（例如描述只写了 ``full load``、数据有三档），
    中间的连接用第一个分隔符、最后一处沿用原来的末尾分隔符，
    这样 ``a, b and c`` 扩成 4 项会得到 ``a, b, c and d``。
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]

    seps = list(separators) or list(default)
    needed = len(items) - 1
    if needed > len(seps):
        seps = [seps[0]] * (needed - 1) + [seps[-1]]
    elif needed < len(seps):
        seps = seps[: needed - 1] + [seps[-1]] if needed > 1 else [seps[-1]]

    pieces = [items[0]]
    for index, item in enumerate(items[1:], start=1):
        pieces.append(seps[index - 1] if index - 1 < len(seps) else seps[-1])
        pieces.append(item)
    return "".join(pieces)


def _collect_runs(
    matches: Sequence[re.Match], text: str, is_separator=_is_separator
) -> list[list[re.Match]]:
    """把相邻（中间只有分隔符）的匹配归成一组，一组视为一个枚举。"""
    runs: list[list[re.Match]] = []
    current: list[re.Match] = []
    for match in matches:
        if current and not is_separator(text[current[-1].end() : match.start()]):
            runs.append(current)
            current = []
        current.append(match)
    if current:
        runs.append(current)
    return runs


def _separators_between(run: Sequence[re.Match], text: str) -> list[str]:
    """取枚举之间的「纯」分隔符；夹了 ``load`` 这种词的退化成逗号。"""
    result: list[str] = []
    for index in range(len(run) - 1):
        between = text[run[index].end() : run[index + 1].start()]
        result.append(between if _is_separator(between) else ", ")
    return result


def _original_text(run: Sequence[re.Match], separators: Sequence[str]) -> str:
    return _join_items([match.group(0).strip() for match in run], separators)


def _audit_voltage(
    line: str, voltages: Sequence[float]
) -> tuple[str, list[str], list[str]]:
    """把一行里的电压枚举换成实际数据的电压。"""
    changes: list[str] = []
    warnings: list[str] = []
    if not voltages:
        return line, changes, warnings

    # 1) 单位只写一次的形式：110&220 VAC
    shared = SHARED_VOLTAGE_PATTERN.search(line)
    if shared:
        described = sorted({float(v) for v in re.findall(r"\d{1,3}", shared.group("nums"))})
        if described == list(voltages):
            return line, changes, warnings
        separators = re.findall(r"\s*(?:&|,|/|and|or)\s*", shared.group("nums"))
        items = [_fmt(value) for value in voltages]
        replacement = (
            _join_items(items, separators, default=VOLTAGE_SEPARATORS)
            + shared.group("gap")
            + shared.group("unit")
        )
        original = shared.group(0)
        line = line[: shared.start()] + replacement + line[shared.end() :]
        changes.append("输入电压：%s → %s" % (original.strip(), replacement.strip()))
        return line, changes, warnings

    # 2) 每个电压各带单位的形式：115VAC&230VAC
    matches = list(VOLTAGE_PATTERN.finditer(line))
    if not matches:
        if re.search(r"voltage", line, re.IGNORECASE):
            warnings.append(
                "输入电压描述里没有具体数值（实际为 %s），请人工确认"
                % "、".join("%sV" % _fmt(value) for value in voltages)
            )
        return line, changes, warnings

    runs = _collect_runs(matches, line)
    if len(runs) > 1:
        # 分频段写法（110Vac/60Hz, and 220Vac/50Hz）：并把对不上的电压按最接近的档位改掉
        described_all = sorted(
            {float(match.group("num")) for run in runs for match in run}
        )
        if described_all == list(voltages):
            return line, changes, warnings

        tokens = sorted(
            [match for run in runs for match in run],
            key=lambda match: match.start(),
            reverse=True,
        )
        fixed: list[float] = []
        for match in tokens:
            value = float(match.group("num"))
            if value in voltages:
                fixed.append(value)
                continue
            new_value = min(voltages, key=lambda item: abs(item - value))
            fixed.append(new_value)
            replacement = "%s%s%s" % (
                _fmt(new_value),
                match.group("v"),
                match.group("unit") or "",
            )
            line = line[: match.start()] + replacement + line[match.end() :]

        if sorted(set(fixed)) == list(voltages):
            changes.append(
                "输入电压：%s → %s"
                % (
                    "、".join("%sV" % _fmt(value) for value in described_all),
                    "、".join("%sV" % _fmt(value) for value in voltages),
                )
            )
            return line, changes, warnings

        warnings.append(
            "输入电压写成多段（描述里是 %s，数据是 %s），未自动修改，请人工确认"
            % (
                "、".join("%sV" % _fmt(value) for value in sorted(set(fixed))),
                "、".join("%sV" % _fmt(value) for value in voltages),
            )
        )
        return line, changes, warnings

    run = runs[0]
    described = sorted({float(match.group("num")) for match in run})
    if described == list(voltages):
        return line, changes, warnings

    separators = _separators_between(run, line)
    original = _original_text(run, separators)
    unit = next((m.group("unit") for m in run if m.group("unit")), "")
    items = ["%s%s%s" % (_fmt(value), run[0].group("v"), unit) for value in voltages]
    replacement = _join_items(items, separators, default=VOLTAGE_SEPARATORS)
    line = line[: run[0].start()] + replacement + line[run[-1].end() :]
    changes.append("输入电压：%s → %s" % (original, replacement))
    return line, changes, warnings


def _load_items(run: Sequence[re.Match], loads: Sequence[float]) -> list[str]:
    """按数据负载生成枚举项。

    描述里有 min / full 这类「档位词」时按大小顺序对应数据：min → 最小档、
    full / max → 最大档；描述里的百分数取数据里最接近的一档，最后把数据里
    没被覆盖到的档位补上（以数据为准）。
    """
    with_word = any(m.group("word") or m.group("rank") for m in run)
    mapped: list[float] = []
    for match in run:
        if not loads:
            break
        if match.group("pct") is not None:
            value = float(match.group("pct"))
            mapped.append(min(loads, key=lambda item: abs(item - value)))
            continue
        rank = (match.group("rank") or "").lower()
        mapped.append(loads[0] if rank.startswith("min") else loads[-1])

    for value in loads:
        if value not in mapped:
            mapped.append(value)
    ordered = sorted(set(mapped)) or list(loads)
    return ["%s%%%s" % (_fmt(value), " load" if with_word else "") for value in ordered]


def _audit_load(
    line: str, loads: Sequence[float]
) -> tuple[str, list[str], list[str]]:
    """把一行里的负载枚举换成实际数据的负载档位。"""
    changes: list[str] = []
    warnings: list[str] = []
    if not loads:
        return line, changes, warnings

    matches = list(LOAD_PATTERN.finditer(line))
    if not matches:
        return line, changes, warnings

    runs = _collect_runs(matches, line, is_separator=_is_load_separator)
    if len(runs) > 1:
        warnings.append(
            "输出负载有多段写法（%s），未自动修改，请人工确认"
            % _original_text(runs[0], _separators_between(runs[0], line))
        )
        return line, changes, warnings

    run = runs[0]
    described = sorted(
        {float(m.group("pct")) for m in run if m.group("pct") is not None}
    )
    has_rank = any(match.group("rank") for match in run)
    if not has_rank and described == list(loads):
        return line, changes, warnings

    separators = _separators_between(run, line)
    original = _original_text(run, separators)
    replacement = _join_items(_load_items(run, loads), separators)
    if replacement == original:
        return line, changes, warnings
    line = line[: run[0].start()] + replacement + line[run[-1].end() :]
    changes.append("输出负载：%s → %s" % (original, replacement))
    return line, changes, warnings


def _condition_bounds(detail: str) -> tuple[int, int]:
    """只审「1. Test Condition」这一段，避免动到 Pass/Fail Criteria。"""
    start = CONDITION_START.search(detail)
    if start is None:
        return 0, len(detail)
    end = CONDITION_END.search(detail, start.end())
    return start.start(), (end.start() if end else len(detail))


def audit_test_detail(
    detail: str, voltages: Iterable, loads: Iterable
) -> tuple[str, list[str], list[str]]:
    """按实际数据校正测试描述里的电压与负载。

    返回 ``(新文本, 改动说明列表, 需人工确认的提示列表)``；没有需要改的地方时
    返回原文与两个空列表。
    """
    voltage_values = _numbers(voltages)
    load_values = _numbers(loads)

    text = detail or ""
    start, end = _condition_bounds(text)
    head, section, tail = text[:start], text[start:end], text[end:]

    changes: list[str] = []
    warnings: list[str] = []
    lines = section.split("\n")
    for index, line in enumerate(lines):
        line, line_changes, line_warnings = _audit_voltage(line, voltage_values)
        changes.extend(line_changes)
        warnings.extend(line_warnings)
        line, line_changes, line_warnings = _audit_load(line, load_values)
        changes.extend(line_changes)
        warnings.extend(line_warnings)
        lines[index] = line

    return head + "\n".join(lines) + tail, changes, warnings


def collect_conditions(report_data: dict) -> tuple[list[float], list[float]]:
    """从解析结果里取出实际用到的电压与负载。"""
    voltages, loads = [], []
    for datas in (report_data or {}).values():
        voltages.append(datas.get("Power"))
        loads.append(datas.get("Load"))
    return _numbers(voltages), _numbers(loads)


def describe_changes(changes: Sequence[str]) -> str:
    """把改动列表拼成一句日志 / 提示用的文本。"""
    return "；".join(changes)
