# 会议纪要转写

原型是「会议纪要转写」，功能是「转写会议纪要，一键溯源」。本包是对该功能的可调用适配，不是把 Whisper、腾讯会议或飞书改名。

入口是 `scripts/minutes.py`。它调用 AssemblyAI 已文档化的 Speech Understanding：纪要摘要带 `start`/`end`，待办带 `timestamp` 和 `quote`。没有 `ASSEMBLYAI_API_KEY` 时退出码为 2，不发请求，也不写编造的纪要。

```text
python scripts/minutes.py write --audio-url https://example.com/meeting.mp3 --out minutes.json
python scripts/minutes.py trace --minutes minutes.json --id m1
```

安装本包不会创建 AssemblyAI 账户，也不会代替完成现场转写。现场转写需要用户自己的密钥和可访问的会议音频。
