# EMI-Report（EMI_deal）

EMI 传导骚扰（Conducted EMI）测试报告自动化工具：把 ELEKTRA 导出的 EMI PDF 报告解析成数据，按模板写入 Excel，并生成 / 嵌入原始 PDF 压缩包，产出一份可直接继续整理的报告底稿。界面基于 PySide6（QMainWindow + QThread）。

- 主入口：[src/EMI-Report.py](src/EMI-Report.py)，窗口标题 `EMI-Report`
- 版本：`2.8`（显示在「帮助 → 关于」窗口），变更历史见 [CHANGELOG.md](CHANGELOG.md)
- 作者：`Lucas Li`（Lucas_Li@acbel.com）
- 面向使用者的说明：[使用须知/使用须知.md](使用须知/使用须知.md)
- 远程仓库：https://github.com/yooxii/EMI_deal.git

---

## 1. 仓库与同步状态

| 项 | 值 |
| --- | --- |
| 远程 | `https://github.com/yooxii/EMI_deal.git`（origin） |
| 当前分支 | `master` |
| 当前提交 | `2.8` 版本提交（插入机种测试图片、修复删行后格式错乱与测试描述框右边框） |
| 与远程关系 | `2.2.1` 版本提交后与 `origin/master` 同步 |
| 提交总数 | 16（含 `2.0` / `2.1` / `2.2` / `2.2.1` 版本提交） |
| 工作区 | `2.0` 的改动已提交；`DealPdf.log` 被 `.gitignore` 忽略 |
| 工作树 | 单一工作树 `E:/Desktop/Code/ORT/EMI_deal`，无 stash、无 tag |
| 版本要求 | `.python-version` → `3.8`；`pyproject.toml` → `requires-python = ">=3.8"`；依赖由 `uv` 管理，索引为清华源 |

本次核对时，本地 `master` 曾落后 `origin/master` 6 个提交（`4b121a4` → `c1dc25e`，远程把 `src/ui` 重构成了 `src/gui` 并新增日志系统）。当时的本地未提交改动（`src/EMI-Report.py`、`src/docx2pdf.py`、`.vscode/launch.json`、`uv.lock`、未跟踪的 `.vscode/tasks.json` 与 `src/ui/ui_setting.py`）已备份到 `E:\Desktop\Code\ORT\_EMI_deal_backup_20261016_092429`，随后丢弃并快进合并到 `c1dc25e`。

## 2. 目录结构

```
EMI_deal/
├─ src/
│  ├─ EMI-Report.py                 # 主入口：EMIWindow 主窗口 + 2 个工作线程
│  ├─ batch.py                      # 无界面批处理入口：离屏驱动同一套流程批量出报告
│  ├─ logger.py                     # 日志基础设施：主日志 / 错误日志 / 装饰器
│  ├─ naming.py                     # 从报告文件名提取名称片段（序列号等）
│  ├─ picmatch.py                   # 按机种名（含同系列前 6 位）在图片目录里匹配测试图片
│  ├─ docx2pdf.py                   # 命令行版 docx→pdf 脚本（与 GUI 版功能重叠）
│  ├─ test.py                       # 开发期试验：Word 表格读写（含本机绝对路径）
│  ├─ test_openpyxl.py              # 开发期试验：删除模板 Setup 前 4 行
│  ├─ gui/                          # 现役 GUI 层（纯代码构建界面，不用 .ui 文件）
│  │  ├─ mainWin.py                 # MainWindow 主界面 + HoverLineEdit 图片悬停预览 + 序列号区
│  │  ├─ ui_docx2pdf.py             # “docx 转 pdf” 子窗口 + ConvertThread
│  │  ├─ ui_wordreplace.py          # “Word 替换” 子窗口 + 替换线程
│  │  ├─ widgets.py                 # 可复用小部件：ClickableLabel（可点击标签）
│  │  ├─ app_state.py               # 界面状态持久化（JSON + 原子写）
│  │  ├─ res.qrc                    # Qt 资源定义（prefix: emipdf）
│  │  ├─ res_rc.py                  # 由 res.qrc 编译出的资源模块（约 1.5 MB）
│  │  └─ __init__.py
│  └─ ui/                           # 旧 Qt Designer 界面，已无任何模块引用（遗留）
│     ├─ EMC.ui / ui_EMC.py         # 旧主界面（ui_EMC.py 反而 import gui.res_rc）
│     ├─ docx2pdf.ui                # 旧 docx2pdf 界面
│     ├─ acbel_logo.jpg / acbel_logo_s.jpg / acbel-1.jpg
│     └─ __init__.py
├─ template/                        # Excel 报告模板（含 Setup 参数表）
│  ├─ 2.1 Conducted EMI Measurement_1.xlsx     # 1 档负载（每机种 4 行）
│  ├─ 2.1 Conducted EMI Measurement_3.xlsx     # 3 档负载（每机种 12 行）
│  ├─ 2.1 Conducted EMI Measurement_4.xlsx     # 4 档负载（每机种 16 行）
│  ├─ 2.1 Conducted EMI Measurement_10.xlsx    # 10 档负载（每机种 40 行）
│  ├─ 2.1 Conducted EMI Measurement_AMZ.xlsx   # 客户专用版式（需手动指定）
│  └─ 2.1 Conducted EMI Measurement_Vdc.xlsx   # 直流版式（需手动指定）
├─ logo/                            # 打包图标与图片源（acbel-1.jpg 等）
├─ 使用须知/                        # 使用须知.md + 4 张示例截图
├─ .vscode/                         # launch.json（调试）/ tasks.json（uv run 任务）/ settings.json
├─ EMIRper.spec                     # 现役 PyInstaller 打包配置（入口 src/EMI-Report.py）
├─ deal_pdf.spec                    # 旧打包配置，入口 deal_pdf.py 已不存在
├─ pyproject.toml / uv.lock         # 依赖与锁定（uv）
├─ .python-version / pip.txt / .gitignore
├─ CHANGELOG.md                     # 更新日志（2.0 起）
└─ README.md                        # 本文档
```

## 3. 模块职责

### 3.1 [src/EMI-Report.py](src/EMI-Report.py) — 主程序

启动即调用 `setup_logging(log_dir=".", log_filename="EMIRper.log")`，再用 `get_error_logger()` 建立错误日志。

