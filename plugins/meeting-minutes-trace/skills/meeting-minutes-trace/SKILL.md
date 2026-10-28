---
name: meeting-minutes-trace
description: 转写会议纪要，并一键回溯到官方返回的音频时间。未配置 ASSEMBLYAI_API_KEY 时不要请求，也不要编造纪要。
---

# 会议纪要转写

原型行是「会议纪要转写」，描述是「转写会议纪要，一键溯源」。本技能调用 AssemblyAI Speech Understanding 完成这件事。它不是 Whisper，不是腾讯会议，不是飞书，也不是通义听悟。

契约在 `references/contract.md`。不要改端点，不要补文档里没有的字段，不要把缺失密钥说成已经转写成功。

音频会上传或提交给 AssemblyAI。没有用户明确要求时，不要提交会议音频。不要把 API key 写入聊天、命令行参数或纪要文件。

## 配置

`user_config.assemblyai_api_key` 必填，敏感，无默认。启动前只放到环境变量 `ASSEMBLYAI_API_KEY`。不要读配置文件，不要搜索主目录，不要向用户索要密钥原文。

可选 `ASSEMBLYAI_BASE_URL` 只能是 `https://api.assemblyai.com` 或 `https://api.eu.assemblyai.com`。未设置时用前者。

## 命令

写纪要。默认两次官方任务：先全文纪要，再带决议的待办。两次都会转写同一音频。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/minutes.py write --audio-url https://example.com/meeting.mp3 --out minutes.json --wait-seconds 600
```

本地文件会先 `POST /v2/upload`，再用返回的 `upload_url`：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/minutes.py write --audio-file <path-to-audio-file> --out minutes.json --wait-seconds 600
```

只要纪要摘要、不要第二次待办任务时加 `--skip-actions`。未完成时退出码 3，文件里有官方 transcript id。继续只轮询已有 id，不新开任务：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/minutes.py resume --minutes minutes.json --wait-seconds 600
```

一键溯源不访问网络。`m1` 是第一条纪要，`a1` 是第一条待办：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/minutes.py trace --minutes minutes.json --id m1
```

没有密钥时，`write` 退出码为 2，状态是 `unavailable`，`network` 为 `not_sent`。这不是转写成功。

## 不要做的事

- 不要运行 Whisper，也不要把转写文本本地总结后假装来自本接口。
- 不要在 `speech_understanding.request` 里同时放 summarization 和 action_items。
- 不要编造 `start`、`end`、`timestamp` 或 `quote`。
- 不要把本包的离线测试或 401 探测说成 native PASS。
