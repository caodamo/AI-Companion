# AI智能伴侣

基于 DeepSeek API 和 Streamlit 构建的 AI 智能伴侣聊天系统。

## 功能

- AI 对话
- 多轮聊天
- 自定义昵称
- 自定义性格
- 历史会话管理
- 本地会话保存
- 流式回复

## 安装

```bash
pip install -r requirements.txt
```

## 配置 API Key

Windows：

```powershell
set DEEPSEEK_API_KEY=你的API_KEY
```

Linux / Mac：

```bash
export DEEPSEEK_API_KEY=你的API_KEY
```

## 运行

```bash
streamlit run AI智能助手/AI智能助手.py
```

## 技术栈

- Python
- Streamlit
- DeepSeek API
- OpenAI SDK

## 项目结构

```text
AI伴侣
│
├── AI智能助手
│   └── AI智能助手.py
├── README.md
├── requirements.txt
└── .gitignore
```
