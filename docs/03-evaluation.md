# 测试、实际结果与限制

## 可复现结果

执行命令 `python -X utf8 scripts/evaluate.py`。运行环境 Python 3.12.14 / Windows。当前离线 8/8 场景符合预期，22/22 测试通过。报告是脚本实际执行生成，原始测试输出在 [test-results.txt](../examples/test-results.txt)，汇总在 [evaluation-summary.json](../examples/evaluation-summary.json)。

| 验收点 | 运行目录 | 预期 / 实际 | 决策数 |
|---|---|---|---|
| 明确答案 | [01-clear](../examples/01-clear/output.json) | answered / answered | 3 |
| 文档冲突 | [02-conflict](../examples/02-conflict/output.json) | conflict / conflict | 4 |
| 资料外问题、补充检索 | [03-outside](../examples/03-outside/output.json) | out_of_scope / out_of_scope | 3 |
| 改写相似问题 | [04-paraphrase](../examples/04-paraphrase/output.json) | conflict / conflict | 4 |
| 上下文追问 | [05-follow-up](../examples/05-follow-up/output.json) | conflict / conflict | 4 |
| 工具暂时失败 | [06-tool-recovery](../examples/06-tool-recovery/output.json) | answered / answered | 4 |
| 工具持续失败、预算 | [07-tool-unavailable](../examples/07-tool-unavailable/output.json) | incomplete / incomplete | 12 |
| 信息不足 | [08-missing-question](../examples/08-missing-question/output.json) | needs_input / needs_input | 0（输入校验） |

每个目录均包含 input.json、output.json、trace.json。Trace 记录动作及参数、简要公开决策依据、工具返回与后续动作；不提交模型内部思维过程。正常路径与冲突路径、工具失败路径的行为差异可以直接逐步比较。

## 额外测试

`tests/test_agent.py` 还检验原文引用完全一致、替换原文后答案变化、移除冲突文档后状态变化、历史中错误答案不作为证据、未读取不能回答、不能漏读冲突来源、观察到冲突不能强行回答、读取前必须检索、非法动作与额外答案字段被拒、运行之间隔离状态、工具异常不泄露原始错误、缺失模型配置不会自动回退 Mock。

HTTP 适配器单元测试用模拟响应核对请求结构和 JSON 解析，真实模型效果另由下面的本地实测证明。

## 真实本地模型结果

Qwen3-1.7B Q8_0、llama.cpp b11979、AMD Ryzen 7 7700、约 32GB 内存。命令为 `python -X utf8 scripts/evaluate_live.py`，模型配置与来源见 [06-local-model.md](06-local-model.md)。当前 [live 汇总](../examples/live/evaluation-summary.json) 的 8/8 状态符合预期；前 7 组实际调用模型，空问题为输入校验，无模型调用。

| 用例 | 实际状态 | 决策数 | 耗时（秒） |
|---|---|---|---|
| [明确答案](../examples/live/01-clear/output.json) | answered | 3 | 8.5448 |
| [文档冲突](../examples/live/02-conflict/output.json) | conflict | 4 | 11.2489 |
| [资料外](../examples/live/03-outside/output.json) | out_of_scope | 3 | 5.4757 |
| [改写问题](../examples/live/04-paraphrase/output.json) | conflict | 4 | 13.2701 |
| [上下文追问](../examples/live/05-follow-up/output.json) | conflict | 4 | 12.5255 |
| [读取失败后恢复](../examples/live/06-tool-recovery/output.json) | answered | 5 | 13.2076 |
| [工具持续失败](../examples/live/07-tool-unavailable/output.json) | incomplete | 5 | 9.9767 |
| [空问题](../examples/live/08-missing-question/output.json) | needs_input | 0 | 0.0001 |

动态变化的直接证据：明确问题读取 P01 后结束；冲突问题继续读取 D01、D02 后请求确认；读取失败后模型重新检索，再读成功并结束；持续失败时模型在第 5 步主动停止。离线持续失败用例则验证 12 步硬上限。

## 开发中实际失败与修复

第一次运行暴露 Windows 子进程输出编码不一致，导致测试报告无法按 UTF-8 读取。测试子进程现使用 `-X utf8`，报告统一 UTF-8。

首轮业务测试中，资料外问题在第二次检索追加“制度 FAQ”后误命中了报销制度，实际返回 conflict，未达到预期。修复将这些通用词从关键词回退中排除，并在结束校验中要求存在与原问题相关的资料。重跑后该场景返回 out_of_scope。

第一轮真实模型仅使用 JSON object 模式，返回缺少 reason 的动作，程序拒绝执行，见 [格式失败记录](../examples/live-initial-format-failure.json)。改用动作 JSON Schema 后，首次全量验收达到 6/8，记录在 [live-initial](../examples/live-initial/evaluation-summary.json)：资料外问题猜测文档 ID，被程序拦截；空问题被模型错误推测成其他问题。补充明确的 ID 和状态说明后，资料外问题修正成功。空问题仍被错误分类，见 [第二轮空问题失败](../examples/live-second-missing-failure.json)，最终移至确定性输入校验处理，再单独重跑该场景并汇总。

## 验证边界与未完成项

当前真实模型验证覆盖小型合成库和固定验收输入，尚未测量多次运行稳定性或更大语料的准确率。8/8 指预设任务状态符合预期，不代表决策理由完全正确：例如失败恢复时模型曾把读取失败描述为搜索失败，但实际执行重新检索、读取并恢复。应增加动作依据准确性评分。

检索依赖小型主题词表，对主题内复杂多条件问题只能返回相关原文。当前不保证回答所有细粒度子问题；例如询问字幕识别准确率时，可引用 P01 中“未提供准确率证据”，但状态可能仍为 answered。正式应用应增加引用片段与问题的语义充分性校验及追问策略。

冲突检测依赖人工提供的 topic/scope/value，尚未从任意自然语言制度自动抽取规范和适用范围。日期未作完整日历合法性校验。长文档、跨主题组合问题、权限隔离和恶意资料内容需扩展评测。

GitHub 仓库为 https://github.com/enteriyt/quvideo-knowledge-agent-2026，提交 SHA 在最终交付时从实际上传版本读取。外部付费模型服务未实测。