| 类 / 函数 | 职责 |
| --- | --- |
| `ProcessPdfThread(QThread)` | PDF 解析线程。信号 `progress_updated(int)` / `processing_finished(dict)` / `processing_error(str)`。`open_pdf` 取 PDF 前两页文本；`deal_datas` 解析字段与数据表；`deal_dirs` 遍历目录内 `*.pdf` 并逐个解析（单个失败只记日志、继续） |
| `ZipThread(QThread)` | 压缩线程。统计目录内所有 PDF，用 `zipfile.ZIP_LZMA` 打包成 `{zipname}.zip`，发进度信号 `progress_updated` / `zip_finished` / `zip_error` |
| `EMIWindow(MainWindow)` | 主窗口逻辑，继承 [src/gui/mainWin.py](src/gui/mainWin.py) 的 `MainWindow` |

`EMIWindow` 方法分组：

| 分组 | 方法 |
| --- | --- |
| 初始化 | `init_var`（行列锚点、设置项、窗口列表、日志路径、状态与序列号定时器）、`init_connect`（信号/槽绑定） |
| 路径选择 | `select_modelpath`、`select_templatepath`、`select_imgpath`（均带 try/except + `error_logger.log_error` + 中文错误框） |
| 序列号 | `bind_serial_tracking`（数据路径变化防抖）、`refresh_serial_numbers`（提取并显示，点击标签也会调用） |
| 界面状态 | `load_state` / `save_state` / `bind_state_tracking` / `install_exception_hook`（见第 11 节） |
| 窗口 | `closeEvent`、`show_docx2pdf`、`show_wordreplace`、`show_setting`、`show_log`、`show_about`、`show_helpdoc`、`show_done`（各窗口单例复用：`_focus_or_create` 负责创建或置前） |
| 日志视图 | `update_log`、`export_log`、`clear_log` |
| 模板 | `open_template`（按负载数量拼模板名、缺失时弹选择框、返回 workbook）、`get_testdetail`（读 `Conducted EMI!F8` 作为测试细节） |
| 主流程 | `main_func`（编排：`_write_header` / `_insert_test_image` / `_resize_report_rows` / `_write_measurements`，再保存并触发压缩）、`getpdfdatas`（起解析线程 + 状态栏进度条，`getpdf_running` 防重入）、`onProcessingFinished`、`onProcessingError`、`updateProgressBar` |
| 条件校验 | `_collect_template_conditions`（收集模板可用的电压 / 负载 / 相线组合）、`_validate_report_conditions`（逐份比对，返回问题列表） |
| 数据完整性 | `_collect_conditions`（枚举各 (电压, 负载, 相线) 条件对应的行）、`_row_state`（行填写状态）、`_check_measurement_gaps`（全序列号同缺则删行并提示，部分缺则告警）、`_diagnose_missing_report`（检查对应报告）、`_cleanup_orphan_merges`（清理残留合并区域） |
| 压缩与嵌入 | `zip_folder`、`updateZipProgressBar`、`onZipFinished`、`onZipError`、`add_zip_to_excel`、`open_excel`（Excel COM 失败时循环询问是否重试） |

### 3.2 [src/gui/mainWin.py](src/gui/mainWin.py) — 主界面

- `HoverLineEdit(QLineEdit)`：鼠标进入时在其右上角弹出无边框预览窗口，把文本当作图片路径 `QPixmap` 缩放显示；用于“测试图片”输入框。
- `MainWindow(QMainWindow)`：`setupUi` → `setMainWidget` + `setMainMenu`，全部界面用代码搭建（无 `.ui` 文件、无 `ui_*.py` 生成物）。
- 窗口标题跟随数据路径最后一级文件夹名（`EMI-Report - <文件夹名>`，路径为空时回到 `EMI-Report`），由 `EMIWindow.update_window_title` 在刷新序列号时一并更新。

界面控件：

| 控件 | 说明 |
| --- | --- |
| `lineEdit_template` + `btnfile_template` | 模版路径（可空，空则按负载数量自动选 `template/` 内模板） |
| `lineEdit_model` + `btnfile_model` | 数据路径（含 EMI PDF 的机种文件夹） |
| `text_serial` + `label_serial` | 序列号显示区（只读，位于「补充信息」上方）：取自数据路径下报告文件名「-」前第一段并去重；数据路径变化后自动刷新，点击标签立即刷新 |
| `spin_qty` | 负载数量（QSpinBox，默认 3） |
| `lineEdit_week` / `lineEdit_rev` / `lineEdit_workerno` | 周期（D/C）/ 版本 / 工令（作为默认值） |
| `check_diff_workno` | 「工令不同」勾选框（在工令输入框右侧，默认不勾选）：勾选后展开下方表格，取消则收起并全部使用默认值 |
| `table_serial` | 「按序列号填写工令 / 版本」表格（默认隐藏）：行标题为序列号（随数据路径自动刷新，可滚动），工令 / 版本留空则用上面的默认值 |
| `date_test` | 测试日期（QDateEdit，默认当天，弹出日历） |
| `lineEdit_img` + `btnfile_img` | 测试图片路径（`HoverLineEdit`，可悬停预览） |
| `text_detail` + `btn_getdetail` | 测试细节文本（点击“点击此处获取”从模板读出） |
| `btn_start` / `btn_clear` / `btn_exit` | 开始 / 清空（清空除「模版路径」「测试细节」以外的输入）/ 退出 |
| `statusBar_main` | 状态栏（进度条临时挂载于此） |

菜单：

| 菜单 | 动作（快捷键） |
| --- | --- |
| 选项 | 设置（Ctrl+I）、重启（Ctrl+R）、退出 |
| 工具 | 查看日志（Ctrl+J）、docx转pdf（Ctrl+T）、word替换（Ctrl+G） |
| 帮助 | 使用文档、关于 |

### 3.3 [src/gui/ui_docx2pdf.py](src/gui/ui_docx2pdf.py) — DOCX 转 PDF 子窗口

- `ConvertThread(QThread)`：用 `win32com` 打开 Word（隐藏窗口），把选中的 `.docx` 文件或目录内全部 `.docx` 另存为 PDF（`FileFormat=17`）；信号 `docx_count` / `docx_curr` / `docx_end` / `docx_error` / `docx_warning`；中断用 `requestInterruption()` + `isInterruptionRequested()`（不使用 `QThread.terminate()`）。
- `Ui_Docx2PdfWin`：界面构建（<s>Designer 生成物</s> 已改写为手写类）。
- `Docx2PdfWindow(Ui_Docx2PdfWin)`：路径选择（目录 / 单文件）、`running` 防重入、状态栏进度条、关闭时请求中断线程。
- 预览区（`label_preview` + `text_preview`）：显示所选路径下 docx 文件名中「-」之前的序列号（去重）与 docx 文件数量；路径变化后 300 ms 防抖自动刷新，点击标签立即刷新。

