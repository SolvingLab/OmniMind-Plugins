# 音频生成

根据文字描述生成音频。文字是声音描述，不是朗读稿。

可调用入口是 `scripts/generate_audio.py`，安装后的 MCP 工具名是 `generate_audio`。两者都调用已固定的官方接口 `POST https://api.elevenlabs.io/v1/sound-generation`。没有 `ELEVENLABS_API_KEY` 时返回 `setup_required`，不发送请求。

这不是 ElevenLabs、Runway、Suno 或语音合成产品的改名包。安装不会生成音频，也不会写入密钥。
