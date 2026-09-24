# Wiki 同步说明

本目录包含 Wiki 内容。由于 GitHub Wiki 需要先在网页端初始化第一个页面才能通过 git 访问，请按以下步骤同步：

## 手动同步步骤

1. 前往 https://github.com/YuJunt/agent-plugin-creator/wiki
2. 点击 "Create the first page" 创建首页
3. 克隆 Wiki 仓库：
   ```bash
   git clone https://github.com/YuJunt/agent-plugin-creator.wiki.git
   ```
4. 复制本目录内容到 Wiki 仓库：
   ```bash
   cp docs/wiki/*.md agent-plugin-creator.wiki/
   ```
5. 提交并推送：
   ```bash
   cd agent-plugin-creator.wiki
   git add .
   git commit -m "Add wiki content"
   git push
   ```

## Wiki 页面列表

| 文件 | 标题 |
|------|------|
| Home.md | 首页 |
| FAQ.md | 常见问题 |
| Best-Practices:-Skill-编写.md | Skill 编写最佳实践 |
| Tutorial:-交互式向导.md | 交互式向导教程 |

## 注意事项

- Wiki 文件名中的空格会被转换为连字符（-）
- 中文文件名需要确保编码正确
- 首页必须命名为 `Home.md`