### 3.4 [src/gui/ui_wordreplace.py](src/gui/ui_wordreplace.py) — Word 替换子窗口

- `replace_text_in_docx(input, output, old, new)`：把 `.docx` 当作 zip 解压到临时目录，直接在 `word/document.xml` 文本层做字符串替换（支持单个字符串或成对列表），再重新打包为新的 `.docx`。它不经过 Word，因此只替换 XML 中的连续文本。
- `replace_value(content)`：正则取出 `>数字.数字<` 形式的浮点值，按每 8 个一组的第 1、4 个位置做小幅随机抖动（`random.randrange(-upper, upper)/2000`），使批量生成的文档数值看起来不完全一致；用于造测试数据。
- `WordReplaceThread(QThread)`：按“原字符串集 / 目标字符串集”（逗号或空白分隔、数量必须一致）对文件名做替换式重命名，同时把内容里的“原字符串 → 目标字符串”一并替换，输出到目标目录；信号 `file_count` / `file_progress` / `replace_finished` / `replace_error`。
- `WordReplace(QMainWindow)`：原路径（目录 / 文件）、目标路径、原/目标字符串集与字符串、开始 / 中止 / 关闭、状态栏进度条。
- `normalize_control_chars(text)`：把 `\r`、`\n`、`\t` 等格式控制符折叠为单个换行（连续多个也只产生一个换行），并去掉每行首尾空白与空行。
- 两个“标签即按钮”的交互：
  - 点击 **原字符串集** 标签（`fill_source_strings`）：读取源路径（文件夹则取其下全部 `.docx`，单文件则取该文件），把文件名去掉扩展名后按「-」取第一段填入，重复的只保留一次；
  - 点击 **目标字符串集** 标签（`clean_target_strings`）：就地整理输入框内容（见 `normalize_control_chars`）。

### 3.5 [src/logger.py](src/logger.py) — 日志基础设施

| 成员 | 职责 |
| --- | --- |
| `setup_logging(log_level, log_dir, log_filename)` | 配置 root logger：控制台 + 文件（`utf-8`）双 handler，格式 `时间 - logger名 - 级别 - 消息`；已存在 handler 时不重复添加 |
| `UserContextFilter` / `UserContextFormatter` | 预留：把当前用户注入日志格式（`[User: xxx]`），当前 `current_user` 恒为 `Unknown` |
| `ErrorLogger` / `get_error_logger()` | 独立错误日志 `error.log`：`====` 分隔块 + 时间 + context + 异常类型/详情 + 由传入异常对象生成的 traceback，同时向主日志写一条 ERROR |
| `safe_execute(context, show_error_dialog)` | 函数装饰器：进入/完成打点，异常写错误日志，可选弹错误框后重新抛出（当前主流程未使用） |
| `log_checkpoint(message, context)` | 调试检查点：写主日志并追加到 `error.log`（主窗口的路径选择处已埋点） |

### 3.6 共用工具

| 文件 | 内容 |
| --- | --- |
| [src/naming.py](src/naming.py) | `name_token(filename)` 取文件名（去扩展名）按「-」分隔的第一段；`collect_name_tokens(path, suffix)` 从文件夹（或单个文件）收集名称首段，按出现顺序去重。主界面的序列号区与 Word 替换的「原字符串集」都用它 |
| [src/gui/widgets.py](src/gui/widgets.py) | `ClickableLabel`：可点击标签（左键点击发 `clicked` 信号，光标为手型），用于「点击标签即触发动作」的交互 |

### 3.7 资源

- [src/gui/res.qrc](src/gui/res.qrc)（prefix `emipdf`）编译为 [src/gui/res_rc.py](src/gui/res_rc.py)，代码中以 `:/emipdf/acbel -1.jpg` 引用窗口图标。
- 注意：`res.qrc` 中列出的 jpg 并不在 `src/gui/` 目录下（真实图片在 `logo/` 与 `src/ui/`），重新编译 qrc 前需要先把图片放回 `src/gui/`。

### 3.8 遗留与开发脚本

| 文件 | 状态 |
| --- | --- |
| [src/ui/](src/ui) | 旧 Qt Designer 界面（`EMC.ui` / `ui_EMC.py` / `docx2pdf.ui` + 图片），已无任何模块 import；`ui_EMC.py` 内部却 `import gui.res_rc`，容易被误认为仍在使用 |
| [src/docx2pdf.py](src/docx2pdf.py) | 命令行版 docx→pdf（只扫一层目录），功能与 `gui/ui_docx2pdf.py` 重叠 |
| [src/test.py](src/test.py) | Word COM + python-docx 表格读写试验，含本机绝对路径 `D:/Desktop_Li/...` |
| [src/test_openpyxl.py](src/test_openpyxl.py) | 删除模板 `Setup` 前 4 行的试验 |
| [deal_pdf.spec](deal_pdf.spec) | 旧打包配置，入口 `deal_pdf.py` 已不存在 |

### 3.9 [src/batch.py](src/batch.py) — 无界面批处理入口

不做界面交互，批量把 EMI PDF 生成报告；实现方式是**复用 GUI 逻辑**而不是另写一套：

