---
name: audio-generation
description: 根据文字描述生成音频。调用已固定的 ElevenLabs sound-generation 接口；未配置时保持待配置，不朗读文字，也不改用其它产品。
---

# 音频生成

用户要求根据文字描述生成音频时，生成描述里的声音，不要把描述朗读出来。

稳定身份是 `proto:market:音频生成`。这不是 ElevenLabs、Runway、Suno、Soundcraft、Bitwize 或 xAI 语音合成的改名包。

## 入口

优先调用本包 MCP 工具 `generate_audio`。MCP 未启动时，运行：

```bash
python ${OMNIMIND_PLUGIN_ROOT}/scripts/generate_audio.py --text "<声音描述>" --output "<用户指定的音频文件>"
```

不要把 API key 放进参数、聊天或命令回显。只从环境变量 `ELEVENLABS_API_KEY` 或插件敏感配置 `api_key` 读取。

可选参数与官方合同一致：`--duration-seconds` 为 0.5 到 30，`--prompt-influence` 为 0 到 1，`--loop` 仅在用户要求可循环音效时加上。

## 结果

stdout 是一条 JSON。`status` 为 `success` 且 `ok` 为 true 时，`outputPath` 才是生成的音频。`mimeType` 以 `audio/` 开头。

其它状态都不是成功，包括 `setup_required`、`invalid-prompt`、`invalid-output`、`not-authenticated`、`upstream-error`、`invalid-response`。不要把失败改写成已生成。

## 未配置

没有 `ELEVENLABS_API_KEY`，或 MCP 因缺少 `user_config.api_key` 未启动时，告诉用户到现有插件配置里填写自己的 ElevenLabs key 后再试。不要收集新 key，不要发明 key，不要改用 `POST https://api.x.ai/v1/tts` 或其它接口。

配置检查不会生成音频：

```bash
python ${OMNIMIND_PLUGIN_ROOT}/scripts/generate_audio.py --check-config
```

`configured: true` 只说明 key 已设置，不是函数通过。
