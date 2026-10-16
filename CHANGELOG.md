# 更新日志

本文件记录 EMI-Report（EMI_deal）的重要变更。
版本号显示在程序「帮助 → 关于」窗口中。

## [2.0] - 2026-10-16

### 新增

- **主界面「序列号」显示区**：位于「补充信息」上方，只读列出数据路径下报告文件名中「-」之前的第一段（自动去重、每行一个）。数据路径变化后自动刷新（500 ms 防抖），也可点击该区域标签立即刷新。
- **Word 替换窗口 · 原字符串集标签可点击**：点击后从源路径获取名称——源为文件夹时遍历其中全部 `.docx`，源为单个文件时取该文件；文件名去掉扩展名后按「-」取第一段，重复的只保留一次。
- **Word 替换窗口 · 目标字符串集标签可点击**：点击后就地整理输入框，把 `\r` / `\n` / `\t` 等格式控制符（连续多个也算一个）统一折叠为单个换行，并去掉每行首尾空白与空行。
- **界面状态持久化**：主窗口全部输入（模板路径、数据路径、负载数量、周期、版本、工令、测试图片、测试细节、测试日期）与三个设置开关自动保存到 `%LOCALAPPDATA%\Acbel\EMI-Report\ui_state.json`，程序异常退出后重新打开自动恢复。采用「变化即保存（300 ms 防抖）+ 原子写 + `sys.excepthook` 兜底 + 正常退出再落盘」四重保障。
- **关键路径日志**：补充启动环境信息（Python / PySide6 / 工作目录 / 日志路径）、PDF 解析明细与汇总、模板读写、报告写入（参数、表头值、行调整、保存路径与用时）、压缩与嵌入、子窗口操作、界面状态存取、未捕获异常等记录；`ErrorLogger` 现在按传入异常对象生成完整 traceback。
- 新增共用模块 `src/naming.py`（从报告文件名提取名称片段）与 `src/gui/widgets.py`（可点击标签 `ClickableLabel`）。
- 新增 `black` / `ruff` 规范配置（见 `pyproject.toml`）。

### 变更

- **代码风格与结构整理**：主程序提取常量区（PDF 解析下标、模板锚点、单元格地址、图片高度等），`main_func` 拆分为 `_write_header` / `_insert_test_image` / `_resize_report_rows` / `_write_measurements`；主界面 `setMainWidget` 拆分；设置窗口改为数据驱动；`show_*` 系列统一走 `_focus_or_create()`。
- 变量与方法命名统一为 snake_case，全部模块补齐类型注解（`from __future__ import annotations`，兼容 Python 3.8）。
- 日志消息由中英混杂统一为中文；日志级别约定为 `INFO` 里程碑 / `WARNING` 可恢复问题 / `DEBUG` 逐份明细 / `ERROR` 失败。
- 子窗口线程中断改用 `requestInterruption()` + `isInterruptionRequested()`，不再使用 `QThread.terminate()`。
- 主窗口默认高度由 450 调整为 520（容纳新增的序列号区）。
- 版本号由 `1.2.0` 升级为 `2.0`；`pyproject.toml` 的版本与描述同步更新（项目名 `pdf-deal` 暂未改动）。

### 修复

- 「导出日志」拿到的是 `getSaveFileName` 返回的元组却当路径使用，必然抛 `TypeError`。
- 模板路径留空时输出文件名计算为空串，导致 `wb.save("")` 保存失败。
- PDF 只有一页时硬取 `pages[1]` 直接崩溃；解析不到数据行时改为明确报错而不是裸 `IndexError`。
- 子线程内创建 `QMessageBox`（线程不安全）与用 `terminate()` 强杀线程（可能残留 Word 进程）。
- `replace_value` 在末尾数值组不完整时抛 `IndexError`，导致该文件替换整体失败。
- 同一子窗口被重复登记进关闭列表。
- 导出日志、日志窗口读取文件未指定编码，中文日志在 Windows 下可能乱码。
- 数据目录不存在、目录内没有 PDF、解析结果为空时静默失败或抛异常，现改为 WARNING 日志 + 提示框并中止。
- 测试图片损坏时中断整份报告生成，现改为记录异常并跳过图片。
- 默认生成报告时表头日志打印的是 openpyxl 的 `Cell` 对象，现打印真实值。
- 多处裸 `except:` 收窄为 `except Exception` 并保留异常信息。

### 文档

- 重写 `README.md`：仓库状态、目录结构、模块职责、端到端流程、Excel 模板契约、日志与配置、代码规范、界面状态持久化、功能记录、待整理事项。
- 新增本更新日志 `CHANGELOG.md`。

### 已知限制

- 状态文件仅保存主窗口的输入与设置开关，两个子窗口（docx 转 pdf、Word 替换）的「上次目录」尚未纳入。
- 需要本机安装 Microsoft Office：Word 用于 docx→pdf，Excel 用于压缩包嵌入；这两条路径的日志已在代码中就位，但未在无 Office 的 CI 环境中实跑。
- `src/ui/` 为废弃的旧界面目录，尚未清理。
