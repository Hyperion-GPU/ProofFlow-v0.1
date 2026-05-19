# `docs/assets/` — milestone v0.1.x dogfood-and-channel-polish

> Generated for milestone v0.1.x dogfood-and-channel-polish; not a release artifact.

本目录承载本里程碑 (`v0.1.x dogfood-and-channel-polish`) 范围内的 **Demo_Asset** 与 **VSCode_Channel** 截图 / 录屏，作为 Dogfood_Report (`docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`) 的 evidence-backed 引用源。

本目录中既有的早期资产（如 `proofflow-demo-thumbnail.png`、`proofflow-pr94-agentguard-comment.svg`）属于历史里程碑，**不**属于本里程碑 evidence；本里程碑新增资产请按下文命名约定落地，不要覆盖既有文件。

## 用途 / Purpose

- 对外展示一次真实 AI coding agent 操作被 ProofFlow 端到端审计的过程（GIF 或短视频）。
- 留存 VS Code 扩展 inline audit、Approve Gate、hash-guarded undo 三段式的截图证据，供 Dogfood_Report 三渠道证据 / Channel Evidence 章节中 `VSCode_Channel` 块按 evidence type `screenshot` / `recording` 引用。
- 任何被 README / quickstart 首屏 demo 区引用的 GIF 必须落在本目录，**不**允许上传到外部对象存储或第三方视频站（参见 design Non-Goals 第 6 条）。

## 命名约定 / Asset Naming Convention

与 `design.md` §Architecture / §Demo Asset Generation Design 对齐，本里程碑使用以下命名（仓库相对路径，全部小写，分隔符 `-`，版本段使用 `v0_1_x` 而非 `v0.1.x` 以避免点号被工具误解析为扩展名分隔）：

| 用途 | 推荐文件名 |
| --- | --- |
| 端到端 dogfood demo（README 首屏 GIF） | `docs/assets/proofflow-v0_1_x-dogfood-<channel>.gif` |
| VS Code inline audit 截图 | `docs/assets/proofflow-v0_1_x-vscode-inline-audit.png` |
| VS Code Approve Gate 截图 | `docs/assets/proofflow-v0_1_x-vscode-approve-gate.png` |
| VS Code 完整流程 GIF（可选） | `docs/assets/proofflow-v0_1_x-vscode-flow.gif` |

`<channel>` 取值 `mcp` / `vscode` / `gha` 之一，与三渠道证据块中的 `Tool / Workflow / View` 字段保持一致。

`README.md` / `README.zh-CN.md` / `docs/ledger_quickstart_mcp.md` 中至少一份需要显式引用 GIF（Requirement 5.2）；引用形态使用仓库相对路径，例如：

```markdown
![ProofFlow v0.1.x dogfood demo](docs/assets/proofflow-v0_1_x-dogfood-mcp.gif)
```

## 体积与时长约束

- GIF ≤ 8 MB，时长 ≤ 60 秒，分辨率 ≤ 1280×720（保证 GitHub README 加载体验，与 design §Demo Asset Generation Design 一致）。
- 如需要保留更长版本，可附加 `.mp4`，但 README / quickstart 引用必须指向 GIF。

## 隐私脱敏要求 / Privacy and Redaction

录制 / 截图前与提交前必须满足下列硬约束：

1. **不允许内嵌本地绝对路径或用户名**——终端窗口标题、PowerShell prompt、VS Code 标题栏、侧边栏、`.mcp.json` / `.codex/config.toml` 任何位置都不得出现 `C:\Users\<name>\…`、`D:\Users\<name>\…` 这类含真实用户名的本地绝对路径。
2. 如必须引用临时路径，统一使用 `<TMP>` 占位符，例如 `<TMP>\proofflow-dogfood-<ts>\data`。
3. 关闭 Windows 通知、邮件 / IM 客户端预览，避免录入私人信息。
4. `.mcp.json` / `.codex/config.toml` 中如出现 token / API key，先用占位符（如 `<MCP_TOKEN>`）替换或在 demo 用临时配置覆盖。
5. 侧边栏不暴露其它私有仓库或未提交文件名。
6. 如不慎录入敏感内容必须 **reshoot 而非后期模糊**（与 design §Risk and Fallback Paths 一致）。

## Windows 路径与 PowerShell 约定

- Windows 路径若含空格（例如 `D:\ProofFlow v0.1\docs\assets`），在任何命令中必须用双引号包裹，例如：

  ```powershell
  Push-Location "D:\ProofFlow v0.1\docs\assets"
  Get-ChildItem
  Pop-Location
  ```

- 不依赖隐式 `cd`；切换工作目录统一用 `Push-Location` / `Pop-Location` 配对。
- 录屏中所示 backend 端口固定为 `8787`（与 README quickstart、`docs/V0_1_DOGFOOD.md` 一致），不允许出现 `:8000` / `:5000` / `--port 8000` 等其它端口示例。

## 引用回写

任何新增资产落地后，必须同步在 Dogfood_Report (`docs/releases/V0_1_X_DOGFOOD_AND_CHANNEL_POLISH.md`) 的 `Demo 资产与示例 Proof Packet / Demo and Example Packet` 章节字段 `demo_asset_path` / `demo_asset_referenced_from` 中登记，并在三渠道证据 / Channel Evidence 的 `VSCode_Channel` 或 `MCP_Channel` 块的 `Evidence` 列表中以 `screenshot` / `recording` 类型记录仓库相对路径。