| 环节 | 做法 |
| --- | --- |
| 加载主程序 | 用 `importlib` 以模块名 `emi_report_main` 加载 `EMI-Report.py`（文件名含连字符，不能直接 `import`）；模块级 `setup_logging` 照常生效 |
| 无界面 | `QT_QPA_PLATFORM=offscreen` + 创建一个不 `show()` 的 `EMIWindow`，把作业参数写进对应输入框（`lineEdit_model` / `lineEdit_template` / `spin_qty` / `lineEdit_week` / `lineEdit_rev` / `lineEdit_workerno` / `text_detail` / `date_test` / `lineEdit_img` / `settings_value`） |
| 不弹窗 | 把主程序模块里的 `QMessageBox` 换成 `QuietMessageBox`（只记日志，`question` 一律返回 No），无人值守时不会被对话框卡住 |
| 解析 PDF | 直接调用 `ProcessPdfThread(...).deal_dirs(dir)`（纯方法，不启动 QThread、不需要事件循环） |
| 序列号过滤 | 作业给了 `serials` 时，只保留这些序列号的 PDF（数据目录里有别的序列号就复制到临时目录），并把机种块顺序按给定序列号排列 |
| 写出与归档 | 调 `main_func` 后取 `save_file_name`，按 `out_dir` / `out_name` 归档；目标已有同名文件时先改名为 `*.bak-<时间戳>.xlsx` 再覆盖 |
| 压缩与嵌入 | `zip` 时同步调 `ZipThread(...).zip_folder()`；`embed` 时调 `add_zip_to_excel(..., close_workbook=True, visible=False)`（需本机 Excel，嵌入后立即关闭本次打开的工作簿、不单独保留压缩包） |
| 补数据 | 数据目录里只有 docx 没有 PDF 时，用 `docx2pdf.convert_docx_files()` 单线程转换（只转作业关心的序列号；失败重试 3 次并重连 Word；不关掉用户已打开的 Word 文档） |
| 借用别的周期数据 | 作业给了 `replace_map` 时，先用 `gui.ui_wordreplace.replace_text_in_docx()` 把源目录 docx 改名/改写内容到临时目录（源目录只读），按目标序列号过滤后再转 PDF、出报告；替换表会自动补「序列号+尾字母」变体、按长串优先替换，输出文件名过滤 Windows 非法字符；`jitter=false`（`--no-jitter`）时关掉替换工具的数值抖动 |
| 测试图片 | 作业给了 `image` 就用它，否则按机种名在 `pic_dir`（默认 `D:\Desktop_Li\WorkDir\PIC\EMI`）里挑：机种名一致 > 同系列（前 6 位）系列图 > 同系列其它后缀，同级取文件名日期最新的；`--no-image` 可整体关闭 |
| 退出 | 输出落盘后 `os._exit(code)`：离屏 Qt 对象在解释器析构阶段会触发堆损坏（`0xC0000374`） |

## 4. 运行、调试与打包

- 直接运行（**cwd 需在仓库根**，否则 `template/` 相对路径与自动选模板会失效）：

  ```powershell
  uv run src/EMI-Report.py
  ```

- 批处理（无界面，同样建议在仓库根执行）：

  ```powershell
  .\.venv\Scripts\python.exe src\batch.py --job jobs.json          # 作业清单
  .\.venv\Scripts\python.exe src\batch.py --job jobs.json --dry-run  # 只检查数据与参数
  .\.venv\Scripts\python.exe src\batch.py --data <机种目录> --week 2613 --rev A04 `
      --workno AH00... --detail-file detail.txt --date 2026/04/20 `
      --serials SN1 SN2 SN3 --out <Report 目录> --zip --embed
  ```

- VS Code：任务 `uv run EMI-Report`（[.vscode/tasks.json](.vscode/tasks.json)，命令为 `uv run ${workspaceFolder}/src/EMI-Report.py`）；调试配置 [.vscode/launch.json](.vscode/launch.json) 只保留“调试当前文件”。
- 打包：

  ```powershell
  pyinstaller EMIRper.spec
  ```

  产物为 `dist/EMIRper/`（COLLECT 目录形式、`console=False`、启用 UPX、图标 `logo\acbel-1.jpg`）。
  注意 `datas=[]`，`template/` 不会被打进产物，发布时需把 `template` 目录放到 exe 的同级工作目录；找不到模板时程序会弹出模板选择框。
- 运行期依赖：`pyside6`、`openpyxl`、`pdfplumber`、`pillow`（图片缩放）、`pywin32`（Word / Excel COM），并要求本机安装 Microsoft Word 2010+（docx→pdf）与 Excel 2010+（嵌入压缩包）。
- `pyproject.toml` 中的 `qt-material` 目前没有实际使用（`apply_stylesheet` 已注释、`QtStyleTools` 已不再继承），`black` 仅作格式化工具。

## 5. 端到端流程

1. **准备数据**：同一机种的 EMI PDF 报告放在以机种命名的文件夹内，文件名遵循 `序列号-输入电压-负载-线性.pdf`（软件版本 ELEKTRA 4.52.1 导出）。
2. **选择路径**：`数据路径` 指向该机种文件夹，此时「序列号」区会自动列出该文件夹内报告文件名「-」之前的序列号（去重）；`模版路径` 可留空，留空时按 `负载数量` 自动使用 `template/2.1 Conducted EMI Measurement_{N}.xlsx`（现有 `_1` / `_3` / `_4` / `_10`），对应模板不存在时回落到 `_3` 并记 WARNING。写入时的行数换算以模板文件名中的数量为准，避免与模板行结构不符。
3. **补充信息**：`点击此处获取` 从模板 `Conducted EMI!F8` 读出测试细节填入文本框；另外填写测试日期、工令、版本、周期（D/C），可选测试图片。
4. **解析 PDF**（`ProcessPdfThread`）：逐份读取前两页文本 → 前 20 行中抓 `Serial` / `Power` / `Load` → 第 15 行之后取列数 > 10 的行作为数据行，并把每行第 1 列重编号为序号 → 分别按 AVG（第 8 列）与 PK（第 5 列）升序排序，取两者较小者所在的排序，用排序后的第 1 行作为该 PDF 的代表行。
5. **写入 Excel**（`main_func`）：先做**条件匹配校验**——逐份检查源数据的电压 / 负载 / 相线能否在模板中找到对应行（例如模板是 10%、20%…100% 十档，而报告是 25%、50%、100%），不匹配时列出具体文件与模板支持的条件并**中止本次写入**，避免表格错位甚至卡住；通过后读取 `Setup` 表锚点 → 写全局表头 `F5` 单体型号（目录名前两段）、`F6` 测试日期、`F8` 测试细节 → 补测试描述框右边框（`_apply_detail_borders`）→ 若图片存在，用 PIL 等比缩放到高 250 px 并转 JPEG，经 `openpyxl.drawing.image` 插入 `C27` → 按实际 UUT 数与负载数量反推需要删除的行数并 `delete_rows_keep_format`（合并区、公式、行高一起搬）→ 按 Serial / 电压 / 负载 / 线性逐级定位，写入 7 列数据（第 5 列固定写 `-`）→ 最后给**每个序列号块**写工令（F 列）、版本（H 列）、周期（I 列）：工令 / 版本可来自「按序列号填写」表格，留空则用界面默认值，从而覆盖模板里的链式公式。
6. **数据完整性检查**（`_check_measurement_gaps`）：写入完成后逐个检查 (电压, 负载, 相线) 条件在**所有序列号**中对应数据行的填写情况——
   - 某条件在所有序列号中都没有数据：视为未安排该测试的正常情况，删除这些空行并给出提示；
   - 只有部分序列号缺数据、或某行只写了一部分列：视为异常，检查数据目录里对应报告文件的情况（报告缺失 / 报告存在但未能取到数据）并给出警告。
