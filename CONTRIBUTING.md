# 参与影序

欢迎摄影师、剪辑师和开发者提交问题、场景建议与改进。

1. 先搜索已有 Issue，避免重复。
2. Bug 请写明系统版本、影序版本、来源设备、目标磁盘、操作步骤、预期与实际结果。
3. 不要上传真实客户素材、访问令牌、API Key 或包含私人路径的完整日志。
4. 提交代码前运行：`python -m compileall -q smb desktop tests` 和 `python -m unittest discover -s tests -v`。
5. 涉及复制、删除、校验和数据库迁移的改动，必须补回归测试。
