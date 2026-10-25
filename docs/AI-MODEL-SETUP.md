# 影序 AI 命名服务配置

影序桌面端可使用本机 Ollama，或使用阿里云百炼千问、DeepSeek、OpenRouter 三家云端视觉服务。API Key 由用户自行申请并保存在 macOS 钥匙串或 Windows 凭据库中，不随项目源码、安装包或同步历史发布。服务地址由影序按服务商固定；模型名称可在支持的情况下调整。

## 千问新人免费额度

1. 登录[阿里云百炼](https://bailian.console.aliyun.com/)并开通 Model Studio。阿里云账号、服务开通和实名验证由账号持有人完成。
2. 进入[API Key 管理](https://bailian.console.aliyun.com/model/settings/api-key)，选择**华北 2（北京）**地域，创建普通 API Key。不要使用 Token Plan/Coding Plan 专用 Key 来消耗新人免费额度。
3. 在百炼的免费额度设置中开启**仅免费额度**，避免额度用尽后按量付费。
4. 在影序桌面端打开“偏好设置 → AI 自动命名”，启用 AI，选择“云端模型 API → 阿里云百炼 · 千问”，粘贴 API Key 并保存。默认模型为 `qwen3-vl-flash`，默认地址为 `https://dashscope.aliyuncs.com/compatible-mode/v1`。

百炼免费额度按账号和模型发放；符合条件的视觉模型通常提供 100 万 Token，额度有效期通常为 90 天。额度、模型资格及期限以百炼控制台显示为准。仅免费额度模式下额度用尽会停止调用。详细规则见[官方新人免费额度说明](https://help.aliyun.com/zh/model-studio/new-free-quota)和[API Key 指南](https://help.aliyun.com/zh/model-studio/get-api-key/)。

## 其他云端服务

- **DeepSeek**：预设 API 地址 `https://api.deepseek.com`、视觉模型 `deepseek-flash`。具体免费政策以 DeepSeek 账号页面为准。
- **OpenRouter**：预设 API 地址 `https://openrouter.ai/api/v1`、`openrouter/free`。路由器会动态选择可用的免费模型；具体模型、容量和速率限制可能变化。
## AI 功能范围与隐私

云端视觉命名和 AI 废片建议会将经过缩放的照片样本发送给所选服务。影序不会把原始媒体上传到 Firebase；云端模型分析是独立且可关闭的功能。请先阅读所选服务的数据处理条款，再启用云端分析。

AI 只给出事件名称和废片建议，结果需要用户复核。文件完全重复由本地 SHA-256 检测，相似照片由本地感知哈希判断；AI 不负责可靠的语义筛重，也不会自动删除文件。