7. **保存**：文件名为 `2.1 Conducted EMI Measurement_{型号}.xlsx`，保存前 `wb.remove(ws_setup)` 删除 `Setup` 表。
8. **压缩与嵌入**：`生成压缩包` 打开时用 ZIP_LZMA 把目录下所有 PDF 压成 `{型号}.zip`（带进度条）；`嵌入压缩包` 打开时用 Excel COM 打开刚保存的 xlsx，在 `Conducted EMI` 表插入该 zip 为 OLE 对象并补齐边框；`执行完毕关闭Excel` 决定是否随即退出 Excel。
9. **完成提示**：`show_done` 列出仍需人工完成的 4 步——填写日期与测试者（注意 MP / MVT）、核对限值标准（默认 Class B）、插入测试图片与压缩包、删除多余项。

> **目录变化提醒**：`main_func` 会 `os.chdir` 到“所选数据文件夹的父目录”。因此生成的 Excel 与 zip 都落在**所选数据文件夹的上一级目录**（同一机种文件夹之外），后续相对路径（日志、zip 名）都以该工作目录为基准。

## 6. Excel 模板契约（[template/](template)）

每份模板固定两张表：`Setup`（行列锚点参数）与 `Conducted EMI`（报告本体）。

`Setup!B1:B8` 参数（程序读取第 1、2、3、4、5、7、8 行）：

| Setup 行 | 含义 | `_3` / `_4` 模板 | `_Vdc` 模板 |
| --- | --- | --- | --- |
| B1 | SN 起始行 | 44 | 44 |
| B2 | SN 列 | 4 | 4 |
| B3 | 电压列 | 11 | 11 |
| B4 | 线性列 | 13 | 12 |
| B5 | 负载列 | 14 | 13 |
| B6 | 备用（未被读取） | 15 | 14 |
| B7 | 结束行 | 103 | 103 |
| B8 | 结束列 | 27 | 27 |

- 报告区每个 UUT 占 `负载数量 × 4` 行（3 负载 → 12 行），SN 行从 44 起；数据从 `负载列 + 1` 起连续写 7 列。
- 模板 `Conducted EMI` 表尺寸：`_3` 为 `A1:AA107`、`_4` 为 `A1:AA127`、`_Vdc` 为 `A1:AA107`，均含百余个合并单元格（程序按需取消合并与删行）。
- 保存前会删除 `Setup` 表，所以输出文件只有 `Conducted EMI`。
- 模板名里的数字后缀决定自动选择与行数换算：`_1` / `_3` / `_4` / `_10` 分别对应 1 / 3 / 4 / 10 档负载；模板文件名不含数字后缀时（如 `_Vdc`、`_AMZ`）不会被自动选中，需在界面手动指定，此时负载数量取界面值。
- 若手动指定了自定义模板且文件名不含 `_数字.xlsx`，输出文件名不会被替换成型号名（沿用模板文件名）。

## 7. 日志与配置

| 日志 | 位置与内容 |
| --- | --- |
| 主日志 | `EMIRper.log`（`setup_logging(log_dir=".")` → 当前工作目录）。格式 `时间 - logger名 - 级别 - 消息`，UTF-8 |
| 错误日志 | `error.log`（`ErrorLogger`）。`CRASH/ERROR DETECTED` 分隔块 + context + 异常类型/详情 + traceback；`log_checkpoint` 的检查点也追加在此 |
| 界面日志窗 | 菜单“工具 → 查看日志”，可更新 / 清空 / 导出当前日志文件内容 |

- `.gitignore` 中 `*.log` 与 `DealPdf.log` 已忽略日志文件；仓库里现存的 `DealPdf.log` 是旧版本残留（未跟踪）。
- 设置项（`NeedZip` / `AddZip` / `CloseExcel`）与界面输入一起持久化，默认值依次为 开 / 开 / 关，详见第 11 节。

**日志覆盖范围**（关键路径均有记录，便于事后定位问题）

| 环节 | 记录内容 |
| --- | --- |
| 启动 | Python / PySide6 版本、工作目录、日志文件路径；界面状态恢复路径与状态文件位置 |
| PDF 解析 | 目录与文件数、逐份文件开始解析、每份的页数与文本长度（DEBUG）、头部字段缺失时 WARNING、无数据行时报错并记录、目录解析汇总（成功 / 失败数） |
| 序列号 | 数据路径变化或点击标签刷新后，记录提取到的序列号数量与来源目录（无结果时记 DEBUG） |
| 模板 | 选中模板路径、模板缺失或打开失败的 WARNING / 异常 |
| 报告写入 | 生成参数（目录 / 模板 / 负载数量 / 报告份数 / 设置开关）、表头各字段实际值、未选图片或图片缺失或插入失败、行调整明细（机种数 / 删除范围 / 数据结束行）、逐份定位结果（DEBUG）、写入汇总、保存路径与总用时 |
| 条件校验 | 源数据的 (电压, 负载, 相线) 与模板不匹配时的具体文件与模板可用条件（ERROR，随后中止本次写入） |
| 数据完整性 | 全序列号同缺的条件（INFO，含删除行数与新的数据结束行）、部分序列号缺数据或数据不完整的条件及其报告诊断结果（WARNING） |
| 压缩与嵌入 | 压缩文件数、输出包名与压缩包大小、取消工作表保护、嵌入完成、按设置关闭 Excel |
| 子窗口 | 窗口初始化、选择的目录 / 文件、启动参数、逐份替换明细（DEBUG）、转换与替换汇总（成功 / 失败） |
| 界面状态 | 恢复与保存的路径、保存失败 WARNING |
| 异常 | 未捕获异常写入 `error.log`（含 traceback），随后立即落盘界面状态 |

- 级别约定：`INFO` 记录流程里程碑与结果，`WARNING` 记录可恢复的问题（字段缺失、图片不存在、目录内无 PDF 等），`DEBUG` 记录逐份明细（解析结果、行定位、状态落盘），`ERROR` / `exception` 记录失败并带 traceback。
- `error.log` 里记录的完整 CRASH/ERROR 块（含 traceback）同样会出现在主日志中（`error_logger` 会向 root logger 传播），另外主日志还会多出一行 `ERROR in <context>: <消息>` 摘要。

