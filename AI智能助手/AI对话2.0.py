import streamlit as st
import os
import sqlite3
from openai import OpenAI
from datetime import datetime
import json

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="AI智能伴侣",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}
)

# ============================================================
# 数据库初始化（替代原来的 JSON 文件存储）
# ============================================================
DB_PATH = "sessions.db"

def init_db():
    """初始化 SQLite 数据库，创建会话表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            title        TEXT,
            nick_name    TEXT,
            nature       TEXT,
            messages     TEXT,
            updated_at   TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# 工具函数
# ============================================================

def generate_session_name():
    """生成基于时间戳的会话 ID"""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_api_client():
    """
    安全地获取 API Key，优先读环境变量，其次读 Streamlit Secrets。
    如果都没有，则在页面上报错并停止运行。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("DEEPSEEK_API_KEY")
        except Exception:
            pass
    if not api_key:
        st.error("⚠️ 未检测到 DEEPSEEK_API_KEY，请配置环境变量或 Streamlit Secrets 后重试。")
        st.stop()
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def generate_session_title(client, messages):
    """
    调用 AI，根据前两条消息自动生成会话标题（5 字以内）。
    失败时回退到时间戳。
    """
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=20,
            messages=[
                {"role": "system", "content": "用5个字以内总结这段对话的主题，只输出主题词，不要标点"},
                *messages[:2]
            ]
        )
        title = resp.choices[0].message.content.strip()
        return title if title else st.session_state.current_session
    except Exception:
        return st.session_state.current_session


# ============================================================
# 数据库 CRUD
# ============================================================

def save_session(client=None):
    """保存当前会话到 SQLite"""
    if not st.session_state.current_session:
        return
    # 如果是第一次保存且消息非空，自动生成标题
    if (
        client is not None
        and st.session_state.messages
        and st.session_state.session_title == st.session_state.current_session
    ):
        title = generate_session_title(client, st.session_state.messages)
        st.session_state.session_title = title
    else:
        title = st.session_state.session_title

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (session_id, title, nick_name, nature, messages, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            title      = excluded.title,
            nick_name  = excluded.nick_name,
            nature     = excluded.nature,
            messages   = excluded.messages,
            updated_at = excluded.updated_at
    """, (
        st.session_state.current_session,
        title,
        st.session_state.nick_name,
        st.session_state.nature,
        json.dumps(st.session_state.messages, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def load_sessions():
    """加载所有会话列表，按更新时间倒序"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM sessions ORDER BY updated_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows  # [(session_id, title), ...]


def load_session(session_id):
    """加载指定会话"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, nick_name, nature, messages FROM sessions WHERE session_id = ?", (session_id,))
        row = c.fetchone()
        conn.close()
        if row:
            st.session_state.session_title   = row[0]
            st.session_state.nick_name       = row[1]
            st.session_state.nature          = row[2]
            st.session_state.messages        = json.loads(row[3])
            st.session_state.current_session = session_id
    except Exception as e:
        st.error(f"加载会话失败：{e}")


def delete_session(session_id):
    """删除指定会话"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        if session_id == st.session_state.current_session:
            st.session_state.messages        = []
            st.session_state.current_session = generate_session_name()
            st.session_state.session_title   = st.session_state.current_session
    except Exception as e:
        st.error(f"删除会话失败：{e}")


def clear_current_session():
    """清空当前会话消息（不删除记录）"""
    st.session_state.messages = []
    st.session_state.current_session = generate_session_name()
    st.session_state.session_title   = st.session_state.current_session


# ============================================================
# Session State 初始化
# ============================================================
if "messages"         not in st.session_state:
    st.session_state.messages         = []
if "nick_name"        not in st.session_state:
    st.session_state.nick_name        = "AI智能助手"
if "nature"           not in st.session_state:
    st.session_state.nature           = "你是一个有着丰富跨境电商经验的从业者"
if "current_session"  not in st.session_state:
    st.session_state.current_session  = generate_session_name()
if "session_title"    not in st.session_state:
    st.session_state.session_title    = st.session_state.current_session

# ============================================================
# API 客户端（全局复用）
# ============================================================
client = get_api_client()

# ============================================================
# 系统提示词
# ============================================================
SYSTEM_PROMPT = """
        你叫 %s，现在是用户的真实伴侣，请完全代入伴侣角色。
        规则：
            1. 每次只回1条消息
            2. 禁止任何场景或状态描述性文字
            3. 匹配用户的语言
            4. 回复简短，像微信聊天一样
            5. 有需要的话可以用❤️🌸等emoji表情
            6. 用符合伴侣性格的方式对话
            7. 回复的内容，要充分体现伴侣的性格特征
        伴侣性格：
            - %s
        你必须严格遵守上述规则来回复用户。
    """

# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    st.subheader("AI 控制面板")

    col_new, col_clear = st.columns(2)
    with col_new:
        if st.button("新建会话", use_container_width=True, icon="✏️"):
            save_session(client)
            if st.session_state.messages:
                clear_current_session()
                st.rerun()
    with col_clear:
        if st.button("清空对话", use_container_width=True, icon="🗑️"):
            clear_current_session()
            st.rerun()

    st.text("会话历史")
    session_list = load_sessions()
    for session_id, title in session_list:
        col1, col2 = st.columns([4, 1])
        with col1:
            btn_type = "primary" if session_id == st.session_state.current_session else "secondary"
            if st.button(
                title or session_id,
                use_container_width=True,
                icon="📄",
                key=f"load_{session_id}",
                type=btn_type
            ):
                load_session(session_id)
                st.rerun()
        with col2:
            if st.button("", use_container_width=True, icon="❌️", key=f"delete_{session_id}"):
                delete_session(session_id)
                st.rerun()

    st.divider()

    st.subheader("伴侣信息")
    nick_name = st.text_input("昵称", placeholder="请输入昵称", value=st.session_state.nick_name)
    if nick_name and nick_name != st.session_state.nick_name:
        st.session_state.nick_name = nick_name
        st.toast("昵称已更新 ✅")

    nature = st.text_area("性格", placeholder="请输入性格", value=st.session_state.nature)
    if nature and nature != st.session_state.nature:
        st.session_state.nature = nature
        st.toast("性格已更新 ✅")

# ============================================================
# 主页面
# ============================================================
st.title("AI智能伴侣")
st.logo("😎")
st.text(f"当前会话：{st.session_state.session_title}")

# 展示历史消息
for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

# ============================================================
# 消息输入与 AI 响应
# ============================================================
MAX_INPUT_LENGTH = 500  # 限制单次输入长度

prompt = st.chat_input("请输入您要问的问题")
if prompt:
    # 输入长度校验
    if len(prompt) > MAX_INPUT_LENGTH:
        st.warning(f"输入内容过长（{len(prompt)} 字），请控制在 {MAX_INPUT_LENGTH} 字以内。")
        st.stop()

    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 AI（带错误处理）
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT % (st.session_state.nick_name, st.session_state.nature)},
                *st.session_state.messages
            ],
            stream=True
        )

        # ✅ 使用 write_stream 替代手动拼接，避免闪烁
        with st.chat_message("assistant"):
            full_response = st.write_stream(response)

    except Exception as e:
        st.error(f"AI 响应失败，请稍后重试。错误信息：{e}")
        # 回滚刚刚加入的用户消息，避免脏数据
        st.session_state.messages.pop()
        st.stop()

    # 保存消息 & 会话（第一条消息时自动生成标题）
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_session(client)