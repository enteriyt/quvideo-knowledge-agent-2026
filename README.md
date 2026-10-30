# 企业知识问答 Agent

第 3 题交付项目。输入问题和可选对话历史，输出制度原文、文档 ID、版本日期、冲突、资料缺口和任务状态。全部资料为合成数据。

## 评审入口

- 核心循环、模型适配与业务工具：[src/knowledge_agent/core.py](src/knowledge_agent/core.py)
- 需求与成功标准：[docs/01-requirements.md](docs/01-requirements.md)
- 技术设计：[docs/02-solution.md](docs/02-solution.md)
- 测试、验收对照与限制：[docs/03-evaluation.md](docs/03-evaluation.md)
- AI 使用记录：[docs/04-ai-usage.md](docs/04-ai-usage.md)
- 开发复盘：[docs/05-retrospective.md](docs/05-retrospective.md)
- 8 组实际离线运行结果：[examples/evaluation-summary.json](examples/evaluation-summary.json)
- 测试原始输出：[examples/test-results.txt](examples/test-results.txt)

当前证据：22 项测试通过，8 组离线场景通过，本地真实模型配置下的 8 组验收状态符合预期。其中 7 组实际调用 Qwen3-1.7B，空问题由输入校验直接处理。真实模型记录在 [examples/live/](examples/live/evaluation-summary.json)，离线记录保留 `offline_mock` 标识。源码仓库：[enteriyt/quvideo-knowledge-agent-2026](https://github.com/enteriyt/quvideo-knowledge-agent-2026)。

## 环境与离线运行

Python 3.10+，标准库实现，运行与测试无需安装第三方依赖。实际验证环境为 Python 3.12.14 / Windows。以下命令在项目根目录执行。

PowerShell：

```powershell
$env:PYTHONPATH = 'src'
python -X utf8 -m knowledge_agent --input examples/01-clear/input.json --mode mock --output local-result.json
python -X utf8 scripts/evaluate.py
python -X utf8 -m unittest discover -s tests -v
```

macOS / Linux：

```sh
PYTHONPATH=src python -m knowledge_agent --input examples/02-conflict/input.json --mode mock --output local-result.json
python scripts/evaluate.py
PYTHONPATH=src python -m unittest discover -s tests -v
```

`scripts/evaluate.py` 自动配置测试子进程的源码路径，并重建 8 组输入、输出、Trace 和测试报告。它不会调用模型服务。也可在虚拟环境执行 `python -m pip install -e .` 后省略 `PYTHONPATH`；该方式需要 setuptools 构建环境。

退出码：正常可解释业务状态（含 conflict、out_of_scope、needs_input）为 0；incomplete、配置或输入错误为 2；评估脚本任何用例或测试失败为 1。

## 真实模型运行

适配器面向支持 `POST /chat/completions`、`messages` 和 `response_format: json_object` 的 HTTPS 服务。由服务实际支持的模型名决定配置。密钥通过环境变量提供，`.env.example` 仅作说明，不自动加载。

PowerShell 中先在本地安全设置 `MODEL_API_KEY`，然后：

```powershell
$env:PYTHONPATH = 'src'
$env:MODEL_NAME = '填写服务支持的实际模型名'
$env:MODEL_BASE_URL = 'https://api.openai.com/v1'
python -X utf8 -m knowledge_agent --mode live --input examples/01-clear/input.json --output examples/live-clear.json
python -X utf8 -m knowledge_agent --mode live --input examples/02-conflict/input.json --output examples/live-conflict.json
python -X utf8 -m knowledge_agent --mode live --input examples/06-tool-recovery/input.json --output examples/live-recovery.json
```

以上外部服务命令需要用户自己的凭据，费用由服务决定。本次实际使用无需密钥的本地模型，完整复现见 [本地模型说明](docs/06-local-model.md)。外部请求默认超时 30 秒、本地 120 秒，默认最多 12 次决策。配置或服务错误明确失败，不会自动切换 Mock。

## 输入和输出

```json
{"question":"那期限呢？","history":[{"role":"user","content":"我想了解报销流程"}]}
```

可选 `failures: {"search": 1, "read": 1}` 用于合成工具故障注入。`--data` 更换资料文件，`--max-steps` 设置 1–100 次决策预算。

状态：`answered` 有原文依据；`conflict` 存在同主题同适用范围的不同规范值；`needs_input` 需补充信息；`out_of_scope` 缺知识库依据；`incomplete` 工具、模型失败或达到预算。每个引用包含原文 SHA-256，Trace 包含每步动作、参数、简要决策依据与完整工具返回，不保存模型内部思维过程。

## 交付状态

代码、规定的 5 份文档、本地模型复现说明、离线与真实运行证据及可执行测试齐备。提交 commit SHA 以该仓库上传完成后的 `git rev-parse HEAD` 为准。候选人个人贡献和实际投入如实记录于 AI 使用说明，尚未由本人补充的部分明确标注。
