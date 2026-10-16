# EMI-Report（EMI_deal）

EMI 传导骚扰（Conducted EMI）测试报告自动化工具：把 ELEKTRA 导出的 EMI PDF 报告解析成数据，按模板写入 Excel，并生成 / 嵌入原始 PDF 压缩包，产出一份可直接继续整理的报告底稿。界面基于 PySide6（QMainWindow + QThread）。

- 主入口：[src/EMI-Report.py](src/EMI-Report.py)，窗口标题 `EMI-Report`
- 版本：`2.0`（显示在「帮助 → 关于」窗口），变更历史见 [CHANGELOG.md](CHANGELOG.md)
- 作者：`Lucas Li`（Lucas_Li@acbel.com）
- 面向使用者的说明：[使用须知/使用须知.md](使用须知/使用须知.md)
- 远程仓库：https://github.com/yooxii/EMI_deal.git

---

## 1. 仓库与同步状态

| 项 | 值 |
| --- | --- |
| 远程 | `https://github.com/yooxii/EMI_deal.git`（origin） |
| 当前分支 | `master` |
| 当前提交 | `2.0` 版本提交（此前基线为 `c1dc25e`，2026-01-06） |
| 与远程关系 | `2.0` 版本提交后与 `origin/master` 同步 |
| 提交总数 | 13（含 `2.0` 版本提交） |
| 工作区 | `2.0` 的改动已提交；`DealPdf.log` 被 `.gitignore` 忽略 |
| 工作树 | 单一工作树 `E:/Desktop/Code/ORT/EMI_deal`，无 stash、无 tag |
| 版本要求 | `.python-version` → `3.8`；`pyproject.toml` → `requires-python = ">=3.8"`；依赖由 `uv` 管理，索引为清华源 |

本次核对时，本地 `master` 曾落后 `origin/master` 6 个提交（`4b121a4` → `c1dc25e`，远程把 `src/ui` 重构成了 `src/gui` 并新增日志系统）。当时的本地未提交改动（`src/EMI-Report.py`、`src/docx2pdf.py`、`.vscode/launch.json`、`uv.lock`、未跟踪的 `.vscode/tasks.json` 与 `src/ui/ui_setting.py`）已备份到 `E:\Desktop\Code\ORT\_EMI_deal_backup_20261016_092429`，随后丢弃并快进合并到 `c1dc25e`。

## 2. 目录结构

