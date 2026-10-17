"""EMI-Report 批处理入口（无界面）。

复用 ``EMI-Report.py`` 里的窗口逻辑：以 Qt 离屏平台创建一个不显示的主窗口，
把作业参数直接填进界面对应的输入框，再调用原有的「解析 PDF → 写入模板 → 保存」
流程，从而做到**不弹界面、可批量**生成报告。GUI 版本不受影响。

用法::

    python src/batch.py --job jobs.json            # 作业清单（{"jobs": [...]})
    python src/batch.py --data DIR --week WK2613 --rev A04 --workno AH00... \
        --detail-file detail.txt --date 2026/04/23 [--out DIR] [--name FILE]
    python src/batch.py --job jobs.json --dry-run  # 只做参数与数据检查，不写文件

作业字段（JSON）::

    data_dir    必填，存放该机种 EMI PDF 的目录
    serials     可选，只使用这些序列号的 PDF（数据目录里混有其他序列号时必须给，
                否则模板机种数会超过上限 MAX_UUT_COUNT）
    template    可选，模板 xlsx（默认按 load_qty 选 template/2.1 Conducted EMI Measurement_{N}.xlsx）
    load_qty    可选，负载档数（默认 3）
    week/rev/workno   周期 / 版本 / 工令，写入每个序列号块
    detail      测试描述文本（或 detail_file 指定文本文件）
    test_date   测试日期 YYYY/MM/DD（默认今天）
    image       测试图片路径（可选；留空则按 pic_dir 里的机种名自动匹配）
    pic_dir     测试图片目录（可选；命令行 --pic-dir 或默认 D:\Desktop_Li\WorkDir\PIC\EMI）
    out_dir     报告输出目录（可选，默认数据目录的上一级）
    out_name    报告文件名（可选，默认去掉模板名中的 _<数量> 后缀）
    zip         是否生成 PDF 压缩包（默认否）
    embed       是否把压缩包嵌入 Excel（默认否，需本机 Excel；嵌入后不再单独保留压缩包）
    close_excel 嵌入后是否关闭 Excel（默认否；批处理始终只关闭自己打开的工作簿）
    docx2pdf    数据目录里只有 docx 时是否先用 Word 转出 PDF（默认是，单线程）

输出：一行一个 JSON 结果（ok / out_file / reports / error），退出码 0 表示全部成功。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Sequence

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SRC_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from picmatch import DEFAULT_PIC_DIR  # noqa: E402  (依赖上面的 sys.path 设置)

# 离屏平台：不创建可见窗口，但仍能实例化 QWidget
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 控制台可能是 GBK/CP950，中文输出（帮助、JSON 结果）会抛 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - 特殊流
        pass

logger = logging.getLogger("emi_batch")

TEMPLATE_NAME_PATTERN = re.compile(r"_(\d+)\.xlsx$")


class QuietMessageBox:
    """批量模式下的 QMessageBox 替身：只记日志，不弹窗、不阻塞。"""

    class StandardButton:  # noqa: N801 - 与 Qt 同名枚举保持一致
        No = 0
        Yes = 1
        Ok = 2

    @staticmethod
    def _log(kind: str, args: Sequence[Any]) -> int:
        text = " | ".join(str(a) for a in args[1:] if a is not None)
        logger.warning("批量模式已拦截弹窗[%s]: %s", kind, text)
        return QuietMessageBox.StandardButton.Ok

    @staticmethod
    def warning(*args: Any, **kwargs: Any) -> int:
        return QuietMessageBox._log("warning", args)

    @staticmethod
    def critical(*args: Any, **kwargs: Any) -> int:
        return QuietMessageBox._log("critical", args)

    @staticmethod
    def information(*args: Any, **kwargs: Any) -> int:
        return QuietMessageBox._log("information", args)

    @staticmethod
    def question(*args: Any, **kwargs: Any) -> int:
        QuietMessageBox._log("question", args)
        return QuietMessageBox.StandardButton.No


def load_main_module() -> Any:
    """把 ``src/EMI-Report.py`` 作为模块加载（文件名含连字符，不能直接 import）。"""
    path = os.path.join(SRC_DIR, "EMI-Report.py")
    spec = importlib.util.spec_from_file_location("emi_report_main", path)
    if spec is None or spec.loader is None:  # pragma: no cover - 环境异常
        raise RuntimeError("无法加载 EMI-Report.py: %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # 批量模式：把弹窗换成静默替身，避免无人值守时被对话框卡住
    module.QMessageBox = QuietMessageBox
    return module


def default_template(main_mod: Any, load_qty: int) -> str:
    """按负载档数取 template 目录下的模板绝对路径。"""
    name = "2.1 Conducted EMI Measurement_%d.xlsx" % load_qty
    return os.path.join(REPO_ROOT, main_mod.TEMPLATE_DIR, name)


def load_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    """从 --job 文件或命令行参数组装作业列表。"""
    pic_dir = "" if args.no_image else (args.pic_dir or DEFAULT_PIC_DIR)
    if args.job:
        with open(args.job, encoding="utf-8") as fp:
            payload = json.load(fp)
        jobs = payload.get("jobs") if isinstance(payload, dict) else payload
        if not isinstance(jobs, list):
            raise SystemExit("作业文件格式错误：应为 {\"jobs\": [...]} 或数组")
        for job in jobs:
            # 命令行上的图片目录 / 图片路径优先于作业文件
            job.setdefault("pic_dir", pic_dir)
            if args.no_image:
                job["pic_dir"] = ""
                job["image"] = ""
            if args.pic_dir:
                job["pic_dir"] = args.pic_dir
            if args.image:
                job["image"] = args.image
            if args.no_jitter:
                job["jitter"] = False
        return jobs

    detail = args.detail or ""
    if args.detail_file:
        with open(args.detail_file, encoding="utf-8") as fp:
            detail = fp.read()
    job = {
        "data_dir": args.data,
        "serials": args.serials or [],
        "template": args.template,
        "load_qty": args.load_qty,
        "week": args.week,
        "rev": args.rev,
        "workno": args.workno,
        "detail": detail,
        "test_date": args.date,
        "image": args.image or "",
        "pic_dir": pic_dir,
        "out_dir": args.out,
        "out_name": args.name,
        "zip": args.zip,
        "embed": args.embed,
        "close_excel": args.close_excel,
        "backup_existing": not args.no_backup,
        "docx2pdf": not args.no_docx2pdf,
        "jitter": not args.no_jitter,
    }
    return [job]


def prepare_workspace(job: dict[str, Any]) -> tuple[str, str | None]:
    """准备数据目录：只保留作业指定序列号的 PDF。

    返回 ``(工作目录, 临时目录)``；临时目录不为 None 时由调用方负责清理。
    """
    data_dir = os.path.abspath(job["data_dir"])
    if not os.path.isdir(data_dir):
        raise RuntimeError("数据目录不存在: %s" % data_dir)

    serials = [str(s).strip() for s in (job.get("serials") or []) if str(s).strip()]
    if not serials:
        return data_dir, None

    model = os.path.basename(data_dir.rstrip("\\/"))
    wanted = set(serials)
    pdfs = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
    selected = [f for f in pdfs if f.split("-")[0].strip() in wanted]
    if not selected:
        raise RuntimeError("数据目录中没有报告序列号对应的 PDF: %s" % ", ".join(serials))
    if len(selected) == len(pdfs):
        return data_dir, None

    temp_root = tempfile.mkdtemp(prefix="emi_batch_")
    work_dir = os.path.join(temp_root, model)
    os.makedirs(work_dir, exist_ok=True)
    for name in selected:
        shutil.copy2(os.path.join(data_dir, name), os.path.join(work_dir, name))
    logger.info(
        "数据目录含 %d 份 PDF，按报告序列号挑出 %d 份到临时目录 %s",
        len(pdfs),
        len(selected),
        work_dir,
    )
    return work_dir, temp_root


def order_reports(
    report_data: dict[str, Any], serials: Sequence[str]
) -> dict[str, Any]:
    """按作业给出的序列号顺序重排报告，使模板里的机种块顺序与报告概览一致。"""
    if not serials:
        return report_data
    ordered: dict[str, Any] = {}
    for serial in serials:
        for name in sorted(report_data):
            if name.startswith(str(serial) + "-") or name.split("-")[0] == str(serial):
                ordered[name] = report_data[name]
    for name, datas in report_data.items():
        ordered.setdefault(name, datas)
    return ordered


def ensure_pdfs(data_dir: str, serials: Sequence[str]) -> int:
    """数据目录里只有 docx、没有对应 pdf 时，先用 Word 转出 PDF（单线程）。

    只转换作业关心的序列号；已在运行 Word 时复用其进程，不关掉用户的文档。
    """
    wanted = {str(s).strip() for s in serials if str(s).strip()}
    docx_names = [n for n in os.listdir(data_dir) if n.lower().endswith(".docx")]
    if wanted:
        docx_names = [n for n in docx_names if n.split("-")[0].strip() in wanted]
    missing = [
        n for n in docx_names
        if not os.path.exists(os.path.join(data_dir, os.path.splitext(n)[0] + ".pdf"))
    ]
    if not missing:
        return 0

    logger.info("发现 %d 份 docx 尚未转 PDF，开始用 Word 转换（单线程）", len(missing))
    from docx2pdf import convert_docx_files

    converted, failed = convert_docx_files(
        [os.path.join(data_dir, n) for n in missing]
    )
    logger.info("docx→pdf 完成: 成功 %d, 失败 %d", converted, failed)
    if failed:
        logger.warning("有 %d 份 docx 转换失败，对应序列号将缺少数据", failed)
    return converted


def safe_filename(name: str) -> str:
    """去掉 Windows 文件名非法字符（序列号里可能出现 ``*`` 之类的标记）。"""
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "")
    return name


def replace_names_simultaneously(name: str, pairs) -> str:
    """一次性（并行）替换文件名里的多个字符串。

    逐条替换会在「源序列号与目标序列号互为彼此」时来回倒手（例如 513→514 之后
    又被 514→513 换回去），因此这里用一次正则匹配同时替换。
    """
    if not pairs:
        return name
    pattern = re.compile("|".join(re.escape(old) for old, _ in pairs))
    mapping = dict(pairs)
    return pattern.sub(lambda match: mapping[match.group(0)], name)


def prepare_replaced_data(job: dict[str, Any]) -> tuple[str, str]:
    """按 ``replace_map`` 用 Word 替换工具改写 docx，输出到临时目录。

    返回 ``(工作目录, 临时目录)``。源数据目录只读，不会被改动；
    替换后的 docx 文件名与内容都会变成目标序列号（供 docx→pdf 与报告生成使用）。
    """
    src = os.path.abspath(job["data_dir"])
    if not os.path.isdir(src):
        raise RuntimeError("替换源目录不存在: %s" % src)
    mapping = job.get("replace_map") or {}
    pairs = list(mapping.items()) if isinstance(mapping, dict) else [
        (str(a), str(b)) for a, b in mapping
    ]
    if not pairs:
        raise RuntimeError("replace_map 为空")
    # 部分源文档里序列号后面跟了一个字母（实测 FSM038-GQ1G 的 docx 里是 "…LJb"），
    # 只替换序列号会把这个尾字母留在结果里，因此顺带把「序列号+字母」的变体一并替换
    extra = []
    for old, new in pairs:
        for suffix in ("b", "B"):
            if (old + suffix, new) not in pairs and (old + suffix, new) not in extra:
                extra.append((old + suffix, new))
    pairs = pairs + extra
    # 先替换较长的源字符串（否则 "…LJ" 先被换掉后，"…LJb" 就再也匹配不上了）
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    olds = [old for old, _ in pairs]
    news = [new for _, new in pairs]
    placeholders = ["EMIBATCHPLACEHOLDER%d" % index for index in range(len(pairs))]

    model = os.path.basename(src.rstrip("\\/"))
    temp_root = tempfile.mkdtemp(prefix="emi_repl_")
    work_dir = os.path.join(temp_root, model)
    os.makedirs(work_dir, exist_ok=True)

    from gui.ui_wordreplace import replace_text_in_docx

    # 默认沿用替换工具的「数值小幅抖动」（造差异化数据）；作业给 jitter=false 时
    # 只做纯文本替换，测量值与源文档保持一致
    jitter = bool(job.get("jitter", True))
    if not jitter:
        logger.info("本次替换已关闭数值抖动，测量值保持与源文档一致。")

    docx_names = [n for n in os.listdir(src) if n.lower().endswith(".docx")]
    logger.info(
        "Word 替换: 源=%s, docx=%d 份, 字符串组=%d -> %s",
        src,
        len(docx_names),
        len(pairs),
        work_dir,
    )
    for name in docx_names:
        target_name = safe_filename(replace_names_simultaneously(name, pairs))
        target_path = os.path.join(work_dir, target_name)
        staged = os.path.join(work_dir, "_stage_tmp.docx")
        try:
            # 两段式：先把源串换成占位符、再把占位符换成目标串，
            # 避免「源串与目标串互为彼此」时被后一条替换倒回去
            replace_text_in_docx(
                os.path.join(src, name), staged, olds, placeholders, jitter=False
            )
            replace_text_in_docx(
                staged, target_path, placeholders, news, jitter=jitter
            )
        except Exception:
            # 失败时不要留下半个临时目录（prepare_workspace 的清理逻辑还没接管）
            shutil.rmtree(temp_root, ignore_errors=True)
            raise
        finally:
            if os.path.exists(staged):
                os.remove(staged)

    # 源目录可能还含别的序列号（替换后仍是原样），只保留目标序列号，避免机种数超限
    keep = {str(s).strip() for s in (job.get("serials") or []) if str(s).strip()}
    keep = keep or set(news)
    for name in os.listdir(work_dir):
        if name.split("-")[0].strip() not in keep:
            os.remove(os.path.join(work_dir, name))
    return work_dir, temp_root


def job_model_name(job: dict[str, Any]) -> str:
    """作业对应的机种名：优先作业自带的 ``_model``，其次报告目录名，最后数据目录名。"""
    model = str(job.get("_model") or "").strip()
    if model:
        return model

    out_dir = str(job.get("out_dir") or "").replace("/", "\\")
    for part in reversed([p for p in out_dir.split("\\") if p.strip()]):
        match = re.match(r"^(.+?)\s+ORT Test Report", part)
        if match:
            return match.group(1).strip()

    return os.path.basename(os.path.abspath(job["data_dir"]).rstrip("\\/"))


def resolve_image(job: dict[str, Any]) -> str:
    """测试图片：作业显式给了就用作业的，否则按机种名在同系列图片里挑一张。"""
    explicit = str(job.get("image") or "").strip()
    if explicit:
        if os.path.exists(explicit):
            return explicit
        logger.warning("作业指定的测试图片不存在: %s", explicit)
        return ""

    pic_dir = str(job.get("pic_dir") or "").strip()
    if not pic_dir:
        return ""

    from picmatch import describe_match, find_model_image

    model = job_model_name(job)
    image_path = find_model_image(model, pic_dir)
    if image_path:
        logger.info(
            "机种 %s 匹配到测试图片: %s（%s）",
            model,
            image_path,
            describe_match(model, image_path),
        )
        return image_path

    logger.warning("机种 %s 在 %s 里没有匹配的测试图片，本次按无图生成。", model, pic_dir)
    return ""


def strip_model_suffix(filename: str, model: str) -> str:
    """去掉输出文件名末尾的下划线与机种名（``..._FSF059-00CG.xlsx`` → ``....xlsx``）。"""
    stem, ext = os.path.splitext(filename)
    suffix = "_" + model
    if model and stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return stem + ext


def run_job(main_mod: Any, win: Any, job: dict[str, Any], dry_run: bool = False) -> dict:
    """执行一个作业，返回结果字典。"""
    started_at = time.perf_counter()
    model = os.path.basename(os.path.abspath(job["data_dir"]).rstrip("\\/"))
    load_qty = int(job.get("load_qty") or main_mod.DEFAULT_LOAD_QTY)
    template = job.get("template") or default_template(main_mod, load_qty)
    if not os.path.exists(template):
        raise RuntimeError("模板不存在: %s" % template)

    os.chdir(REPO_ROOT)
    converted = 0
    if job.get("replace_map"):
        # 借用其它周期的同名机种数据：先 Word 替换序列号，再转 PDF
        work_dir, temp_root = prepare_replaced_data(job)
        if job.get("docx2pdf", True):
            converted = ensure_pdfs(work_dir, job.get("serials") or [])
    else:
        if job.get("docx2pdf", True):
            converted = ensure_pdfs(
                os.path.abspath(job["data_dir"]), job.get("serials") or []
            )
        work_dir, temp_root = prepare_workspace(job)
    try:
        os.chdir(REPO_ROOT)
        report_data = main_mod.ProcessPdfThread(work_dir).deal_dirs(work_dir)
        if not report_data:
            raise RuntimeError("没有解析到任何 PDF 数据: %s" % work_dir)
        report_data = order_reports(report_data, job.get("serials") or [])
        serials = sorted({name.split("-")[0] for name in report_data})
        logger.info("解析到 %d 份报告，序列号: %s", len(report_data), ", ".join(serials))
        image_path = resolve_image(job)

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "model": model,
                "template": template,
                "reports": len(report_data),
                "serials": serials,
                "image": image_path,
                "seconds": round(time.perf_counter() - started_at, 2),
            }

        from PySide6.QtCore import QDate

        win.lineEdit_model.setText(work_dir)
        win.lineEdit_template.setText(os.path.abspath(template))
        win.spin_qty.setValue(load_qty)
        win.lineEdit_week.setText(str(job.get("week") or ""))
        win.lineEdit_rev.setText(str(job.get("rev") or ""))
        win.lineEdit_workerno.setText(str(job.get("workno") or ""))
        win.check_diff_workno.setChecked(False)
        win.text_detail.setPlainText(str(job.get("detail") or ""))
        win.lineEdit_img.setText(image_path)
        test_date = str(job.get("test_date") or "")
        parsed_date = QDate.fromString(test_date, "yyyy/MM/dd")
        win.date_test.setDate(parsed_date if parsed_date.isValid() else QDate.currentDate())
        win.settings_value.update(
            {
                # 压缩与嵌入在批处理里同步执行（GUI 走线程 + 事件循环，这里没有事件循环）
                "NeedZip": False,
                "AddZip": bool(job.get("embed")),
                "CloseExcel": bool(job.get("close_excel")),
            }
        )

        os.chdir(REPO_ROOT)
        win.save_file_name = None
        win.main_func(report_data)
        saved = win.save_file_name
        if not saved:
            raise RuntimeError("报告未生成（详见 EMIRper.log）")

        saved_path = os.path.abspath(saved)
        if not os.path.exists(saved_path):
            raise RuntimeError("报告文件未找到: %s" % saved_path)

        # 压缩包：直接同步调用 ZipThread 的打包逻辑（只打包本次用到的 PDF）
        zip_path = None
        if job.get("zip") or job.get("embed"):
            main_mod.ZipThread(work_dir, model).zip_folder()
            zip_path = os.path.join(os.getcwd(), "%s.zip" % model)
            if not os.path.exists(zip_path):
                raise RuntimeError("压缩包未生成: %s" % zip_path)
            logger.info("已生成压缩包: %s", zip_path)

        # 嵌入压缩包：复用主窗口的实现（同时补齐最后一行底边的粗边框）；
        # 嵌入后立即关闭工作簿并保持 Excel 不可见，否则文件被占用无法归档
        if job.get("embed"):
            win.add_zip_to_excel(model, saved, close_workbook=True, visible=False)
            logger.info("压缩包嵌入完成: %s", saved)

        out_dir = job.get("out_dir") or os.path.dirname(os.path.abspath(job["data_dir"]))
        os.makedirs(out_dir, exist_ok=True)
        out_name = job.get("out_name") or strip_model_suffix(
            os.path.basename(saved_path), model
        )
        out_path = os.path.join(out_dir, out_name)
        backup_path = None
        if os.path.abspath(out_path) != saved_path:
            if os.path.exists(out_path):
                # 目标位置已有同名报告（通常是上一周期留下的旧文件）：默认先备份再覆盖
                if job.get("backup_existing", True):
                    stem, ext = os.path.splitext(out_path)
                    backup_path = "%s.bak-%s%s" % (
                        stem,
                        time.strftime("%Y%m%d-%H%M%S"),
                        ext,
                    )
                    shutil.move(out_path, backup_path)
                    logger.info("已备份同名旧报告: %s", backup_path)
                else:
                    os.remove(out_path)
            # Excel 释放文件句柄可能稍有延迟，重试几次再放弃
            for attempt in range(30):
                try:
                    shutil.move(saved_path, out_path)
                    break
                except PermissionError:
                    if attempt == 29:
                        raise
                    time.sleep(1)

        # 压缩包：已嵌入报告时不再单独保留；只要求打包时放到报告旁边
        if zip_path:
            if job.get("embed"):
                try:
                    os.remove(zip_path)
                except OSError:
                    logger.warning("删除临时压缩包失败: %s", zip_path)
                zip_path = None
            else:
                target_zip = os.path.join(out_dir, os.path.basename(zip_path))
                if target_zip != zip_path:
                    if os.path.exists(target_zip):
                        os.remove(target_zip)
                    shutil.move(zip_path, target_zip)
                    zip_path = target_zip

        return {
            "ok": True,
            "model": model,
            "template": os.path.basename(template),
            "reports": len(report_data),
            "serials": serials,
            "out_file": out_path,
            "backup_file": backup_path,
            "zip_file": zip_path,
            "image": image_path,
            "docx_converted": converted,
            "seconds": round(time.perf_counter() - started_at, 2),
        }
    finally:
        os.chdir(REPO_ROOT)
        if temp_root:
            shutil.rmtree(temp_root, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EMI 报告批量生成（无界面）")
    parser.add_argument("--job", help="作业清单 JSON（{\"jobs\": [...]}）")
    parser.add_argument("--data", help="数据目录（含 EMI PDF 的机种文件夹）")
    parser.add_argument("--serials", nargs="*", help="只使用这些序列号的 PDF")
    parser.add_argument("--template", help="模板 xlsx 路径")
    parser.add_argument("--load-qty", type=int, help="负载档数（默认 3）")
    parser.add_argument("--week", help="周期 / D/C")
    parser.add_argument("--rev", help="版本")
    parser.add_argument("--workno", help="工令")
    parser.add_argument("--detail", help="测试描述文本")
    parser.add_argument("--detail-file", help="测试描述文本文件（UTF-8）")
    parser.add_argument("--date", help="测试日期 YYYY/MM/DD")
    parser.add_argument("--image", help="测试图片路径")
    parser.add_argument(
        "--pic-dir",
        default=None,
        help="测试图片目录（默认 %s，按机种名/同系列自动匹配）" % DEFAULT_PIC_DIR,
    )
    parser.add_argument("--no-image", action="store_true", help="不插入测试图片")
    parser.add_argument("--out", help="报告输出目录")
    parser.add_argument("--name", help="报告文件名")
    parser.add_argument("--zip", action="store_true", help="生成 PDF 压缩包")
    parser.add_argument("--embed", action="store_true", help="把压缩包嵌入 Excel")
    parser.add_argument("--close-excel", action="store_true", help="嵌入后关闭 Excel")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="目标目录已有同名报告时直接覆盖（默认先改名备份）",
    )
    parser.add_argument(
        "--no-docx2pdf",
        action="store_true",
        help="数据目录里只有 docx 时不自动用 Word 转 PDF",
    )
    parser.add_argument(
        "--no-jitter",
        action="store_true",
        help="替换序列号时不做数值抖动（测量值保持与源文档一致）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只检查参数与数据，不写文件")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    jobs = load_jobs(args)

    main_mod = load_main_module()
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("Acbel")
    app.setApplicationName("EMI-Report")

    os.chdir(REPO_ROOT)
    logger.info("批处理开始: %d 个作业, dry_run=%s", len(jobs), args.dry_run)
    win = main_mod.EMIWindow()

    failed = 0
    for index, job in enumerate(jobs, start=1):
        logger.info("---- 作业 %d/%d: %s ----", index, len(jobs), job.get("data_dir"))
        try:
            result = run_job(main_mod, win, job, dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001 - 单个作业失败不影响其余作业
            failed += 1
            logger.exception("作业失败: %s", exc)
            result = {"ok": False, "data_dir": job.get("data_dir"), "error": str(exc)}
        result["index"] = index
        print(json.dumps(result, ensure_ascii=False), flush=True)

    logger.info("批处理结束: 成功 %d, 失败 %d", len(jobs) - failed, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    # 离屏窗口在解释器退出时销毁 Qt 对象会触发堆损坏（0xC0000374），
    # 这里显式落盘输出后直接结束进程，绕开析构阶段。
    _code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    logging.shutdown()
    os._exit(_code)