## 8. 待整理事项

1. `src/ui/` 整个目录已无引用，可清理；其中 `ui_EMC.py` 反向 `import gui.res_rc`，容易造成“仍在使用”的错觉。
2. `deal_pdf.spec` 引用的 `deal_pdf.py` 已不存在，配置无效。
3. `src/gui/res.qrc` 依赖的 jpg 不在同目录，重新编译资源前需补图。
4. `pyproject.toml` 的项目名仍为 `pdf-deal`（与项目名 `EMI-Report` 不一致）；2.0 已更新其 `version` 与 `description`。
5. `qt-material` 已无实际使用，可从依赖中移除。
6. `src/test.py` 与 `src/gui/ui_wordreplace.py` 的 `test()` 中写死了本机路径（`D:\Desktop_Li\...`）。
7. 日志路径与输出文件都基于当前工作目录，而主流程会 `os.chdir`，跨盘或只读目录场景需注意。
8. `使用须知/使用须知.md` 中描述的 `deal_pdf.exe` 现已更名为 `EMIRper`；面向使用者的完整说明已内置到程序「帮助 → 使用文档」。
9. 项目当前没有自动化测试。

## 9. 代码规范与工具链

风格约定统一写在 [pyproject.toml](pyproject.toml)：

| 项 | 约定 |
| --- | --- |
| 格式化 | `black`，行长 88，`target-version = py38`；排除 `.venv`、`build`、`dist`、`src/ui`、`src/gui/res_rc.py` |
| 静态检查 | `ruff`，规则集 `E4 E7 E9 F W I UP B C4 SIM RET G`；忽略 `E501`（行长交给 black）、`SIM108`、`RET504` |
| 类型注解 | 模块统一 `from __future__ import annotations`，注解可用 `list[str]`、`str \| None` 等新写法（运行环境仍是 Python 3.8） |
| 命名 | 模块 / 函数 / 变量 snake_case，类 PascalCase，常量 UPPER_CASE，Qt 槽函数同样 snake_case |
| 日志 | 统一 `logging`，消息用惰性格式 `logger.info("x=%s", x)`，异常用 `logger.exception(...)`；`print` 仅保留在 CLI 脚本与日志兜底分支 |
| 异常 | 禁止裸 `except:`；要么记录后继续，要么向上抛出 |
| 线程 | 子线程内不创建窗口（用信号回主线程）；中断用 `requestInterruption()` + `isInterruptionRequested()`，不用 `QThread.terminate()` |

常用命令（在仓库根执行）：

```powershell
.\.venv\Scripts\black.exe src        # 格式化
uv tool run ruff check src           # 静态检查
uv tool run ruff check --fix src     # 自动修复可修复项
```

> `src/ui/` 是废弃的旧界面目录，`src/gui/res_rc.py` 是 qrc 编译产物，两者已排除在格式化与检查之外。

## 10. 本次代码优化记录（2026-10-16）

**问题修复**

| 位置 | 问题 | 处理 |
| --- | --- | --- |
| `show_docx2pdf` | 同一个窗口被 `windows.append` 登记两次 | 抽出 `_focus_or_create()` 统一登记 |
| `select_*` / `export_log` | `getSaveFileName` / `getOpenFileName` 返回的是元组却按字符串使用，导出日志必然抛 `TypeError` | 正确解包并处理取消分支 |
| `open_template` | 界面模板路径为空时输出文件名算成空串，`wb.save("")` 失败 | 以实际使用的模板路径推导输出名，并回填到界面 |
| `open_pdf` | 硬取 `pdf.pages[1]`，只有一页的 PDF 直接崩溃 | 取前两页并容忍空文本 |
| `ConvertThread` | 在子线程中创建 `QMessageBox`；用 `terminate()` 强杀线程 | 改为信号回主线程提示；`requestInterruption()` + `wait()` |
| `replace_value` | 末尾数值组不完整时抛 `IndexError`，导致该文件替换整体失败 | 加边界检查，跳过不完整的组并记日志 |
| 多处 | 裸 `except:`（日志模块、Excel COM、命令行脚本） | 收窄为 `except Exception` 并附带异常信息 |

**风格与结构**

- 主程序新增常量区：PDF 解析下标、模板锚点、单元格地址、图片高度、机种与行数换算等魔法数字全部命名化。
- `main_func`（约 150 行）拆为 `_write_header` / `_insert_test_image` / `_resize_report_rows` / `_write_measurements`，主流程只做编排。
- 设置窗口由三组复制粘贴改为 `SETTING_ITEMS` 数据驱动；`show_*` 系列统一走 `_focus_or_create()`，约 7 处 `hasattr` 样板消失。
- `mainWin.setMainWidget`（约 150 行）拆为路径行 / 补充信息区 / 操作按钮三部分，并抽出小工具方法；删除无效的 `sys.path.append`。
- `ui_docx2pdf`、`ui_wordreplace` 的线程类与窗口类补齐类型注解、信号命名与错误路径；Word 替换窗口的 `setupUi` 同样拆分。
- 变量命名去缩写：`res` → `report_data`、`resdatas` → `rows`、`tmp` / `tmpp` → `parts`、`file_` → `filename` 等。
- 日志统一为惰性格式，`logger.error(..., exc_info=True)` 统一改写成 `logger.exception(...)`。

**验证方式**：`black --check src` 与 `ruff check src` 全绿；离屏（`QT_QPA_PLATFORM=offscreen`）实例化主窗口并打开全部 7 个子窗口无异常；用构造数据对拍 `deal_datas` 的 AVG / PK 选择结果与重构前一致；用合成 docx 走通 `replace_text_in_docx` 的替换链路。

## 11. 界面状态持久化（异常退出可恢复）

目标：程序异常退出（崩溃）后重新打开，不必重新填写输入框。

**保存内容**

| 保存内容 | 对应控件 |
| --- | --- |
| 模板路径 / 数据路径 | `lineEdit_template` / `lineEdit_model` |
| 负载数量 | `spin_qty` |
| 周期(D/C) / 版本 / 工令 | `lineEdit_week` / `lineEdit_rev` / `lineEdit_workerno` |
| 测试图片路径 | `lineEdit_img` |
| 测试细节 | `text_detail` |
| 测试日期 | `date_test`（按 ISO 日期存取） |
| 三个设置开关 | `NeedZip` / `AddZip` / `CloseExcel` |

