# DeepSeek Harness 桌面版（Linux + Windows）

DeepSeek Harness 的原生桌面 GUI：把 harness 的 `dsh web` 界面装进原生窗口，`dsh web` 作为受监管的 sidecar 进程运行。内置 **dsh 插件中心（Plugin Hub）**，自动复用本地已有的 harness 配置（免二次配置），在 Linux 和 Windows 上都打包为双击即开的应用。

GitHub 仓库：<https://github.com/hux-hx/DeepSeek-Harness-GUI>

## 为什么做这个

2026 年 8 月的联网调研结论：DeepSeek Harness 官方没有 Linux 桌面版：

| 渠道 | 现状 |
| --- | --- |
| 官方（`github.com/deepseek-ai/deepseek-harness`） | 通过 `dsh web`（`http://127.0.0.1:3080`）提供本地 Web UI；任何平台都没有签名桌面安装包 |
| 社区 macOS 版（[fendouai/deepseek-harness-desktop](https://github.com/fendouai/deepseek-harness-desktop) v0.1.0-rc.5） | 仅有 Apple Silicon DMG：捆绑 Node.js 运行时 + 受监管的 `dsh` sidecar + 现有 Web UI |
| 社区 Windows 版（Microsoft Store "DeepSeek-Harness-Setup"） | 打包 Web UI 的 Windows 安装器 |
| Linux | 无人发布 —— 本应用补上空缺，并额外适配了 Windows |

本应用采用与社区 macOS/Windows 版相同的架构（受监管 sidecar + 现有 Web UI），但零捆绑运行时：直接驱动本机已有的 dsh，只补齐桌面外壳（图标、菜单项、原生窗口、sidecar 生命周期、插件中心）。

## 功能

- **受监管 sidecar** —— 以独立 `DSH_HOME` + 操作系统随机端口启动 `dsh web`；关闭窗口（或 SIGTERM/SIGINT）会终止整个进程树（SIGTERM → 5 秒宽限 → SIGKILL）。
- **免二次配置** —— 首次运行时把本地已有 harness home 的 `settings.yaml`、`.credentials.yaml`、`.anonymous-user-id` 以及整个 `profiles/web/` 目录（含已安装的插件包和 node_modules）一并复制进应用自己的 home（保留权限位）。供应商、模型、API key、插件依赖全部带走，无需重新下载或登记；会话数据不受影响。`--fresh` 可跳过导入。
- **内置插件中心** —— 管理_web profile 的 dsh 插件：扫描 harness 检出里的 `@deepseek-ai` 包作为目录；展示已安装/已登记状态；通过 `dsh plugin --profile web add` 把 npm 包装进 profile；在 `cordis.patch.yml` 登记/取消登记（保留头部注释与非 insert 条目）；实时显示命令输出。可从窗口工具栏的 "Plugin Hub" 按钮或 `--plugins` 打开。
- **原生窗口外壳** —— `Ctrl+R` 刷新、`Ctrl+Shift+R` 绕过缓存、`Ctrl+=`/`Ctrl+-`/`Ctrl+0` 缩放、`F11` 全屏、`Ctrl+Q` 退出；记住窗口尺寸与缩放；离开应用源的链接在系统浏览器打开（Linux）。

## 目录结构

```
desktop-linux/                      （本应用）
├── bin/deepseek-harness-desktop    入口：CLI + Linux 的 GTK 窗口 / Windows 的 pywebview
├── bin/dshdesktop_core.py          路径、dsh 解析、sidecar、配置导入
├── bin/dshdesktop_hub.py           插件中心逻辑 + GTK/Tk 界面
├── share/applications/*.desktop.in MATE/GNOME 菜单项模板
├── share/icons/…                   SVG、PNG（48/128/256）、Windows .ico
├── windows/                        双击 .cmd 启动器 + install-windows.ps1
├── install.sh / uninstall.sh       Linux 按用户安装（~/.local）
└── README.md / README.zh.md / LICENSE
```

## 安装（Linux）

```sh
cd DeepSeek-Harness-GUI
./install.sh          # 按用户安装，前缀 ~/.local
```

安装内容：`~/.local/bin/deepseek-harness-desktop`、图标、MATE/GNOME 菜单项（Development 分类）、可双击打开的 `~/Desktop/DeepSeek-Harness-Desktop.desktop`。依赖：Python 3、GTK 3、WebKit2GTK 4.1（`gir1.2-webkit2-4.1`）、可用的 `dsh`（`npm i -g @deepseek-ai/dsh`）。

## 安装（Windows）

1. 安装 Python 3（python.org，勾选 "Add to PATH" 与 tcl/tk），然后 `py -3 -m pip install pywebview`（使用 Windows 10/11 内置的 WebView2 运行时）。
2. 安装 harness：`npm i -g @deepseek-ai/dsh`。
3. 双击 `windows/install-windows.ps1`（或 `powershell -ExecutionPolicy Bypass -File install-windows.ps1`）——检查依赖并创建开始菜单与桌面快捷方式（应用 + 插件中心）。
4. 双击 **DeepSeek Harness Desktop** 即可打开。

## 使用

```sh
deepseek-harness-desktop                         # 启动 sidecar 并打开窗口
deepseek-harness-desktop --attach http://127.0.0.1:3080   # 直接包装已在运行的 dsh web
deepseek-harness-desktop --plugins               # 打开插件中心
deepseek-harness-desktop --port 4200             # 固定 sidecar 端口
deepseek-harness-desktop --home ~/.dsh           # 共用主 DSH home（见下方说明）
deepseek-harness-desktop --dsh /path/to/dsh      # 显式指定 dsh 可执行文件
deepseek-harness-desktop --repo /path/to/deepseek-harness   # 源码模式 + 插件目录来源
deepseek-harness-desktop --fresh                 # 跳过本地配置导入
deepseek-harness-desktop --geometry 1440x900     # 初始窗口尺寸
deepseek-harness-desktop --check                 # 无头自检：启动/就绪/关闭
```

首次启动会自动导入本地 harness 配置，因此界面打开时供应商、模型、API key 都已就绪；若本机没有 harness，则会进入 Web UI 自带的引导，按提示填一次即可。

> 注意：在另一个 `dsh web` 运行期间共用 `--home ~/.dsh` 会让两个进程写同一个 profile；请优先使用默认隔离 home，或用 `--attach` 包装正在运行的实例。

## dsh 解析顺序

`--dsh`/`DSH_BIN` → 应用相邻（或 `--repo`/`DSH_REPO` 指定）且已装 `node_modules` 的 harness 检出（通过 tsx 运行 `apps/cli/src/bin.ts`，即直接使用项目源码）→ `PATH` 上的 `dsh` → Linux 的 nvm（`~/.nvm/versions/node/*/bin/dsh`）或 Windows 的 npm 全局 shim（`%APPDATA%\npm\dsh.cmd`）。

## 数据目录

```
Linux:  ~/.local/share/deepseek-harness-desktop/
Windows: %APPDATA%\DeepSeekHarnessDesktop\
├── home/                  # sidecar 的 DSH_HOME（profiles、storages、logs/、导入的配置）
├── hub-packages.json      # 插件中心记录
└── window-state.json      # 上次窗口尺寸/最大化/缩放（Linux）
```

sidecar 日志：`home/logs/sidecar-<时间戳>.log`（保留最近 10 份）。窗口报告启动失败时，先看最新一份日志。

## 故障排查

- **"dsh executable not found"** —— 设置 `DSH_BIN`/`--dsh`。从菜单启动时 `PATH` 常缺少 nvm 目录；启动器也会自动检查 nvm/npm shim 位置。
- **首次启动偏慢** —— web profile 首次运行会把插件依赖装进全新 `DSH_HOME`；之后的启动只需几秒。
- **老 GPU 渲染异常** —— Linux 用 `WEBKIT_DISABLE_COMPOSITING_MODE=1` 强制软件渲染。
- **插件装了但不显示** —— 插件中心已把它登记进 `cordis.patch.yml`；随后重新加载 Web UI 即可。

## 安全说明

窗口显示的就是官方 `dsh web` 在回环地址上提供的内容，不涉及任何捆绑或改动过的 harness 二进制。sidecar 与任何本地 `dsh` 运行一样拥有文件系统、shell、模型密钥等权限，请像使用 `dsh web` 一样保持审批开启并妥善保管 API key。凭据文件按原 `0600` 权限复制。

## 许可

MIT —— 见 [LICENSE](LICENSE)。
