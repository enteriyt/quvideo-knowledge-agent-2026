# 无 API 密钥的真实模型复现

本机实际采用 Qwen3-1.7B 的官方 Q8_0 GGUF 权重，在 llama.cpp b11979 CPU 版运行。模型进程绑定 `127.0.0.1:8089`，上下文 8192，8 个 CPU 线程，1 个并行槽，关闭思考模式。动作仍由神经网络逐轮生成，OfflineMock 不参与这条路径。

## 官方来源与校验

- [llama.cpp b11979 Windows CPU 发布包](https://github.com/ggml-org/llama.cpp/releases/download/b11979/llama-b11979-bin-win-cpu-x64.zip)，24,408,679 字节，SHA-256：`212aa9005c1c32558898e61845665b1860fe7796acc231a335d557c5bdb604af`。
- [Qwen 官方 ModelScope 模型仓库](https://modelscope.cn/models/Qwen/Qwen3-1.7B-GGUF/files)，文件 `Qwen3-1.7B-Q8_0.gguf`，1,834,426,016 字节，SHA-256：`061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`。

本次下载后逐一核对了发布接口提供的摘要。仓库只存代码与证据，运行程序和模型权重单独下载；下载与使用遵循来源项目的许可证。

## 启动和验证

解压 CPU 包，使用实际路径启动（在 Windows PowerShell 执行）：

```powershell
.\scripts\start_local_model.ps1 -LlamaServer 'C:\实际路径\llama-server.exe' -ModelPath 'C:\实际路径\Qwen3-1.7B-Q8_0.gguf'
$env:MODEL_NAME = 'qwen3-1.7b'
$env:MODEL_BASE_URL = 'http://127.0.0.1:8089/v1'
python -X utf8 scripts/evaluate_live.py
```

脚本验证权重哈希，以隐藏窗口启动服务，将 PID 和日志放在被忽略的 `.local-model/`。等待服务日志显示就绪再执行评估。按 PID 停止自己启动的服务时，先核对进程确实是本项目的 llama-server，再停止该进程。

该回环地址配置无需 `MODEL_API_KEY`。应用仅允许明确的 `127.0.0.1` / `::1` 使用 HTTP；外部模型服务仍要求 HTTPS 和密钥。当前本地请求使用 JSON Schema 约束动作结构、temperature=0、最多 384 输出 token，单次模型请求超时 120 秒。JSON Schema 只约束格式，检索词、文档选择和结束状态由模型生成。

`scripts/evaluate_live.py` 会真实调用服务并覆盖 `examples/live/` 的当前结果；`examples/live-initial/` 保留首次验收的结果，`examples/live-initial-format-failure.json` 保留仅使用 JSON object 时缺少 reason 字段的失败记录。初始结果用于说明改进过程，当前验收以 `examples/live/evaluation-summary.json` 为准。不要将这条耗时实测命令混入默认离线测试。