**存放位置**：`%LOCALAPPDATA%\Acbel\EMI-Report\ui_state.json`（Qt 应用配置目录，路径由 `QApplication` 的 organizationName / applicationName 决定；取不到时退回 `%LOCALAPPDATA%\EMI-Report`）。文件为 UTF-8 JSON，可直接查看或删除——删除即恢复默认。

**崩溃不丢的四道保险**

1. **变化即保存**：所有输入控件的变化都触发一次 300 ms 防抖写盘（`bind_state_tracking` + `QTimer`），不依赖正常退出流程；
2. **原子写入**：先写 `ui_state.json.tmp`，再 `os.replace` 整体替换；即使写到一半崩溃也不会留下损坏文件，读到损坏内容时静默退回默认值；
3. **异常兜底**：安装 `sys.excepthook`（`install_exception_hook`），未捕获异常时先写入 `error.log`、立即再保存一次状态，然后交给默认处理；
4. **正常退出**：`closeEvent` 与设置窗口的「保存」按钮都会再落盘一次。

**验证**：模拟在 Qt 槽函数内抛 `RuntimeError` 崩溃，崩溃后状态文件中仍是刚输入的 `model_path` / `week`；重新实例化窗口可完整回填；故意写坏 JSON 后程序按默认值启动且不报错。

实现位置：[src/gui/app_state.py](src/gui/app_state.py)（状态存取与原子写）+ [src/EMI-Report.py](src/EMI-Report.py) 中的「界面状态持久化」方法区。

## 12. 日志补充记录（2026-10-16）

补齐了此前基本没有日志的关键路径：

- **启动**：Python / PySide6 版本、工作目录、日志文件路径；
- **PDF 解析**：目录与文件数、逐份页数与提取文本长度（DEBUG）、头部字段缺失告警、解析不到数据行时的明确报错、目录解析汇总（成功 / 失败）；
- **报告写入**：生成参数、表头各字段实际值、图片跳过或失败原因、行调整明细、逐份行定位结果（DEBUG）、保存路径与总用时；
- **压缩与嵌入**：压缩包大小、取消工作表保护、嵌入完成、按设置关闭 Excel、用户放弃启动 Excel；
- **子窗口**：窗口初始化、路径选择、启动参数、逐份替换明细（DEBUG）、转换与替换汇总；
- **界面状态**：恢复与保存路径、保存失败告警；
- **异常**：未捕获异常记录到 `error.log`。

顺带做的两件小事：

1. `_write_header` 的日志原先打印的是 openpyxl 的 `Cell` 对象（如 `<Cell 'Conducted EMI'.F6>`），已改为打印真实值；
2. 中英混杂的日志消息统一为中文，并修正 `logger.exception` 的误用（对用户输入校验一类的提示改用 `WARNING`）。此外 `ErrorLogger` 现在以传入的异常对象生成 traceback，异常钩子里也能记录到完整调用栈。

同时补了几处"哑失败"的提示与中止逻辑：

- 数据目录不存在、目录内没有 PDF、解析结果为空时，给出 `WARNING` 日志 + 提示框并中止，而不是抛异常或写出空报告；
- 测试图片读取/插入失败时记录异常并跳过图片，不再中断整份报告的生成。

## 13. 功能新增记录（2026-10-16）

| 位置 | 功能 |
| --- | --- |
| 主界面「序列号」区（`label_serial` + `text_serial`） | 位于「补充信息」上方，只读显示数据路径下报告文件名「-」之前的第一段（去重，每行一个）。数据路径变化后 500 ms 防抖自动刷新，点击标签立即刷新；目录不存在或没有 PDF 时显示为空。窗口默认高度因此由 450 调整为 520 |
| Word 替换窗口 · **原字符串集** 标签 | 点击后从源路径取名称：源是文件夹则遍历其下全部 `.docx`，源是单个文件则取该文件；文件名去掉扩展名后按「-」取第一段，重复的只保留一次，按文件名排序后逐行填入 |
| Word 替换窗口 · **目标字符串集** 标签 | 点击后就地整理输入框：`\r` / `\n` / `\t` 等格式控制符（连续多个也算一个）统一折叠为单个换行，并去掉每行首尾空白与空行 |

配套实现见 [src/naming.py](src/naming.py)（名称提取，主界面与 Word 替换共用）与 [src/gui/widgets.py](src/gui/widgets.py)（`ClickableLabel`）。

**验证方式**：用临时目录构造 `SN1-220V-100%-L.pdf`、`SN1-220V-50%-N.pdf`、`SN2-110V-100%-L.pdf` 与 `note.txt`，序列号区得到 `SN1`、`SN2`（去重、忽略非 PDF）；同样的 docx 目录下点击「原字符串集」得到 `SN1`、`SN3`，改为单文件时为 `SN3`；`A1\r\n\r\n\tB2\n\n\n\n   C3` 整理后为 `A1\nB2\nC3`，`X\t\tY` 整理后为 `X\nY`。

## 14. 批处理入口（2026-10-16，v2.3）

面向「一次补齐多份报告」的场景：把每份报告的参数写进作业清单，由 `src/batch.py` 逐条跑完。

### 14.1 作业文件

```json
{
  "jobs": [
    {
      "data_dir": "D:\\...\\WorkDir\\FSF059-00CG",
      "serials": ["FSF059A0400CGB2613002097", "FSF059A0400CGB2613002122", "FSF059A0400CGB2613002098"],
      "template": "……\\template\\2.1 Conducted EMI Measurement_3.xlsx",
      "load_qty": 3,
      "week": "2613",
      "rev": "A04",
      "workno": "AH00F59B0041P01134",
      "detail": "1. Test Condition:\n……\n\n2. Pass/Fail Criteria:\n……",
      "test_date": "2026/04/20",
      "image": "",
      "out_dir": "D:\\...\\<报告文件夹>\\Report",
      "out_name": "2.1 Conducted EMI Measurement.xlsx",
      "zip": false,
      "embed": false,
      "backup_existing": true
    }
  ]
}
```