```
EMI_deal/
├─ src/
│  ├─ EMI-Report.py                 # 主入口：EMIWindow 主窗口 + 2 个工作线程
│  ├─ logger.py                     # 日志基础设施：主日志 / 错误日志 / 装饰器
│  ├─ naming.py                     # 从报告文件名提取名称片段（序列号等）
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
├─ template/                        # Excel 报告模板（3 份，含 Setup 参数表）
│  ├─ 2.1 Conducted EMI Measurement_3.xlsx
│  ├─ 2.1 Conducted EMI Measurement_4.xlsx
│  └─ 2.1 Conducted EMI Measurement_Vdc.xlsx
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
| 压缩与嵌入 | `zip_folder`、`updateZipProgressBar`、`onZipFinished`、`onZipError`、`add_zip_to_excel`、`open_excel`（Excel COM 失败时循环询问是否重试） |

### 3.2 [src/gui/mainWin.py](src/gui/mainWin.py) — 主界面

- `HoverLineEdit(QLineEdit)`：鼠标进入时在其右上角弹出无边框预览窗口，把文本当作图片路径 `QPixmap` 缩放显示；用于“测试图片”输入框。
- `MainWindow(QMainWindow)`：`setupUi` → `setMainWidget` + `setMainMenu`，全部界面用代码搭建（无 `.ui` 文件、无 `ui_*.py` 生成物）。

界面控件：

| 控件 | 说明 |
| --- | --- |
| `lineEdit_template` + `btnfile_template` | 模版路径（可空，空则按负载数量自动选 `template/` 内模板） |
| `lineEdit_model` + `btnfile_model` | 数据路径（含 EMI PDF 的机种文件夹） |
| `text_serial` + `label_serial` | 序列号显示区（只读，位于「补充信息」上方）：取自数据路径下报告文件名「-」前第一段并去重；数据路径变化后自动刷新，点击标签立即刷新 |
| `spin_qty` | 负载数量（QSpinBox，默认 3） |
| `lineEdit_week` / `lineEdit_rev` / `lineEdit_workerno` | 周期（D/C）/ 版本 / 工令 |
| `date_test` | 测试日期（QDateEdit，默认当天，弹出日历） |
| `lineEdit_img` + `btnfile_img` | 测试图片路径（`HoverLineEdit`，可悬停预览） |
| `text_detail` + `btn_getdetail` | 测试细节文本（点击“点击此处获取”从模板读出） |
| `btn_start` / `btn_exit` | 开始 / 退出 |
| `statusBar_main` | 状态栏（进度条临时挂载于此） |

菜单：

| 菜单 | 动作（快捷键） |
| --- | --- |
| 选项 | 设置（Ctrl+I）、退出 |
| 工具 | 查看日志（Ctrl+J）、docx转pdf（Ctrl+T）、word替换（Ctrl+G） |
| 帮助 | 使用文档、关于 |

### 3.3 [src/gui/ui_docx2pdf.py](src/gui/ui_docx2pdf.py) — DOCX 转 PDF 子窗口

- `ConvertThread(QThread)`：用 `win32com` 打开 Word（隐藏窗口），把选中的 `.docx` 文件或目录内全部 `.docx` 另存为 PDF（`FileFormat=17`）；信号 `docx_count` / `docx_curr` / `docx_end` / `docx_error` / `docx_warning`；中断用 `requestInterruption()` + `isInterruptionRequested()`（不使用 `QThread.terminate()`）。
- `Ui_Docx2PdfWin`：界面构建（<s>Designer 生成物</s> 已改写为手写类）。
- `Docx2PdfWindow(Ui_Docx2PdfWin)`：路径选择（目录 / 单文件）、`running` 防重入、状态栏进度条、关闭时请求中断线程。

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

## 4. 运行、调试与打包

- 直接运行（**cwd 需在仓库根**，否则 `template/` 相对路径与自动选模板会失效）：

  ```powershell
  uv run src/EMI-Report.py
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
2. **选择路径**：`数据路径` 指向该机种文件夹，此时「序列号」区会自动列出该文件夹内报告文件名「-」之前的序列号（去重）；`模版路径` 可留空，留空时按 `负载数量` 自动使用 `template/2.1 Conducted EMI Measurement_{3|4}.xlsx`，数量不是 3/4 时回落 `_3`。
3. **补充信息**：`点击此处获取` 从模板 `Conducted EMI!F8` 读出测试细节填入文本框；另外填写测试日期、工令、版本、周期（D/C），可选测试图片。
4. **解析 PDF**（`ProcessPdfThread`）：逐份读取前两页文本 → 前 20 行中抓 `Serial` / `Power` / `Load` → 第 15 行之后取列数 > 10 的行作为数据行，并把每行第 1 列重编号为序号 → 分别按 AVG（第 8 列）与 PK（第 5 列）升序排序，取两者较小者所在的排序，用排序后的第 1 行作为该 PDF 的代表行。
5. **写入 Excel**（`main_func`）：读取 `Setup` 表锚点 → 写表头 `F5` 单体型号（目录名前两段）、`F6` 测试日期、`F8` 测试细节、`F44` 工令、`H44` 版本、`I44` 周期 → 若图片存在，用 PIL 等比缩放到高 250 px 并转 JPEG，经 `openpyxl.drawing.image` 插入 `C27` → 按实际 UUT 数与负载数量反推需要删除的行数并 `delete_rows` → 按 Serial / 电压 / 负载 / 线性逐级定位，写入 7 列数据（第 5 列固定写 `-`）。
6. **保存**：文件名为 `2.1 Conducted EMI Measurement_{型号}.xlsx`，保存前 `wb.remove(ws_setup)` 删除 `Setup` 表。
7. **压缩与嵌入**：`生成压缩包` 打开时用 ZIP_LZMA 把目录下所有 PDF 压成 `{型号}.zip`（带进度条）；`嵌入压缩包` 打开时用 Excel COM 打开刚保存的 xlsx，在 `Conducted EMI` 表插入该 zip 为 OLE 对象并补齐边框；`执行完毕关闭Excel` 决定是否随即退出 Excel。
8. **完成提示**：`show_done` 列出仍需人工完成的 4 步——填写日期与测试者（注意 MP / MVT）、核对限值标准（默认 Class B）、插入测试图片与压缩包、删除多余项。

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
- `_Vdc` 模板文件名不以 `_3` / `_4` 结尾，不会被自动选中，需在界面手动指定。
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
8. 帮助菜单“使用文档”仍是“待补充”；`使用须知/使用须知.md` 中描述的 `deal_pdf.exe` 现已更名为 `EMIRper`。
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
