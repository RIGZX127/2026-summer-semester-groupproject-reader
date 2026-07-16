# Mercury RSS Reader — 使用指南

## 安装

### macOS
1. 双击 `Mercury-macos-xxx.dmg` 挂载
2. 将 **Mercury** 拖入 **Applications** 文件夹
3. 首次打开：在 Applications 中**右键 Mercury → 打开**（未签名需确认一次，仅首次）

### Windows
双击 `Mercury.exe`，Windows Defender 提示时点击「更多信息」→「仍要运行」。

---

## 添加订阅源

1. 打开 Mercury，左侧点击 **「＋ 添加订阅」**
2. 输入 RSS/Atom 地址，例如：
   - Hacker News：`https://hnrss.org/frontpage`
   - 阮一峰：`https://feeds.feedburner.com/ruanyifeng`
   - 任何博客或新闻站的 RSS 链接
3. 确认后自动同步文章

---

## 阅读文章

### 三种模式
工具栏可切换：
- **Reader** — 纯净正文阅读（AI 提取 + 清洗）
- **Web** — 原始网页渲染
- **双栏** — 左右分屏对比

### 查看文章
1. 左侧点订阅源 → 中间出现文章列表
2. 点文章 → 右侧 Reader 渲染正文
3. 调节 **字号（14–24px）、主题（浅/深/跟随系统）、内容宽度（窄/中/宽）**

### 文章管理
| 操作 | 方式 |
|------|------|
| 搜索 | 文章列表上方搜索框 |
| 已读/未读 | 右键 → 标记已读 |
| 收藏 | 右键 → 收藏 |
| 删除 | 右键 → 删除 |

### 专注模式
工具栏右侧点 ⛶ 按钮，隐藏侧栏和文章列表，Reader 占满窗口。

---

## AI 功能（需先配置 LLM）

### 第一步：配置 LLM

菜单栏 **AI → AI 设置**（快捷键 `Ctrl+,`）：

1. **Provider 标签页**：填入 API 地址 + 模型名 + API Key
   - 本地 Ollama：`http://localhost:11434/v1` / `qwen3`（无需 Key）
   - OpenAI：`https://api.openai.com/v1` / `gpt-4o-mini` / `sk-xxx`
   - DeepSeek：`https://api.deepseek.com/v1` / `deepseek-chat` / `sk-xxx`
2. **Agent 标签页**：配置摘要语言/详细度 + 翻译目标语言/并发数

### 第二步：使用 AI

| 功能 | 操作 | 说明 |
|------|------|------|
| **AI 摘要** | 点开文章 → 底部「✨ AI 摘要」→ 点击「生成摘要」 | 流式显示，可折叠。支持自动摘要（设置中开启） |
| **AI 翻译** | 工具栏点「翻译」 | 实时进度，完成后可选原文/双语/仅译文三种模式 |
| **AI 标签** | CLI（见下方） | 标签建议 UI 开发中 |

---

## 命令行工具（高级）

内置的 CLI 工具可直接操作 Agent：

```bash
# 配置 LLM（写入 QSettings，GUI 也共用）
Mercury.exe configure --base-url http://localhost:11434/v1 --model qwen3

# 列出所有文章
Mercury.exe list

# 单独测试
Mercury.exe summary 1      # AI 摘要
Mercury.exe translate 1    # AI 翻译
Mercury.exe tagging 1      # AI 标签建议

# 一键验证所有 Agent
Mercury.exe verify-all 1
```

---

## 数据与配置

所有数据存储在 `~/.mercury/`：
```
~/.mercury/
├── mercury.db        # SQLite 数据库
├── prompts/          # 自定义提示词（可选）
└── translation_*.html # 翻译导出缓存
```

备份：复制整个 `.mercury` 文件夹即可。恢复时放回原位。

---

## 常见问题

**Q: 文章显示「Reader 模式不可用」？**
Cloudflare 等防护网站 httpx 无法抓取，自动降级到 Web 模式用内置浏览器渲染。

**Q: 翻译点了没反应？**
检查是否已在 AI 设置中配置 LLM Provider。

**Q: 如何备份/迁移？**
复制 `~/.mercury/` 文件夹到新电脑相同位置。

**Q: macOS 提示「已损坏无法打开」？**
终端运行：`xattr -cr /Applications/Mercury.app` 后重新打开。

---

## 技术栈

| 层 | 技术 |
|----|------|
| UI | PySide6 + Qt WebEngine |
| 后端 | Python 3.12+ asyncio |
| 正文提取 | readability-lxml + BeautifulSoup |
| AI Agent | OpenAI 兼容 API（Ollama / GPT / DeepSeek 等） |
| 数据库 | SQLite |
