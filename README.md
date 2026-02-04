# VoiceCode

Windows 托盘工具：按住快捷键录音，松开后语音转文字并写入 OpenCode Desktop 输入框，自动发送。

## 运行

```powershell
uv sync
uv run python -m voicecode.main
```

托盘右键菜单：设置 / 重置 / 退出。

## 设置

托盘菜单 -> 设置：
- 讯飞 AppID / API Secret / API Key
- 快捷键（默认：`<ctrl>+<alt>+<space>`）
- 窗口标题关键字（默认：`OpenCode`）
- 发送按键（`enter` 或 `ctrl+enter`）

## 打包

```powershell
uv run python build.py
```