| 字段 | 说明 |
| --- | --- |
| `data_dir` | 必填，存放该机种 EMI PDF（或 docx）的目录（GUI 里的「数据路径」） |
| `replace_map` | 可选，`{"源序列号": "目标序列号"}`：先用 Word 替换工具把源目录的 docx 改名/改写内容到临时目录，再转 PDF 出报告（源目录只读）。用于借用别的周期同名机种数据的场景 |
| `serials` | 可选但建议填：只使用这些序列号的 PDF；不填则该目录下的 PDF 全部使用（超过模板 5 个机种块会失败） |
| `template` | 可选，留空按 `load_qty` 取 `template/2.1 Conducted EMI Measurement_{N}.xlsx` |
| `load_qty` | 可选，负载档数（默认 3）；实际行数换算以模板文件名里的数字为准 |
| `week` / `rev` / `workno` | 周期（D/C）/ 版本 / 工令，按序列号块写入 F / H / I 列 |
| `detail` | 测试描述，写入 `Conducted EMI!F8`；也可用 `detail_file` 指向文本文件 |
| `test_date` | 测试日期 `YYYY/MM/DD`（默认今天），写入 `F6` |
| `image` | 可选，测试图片路径（等比缩放到高 250 px 后插入 `C27`）；留空则按 `pic_dir` 自动匹配 |
| `pic_dir` | 可选，测试图片目录（默认 `D:\Desktop_Li\WorkDir\PIC\EMI`）；`--no-image` 时整体不插图 |
| `jitter` | 可选，替换序列号时是否对测量数值做小幅随机抖动（默认 `true`）；`false` 时测量值保持与源文档一致 |
| `out_dir` / `out_name` | 报告归档目录与文件名；`out_name` 默认去掉模板名里的 `_<数量>` 后缀 |
| `zip` / `embed` / `close_excel` | 是否生成 PDF 压缩包 / 嵌入 Excel / 嵌入后关闭 Excel（默认均否）。`embed` 时批处理只关闭自己打开的工作簿，嵌入完成后不再单独保留压缩包 |
| `docx2pdf` | 数据目录里只有 docx、没有对应 PDF 时，是否先用本机 Word 转出 PDF（默认 `true`，单线程） |
| `backup_existing` | 目标已有同名报告时是否先备份（默认 `true`；改为 `false` 即直接替换） |

### 14.2 输出与退出码

每条作业打印一行 JSON：`{"index": 1, "ok": true, "model": "...", "reports": 36, "serials": [...], "out_file": "...", "backup_file": null, "zip_file": null, "seconds": 51.8}`；
失败时为 `{"ok": false, "error": "..."}`。全部成功退出码为 0，任一作业失败为 1（其余作业仍会继续跑）。

### 14.3 注意

- 批处理同样会 `os.chdir` 到数据目录的上一级（沿用 GUI 行为），因此**每条作业的路径都写绝对路径**最稳妥。
- 生成过程中 openpyxl 会丢弃模板里公式的缓存值（如 `M6` 的 `Pass`、`H6` 的日期、`F10` 的取样数），
  用 Excel 打开时会重新计算，属预期现象。
- 一次作业至少要解析 12 份 PDF（每序列号 2 电压 × 负载档数 × 2 相线），实测约 30~60 秒/份；
  需要 `docx2pdf` 时再加 1~2 分钟（36~48 份 Word 转换），`embed` 会在本机 Excel 里插入 OLE 对象。
- 报告里的序列号取自 **PDF 内容**的 `Serial` 字段（与 GUI 一致），不是文件名。若源文档里的
  序列号与报告概览的 Waterfall 不一致（例如多出一个字符），生成结果会照抄源文档，需要先用
  Word 替换工具修正源数据。

## 15. 测试图片与「删空条件」格式修复（2026-10-17，v2.8）

### 15.1 按机种名自动匹配测试图片

- 新模块 [src/picmatch.py](src/picmatch.py)：图片文件名第一段（下划线分隔）即机种名，
  例如 `FSL028-EL2G_20250313_101559.png`；只写前 6 位（`FSL028_...`）的视为**系列图**，
  前 6 位相同即同系列，可给该系列不同后缀的机种共用。
- 匹配优先级：机种名完全一致 → 系列图 → 同系列其它后缀；同级取文件名日期（`20XXXXXX`）最新的。
- GUI：选完「数据路径」后若「测试图片」还空着，自动按机种名挑一张填进去（日志记录匹配依据）。
- 批处理：`image` 留空时自动匹配（`pic_dir` 指定图片目录，`--no-image` 关闭）；
  机种名优先取作业的 `_model`，其次报告目录名里的「<机种> ORT Test Report」，最后数据目录名。

### 15.2 删空条件后格式错乱

`openpyxl` 的 `delete_rows` 只搬单元格：**合并区域不跟着平移、公式里的行号也不改**，
旧实现因此靠「先记录合并模式 → 删行 → 逐块 unmerge/merge 重建」来补救，但
`unmerge_cells` 会把合并区内非左上角的单元格**直接删掉**（连同它们的边框与填充），
重建时只能从上左单元格补回边线，于是出现：

- 机种块中间几行的边框、底色消失（看起来像「格式乱了」）；
- 合并区按旧坐标计算，落到别的机种块上，留下跨块的残留合并（行数也被撑大）；
- `W`/`X` 列的 `=T-Q` / `=U-R` 仍然引用删行之前的行号，边距值算到别的行。

现在改为统一走 `delete_rows_keep_format()`：一次算好「保留行 → 新行号」映射，
再同步搬运单元格（含样式）、改写公式引用（`openpyxl.formula.translate.Translator`）、
按保留的行重算合并区域、搬行高；合并区底边 / 顶边所在行被删掉时，把那条边框搬到新的边缘行，
避免每个机种块底部少一条线。`_collect_block_merges` / `_rebuild_block_merges` /
`_cleanup_orphan_merges` 随之删除。

### 15.3 测试描述区域（`B8:P8`）右边框

模板里 `P8` 的右边框本来就是 `medium`（粗线），但 openpyxl **读入时**会按合并区上左单元格
（`N8`，右边是 `thin`）重刷合并区边缘单元格的边框，另存后 `P8` 就变成细线了。
新增 `_apply_detail_borders()`：写表头后按「第 8 行里上边框为 `medium` 的列区间」找出区域，
把区域右侧单元格的右边框重新设为左侧那条粗线（取 `B8` 左边框的样式与颜色）。
验证方式：解压 `xl/worksheets/sheet2.xml` 看 `P8` 的 `borderId` 是否 `right="medium"`。

### 15.4 替换工具的数值抖动开关

`gui.ui_wordreplace.replace_text_in_docx()` 默认会对测量数值做小幅随机抖动（造差异化数据），
之前没有开关。新增 `jitter` 参数（默认 `True` 保持原行为）：纯文本替换场景传 `False`
即保持测量值与源文档一致；批处理用 `jitter: false` 或 `--no-jitter` 打开该模式。
