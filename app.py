import os
import re
import json
from datetime import datetime

import streamlit as st
from openai import OpenAI

APP_VERSION = "v2.3-clean-json"
SECTIONS_FILE = "karamazov_sections.json"
SECTIONS_FILE_FALLBACK = r"D:\karamazov\karamazov_sections.json"
DEFAULT_MODEL = "gpt-4.1-mini"

st.set_page_config(
    page_title="《卡拉马佐夫兄弟》AI 互动文学档案馆",
    page_icon="📚",
    layout="wide",
)

api_key = None
try:
    api_key = st.secrets.get("OPENAI_API_KEY", None)
except Exception:
    api_key = None

if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key) if api_key else None


CHARACTERS = {
    "阿廖沙": {
        "aliases": ["阿廖沙", "阿列克谢", "Alyosha", "Alexey", "Alexei"],
        "identity": "卡拉马佐夫家最小的儿子，接近佐西马长老，具有精神性、同情心和倾听能力。",
        "conflict": "他相信爱与信仰，但面对的是家庭腐烂、欲望、怀疑、痛苦和道德混乱。",
    },
    "德米特里": {
        "aliases": ["德米特里", "米佳", "Dmitri", "Mitya"],
        "identity": "卡拉马佐夫家的长子，热烈、冲动、感官化，卷入金钱、爱情、嫉妒和罪感。",
        "conflict": "他被欲望、骄傲和嫉妒驱动，同时又渴望忏悔、受苦和精神重生。",
    },
    "伊万": {
        "aliases": ["伊万", "Ivan", "Vanya"],
        "identity": "卡拉马佐夫家的知识型儿子，聪明、怀疑、痛苦，思考上帝、恶、自由和责任。",
        "conflict": "他不能接受无辜者尤其儿童的苦难，因此拒绝廉价的信仰安慰，却也无法逃避思想后果。",
    },
    "老卡拉马佐夫": {
        "aliases": ["老卡拉马佐夫", "费奥多尔", "费尧多尔", "Fyodor", "Fyodor Pavlovich"],
        "identity": "卡拉马佐夫兄弟的父亲，粗俗、贪婪、放荡、滑稽而腐败。",
        "conflict": "他代表堕落的父权和责任缺席，也成为儿子们憎恨、争夺与弑父想象的对象。",
    },
    "斯麦尔佳科夫": {
        "aliases": ["斯麦尔佳科夫", "斯乜尔加科夫", "Smerdyakov", "Pavel"],
        "identity": "老卡拉马佐夫家的仆人，身份暧昧，怨恨、阴冷、计算性强。",
        "conflict": "他把屈辱、怨恨和关于道德许可的思想转化为现实行动。",
    },
    "格鲁申卡": {
        "aliases": ["格鲁申卡", "格露莘卡", "Grushenka", "Agrafena"],
        "identity": "被德米特里和老卡拉马佐夫同时欲望化的女性，魅力强烈但并非简单诱惑者。",
        "conflict": "她在受伤的骄傲、欲望、报复、操控和情感转化之间摇摆。",
    },
    "卡捷琳娜": {
        "aliases": ["卡捷琳娜", "卡嘉", "Katerina", "Katya"],
        "identity": "德米特里的未婚妻或旧情人之一，骄傲、道德感强、受伤，也和伊万形成复杂关系。",
        "conflict": "她常把牺牲、骄傲、爱、复仇和道德优越感混在一起。",
    },
    "佐西马长老": {
        "aliases": ["佐西马", "长老", "Zosima", "Elder Zosima"],
        "identity": "阿廖沙的精神导师，强调积极的爱、谦卑、普遍责任和精神更新。",
        "conflict": "他的教导为小说提供精神回应，但也受到怀疑、丑闻和肉身死亡的挑战。",
    },
    "伊柳沙": {
        "aliases": ["伊柳沙", "Ilyusha", "Ilyushechka"],
        "identity": "一个受苦的孩子，牵动关于无辜、残酷、怜悯和道德教育的主题。",
        "conflict": "他的痛苦迫使读者面对：当孩子受苦时，信仰、爱和责任还能如何成立？",
    },
}

THEMES = {
    "信仰与怀疑": ["信仰", "怀疑", "上帝", "无神论", "伊万", "阿廖沙", "佐西马", "大审判官"],
    "弑父与责任": ["弑父", "父亲", "谋杀", "责任", "德米特里", "伊万", "斯麦尔佳科夫", "老卡拉马佐夫"],
    "儿童苦难": ["儿童", "孩子", "苦难", "无辜", "伊柳沙", "眼泪", "伊万"],
    "欲望与堕落": ["欲望", "堕落", "金钱", "嫉妒", "格鲁申卡", "德米特里", "老卡拉马佐夫"],
    "骄傲与羞辱": ["骄傲", "羞辱", "牺牲", "复仇", "卡捷琳娜", "格鲁申卡", "德米特里", "伊万"],
    "积极的爱": ["积极的爱", "爱", "佐西马", "阿廖沙", "责任", "谦卑", "怜悯"],
}

RELATIONSHIPS = [
    ("老卡拉马佐夫", "德米特里", "父子 / 金钱冲突 / 欲望竞争"),
    ("老卡拉马佐夫", "伊万", "父子 / 冷漠与轻蔑"),
    ("老卡拉马佐夫", "阿廖沙", "父子 / 道德对照"),
    ("德米特里", "伊万", "兄弟 / 判断、竞争与责任"),
    ("德米特里", "阿廖沙", "兄弟 / 倾诉与信任"),
    ("伊万", "阿廖沙", "兄弟 / 信仰与怀疑的对话"),
    ("德米特里", "格鲁申卡", "激情之爱 / 嫉妒"),
    ("老卡拉马佐夫", "格鲁申卡", "欲望 / 与儿子的竞争"),
    ("德米特里", "卡捷琳娜", "婚约、债务与受伤的骄傲"),
    ("伊万", "卡捷琳娜", "理性与情感的张力"),
    ("阿廖沙", "佐西马长老", "弟子 / 精神导师"),
    ("伊万", "斯麦尔佳科夫", "思想影响 / 道德罪责"),
    ("老卡拉马佐夫", "斯麦尔佳科夫", "主人 / 仆人 / 暧昧身世阴影"),
    ("阿廖沙", "伊柳沙", "怜悯与道德教育"),
]


def load_sections():
    json_path = SECTIONS_FILE
    if not os.path.exists(json_path):
        json_path = SECTIONS_FILE_FALLBACK

    if not os.path.exists(json_path):
        return [{
            "title": "未找到文本资料",
            "book_number": 1,
            "source": "系统提示",
            "text": "没有找到 karamazov_sections.json。请先把 EPUB 转换成 JSON。"
        }], False, "未找到文本资料，请先生成 karamazov_sections.json。"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_sections = data.get("sections", data if isinstance(data, list) else [])
    sections = []

    for i, item in enumerate(raw_sections):
        if not isinstance(item, dict):
            continue

        text = str(item.get("text", "")).strip()

        if len(text) < 20:
            continue

        sections.append({
            "title": str(item.get("title", f"章节 {i + 1}")).strip(),
            "book_number": int(item.get("book_number", i + 1)),
            "source": str(item.get("source", SECTIONS_FILE)),
            "text": text,
        })

    if not sections:
        return [{
            "title": "文本资料为空",
            "book_number": 1,
            "source": "系统提示",
            "text": "karamazov_sections.json 存在，但里面没有有效正文。"
        }], False, "文本资料存在，但没有有效正文。"

    return sections, True, f"已载入文本资料，共 {len(sections)} 个章节/段落。"


def safe_join(items):
    return "、".join(items) if items else "暂无资料"


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def detect_characters(text):
    found = []
    lower = text.lower()

    for name, data in CHARACTERS.items():
        for alias in data["aliases"]:
            if alias.lower() in lower or alias in text:
                found.append(name)
                break

    return found


def detect_themes(text):
    found = []
    lower = text.lower()

    for theme, keywords in THEMES.items():
        for kw in keywords:
            if kw.lower() in lower or kw in text:
                found.append(theme)
                break

    return found


def make_chunks(sections):
    chunks = []

    for section_index, section in enumerate(sections):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section["text"]) if p.strip()]

        if not paragraphs:
            paragraphs = [section["text"]]

        current = ""
        n = 1

        def add_chunk(content):
            nonlocal n

            if not content.strip():
                return

            chunks.append({
                "id": f"K-{section_index + 1:03d}-{n:02d}",
                "section_index": section_index,
                "section_title": section["title"],
                "book_number": section.get("book_number", 0),
                "source": section.get("source", ""),
                "content": content.strip(),
                "characters": detect_characters(content),
                "themes": detect_themes(content),
            })

            n += 1

        for para in paragraphs:
            if len(current) + len(para) <= 2400:
                current = current + "\n\n" + para if current else para
            else:
                add_chunk(current)
                current = current[-250:] + "\n\n" + para

        add_chunk(current)

    return chunks


def expand_query(q):
    q = q or ""

    mapping = {
        "阿廖沙": "阿廖沙 阿列克谢 信仰 爱 佐西马",
        "德米特里": "德米特里 米佳 欲望 罪感 格鲁申卡 金钱",
        "米佳": "德米特里 米佳 欲望 罪感 格鲁申卡 金钱",
        "伊万": "伊万 上帝 怀疑 反抗 儿童苦难 大审判官 责任",
        "老卡拉马佐夫": "老卡拉马佐夫 费奥多尔 父亲 弑父 金钱 欲望",
        "斯麦尔佳科夫": "斯麦尔佳科夫 伊万 谋杀 责任 仆人",
        "格鲁申卡": "格鲁申卡 德米特里 欲望 老卡拉马佐夫",
        "卡捷琳娜": "卡捷琳娜 卡嘉 骄傲 债 德米特里 伊万",
        "佐西马": "佐西马 长老 积极的爱 信仰 阿廖沙",
        "大审判官": "大审判官 伊万 基督 自由 奇迹 权威",
        "信仰": "信仰 上帝 佐西马 阿廖沙 怀疑",
        "怀疑": "怀疑 无神论 伊万 苦难",
        "弑父": "弑父 父亲 谋杀 德米特里 伊万 斯麦尔佳科夫",
        "儿童": "儿童 孩子 伊柳沙 苦难 无辜",
        "苦难": "苦难 儿童 伊万 反抗",
        "责任": "责任 罪责 伊万 斯麦尔佳科夫",
        "欲望": "欲望 堕落 德米特里 格鲁申卡 老卡拉马佐夫",
        "审判": "审判 法庭 德米特里 证据",
    }

    for k, v in mapping.items():
        if k in q:
            q += " " + v

    return q


def retrieve(chunks, query, current_index, spoiler_free=True, top_k=6):
    pool = [c for c in chunks if (not spoiler_free or c["section_index"] <= current_index)]
    q = normalize(expand_query(query)).lower()

    if not q:
        return [c for c in pool if c["section_index"] == current_index][:top_k]

    terms = [x for x in re.split(r"[\s,，。；;:：!?？、]+", q) if len(x) >= 2]
    scored = []

    for c in pool:
        text = normalize(
            c["id"]
            + " "
            + c["section_title"]
            + " "
            + c["content"]
            + " "
            + " ".join(c["characters"])
            + " "
            + " ".join(c["themes"])
        ).lower()

        score = 4 if c["section_index"] == current_index else 0

        for t in terms:
            if t in text:
                score += 5

        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [c for score, c in scored if score > 0][:top_k]

    return result if result else pool[:top_k]


def format_chunks(chunks):
    if not chunks:
        return "没有找到证据片段。"

    parts = []

    for c in chunks:
        parts.append(
            f"[{c['id']}] {c['section_title']}\n"
            f"人物：{safe_join(c['characters'])}\n"
            f"主题：{safe_join(c['themes'])}\n"
            f"文本：\n{c['content']}"
        )

    return "\n\n---\n\n".join(parts)


def display_chunks(chunks):
    if not chunks:
        st.write("暂无检索到的证据片段。")
        return

    for c in chunks:
        with st.expander(f"[{c['id']}] {c['section_title']}"):
            st.write("**来源：**", c.get("source", ""))
            st.write("**人物：**", safe_join(c["characters"]))
            st.write("**主题：**", safe_join(c["themes"]))
            st.write(c["content"])


def call_ai(system_prompt, user_prompt):
    if client is None:
        return "没有读取到 OpenAI API key。请设置 OPENAI_API_KEY。"

    response = client.chat.completions.create(
        model=st.session_state.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.35,
    )

    return response.choices[0].message.content


def ask_ai(task, section_title, evidence, question, spoiler_free=True):
    system_prompt = f"""
你是《卡拉马佐夫兄弟》的中文文学阅读助手。
请主要根据证据片段回答，不要编造证据之外的内容。
如果不剧透模式开启，不要透露当前阅读进度之后的情节。
关键判断后引用证据编号，例如 [K-003-01]。
回答必须是中文，具体、有文学分析价值。
不剧透模式：{"开启" if spoiler_free else "关闭"}
"""

    user_prompt = f"""
任务：{task}
当前章节：{section_title}
用户问题：{question if question.strip() else "没有额外问题，请按任务分析。"}

证据片段：
{format_chunks(evidence)}
"""

    return call_ai(system_prompt, user_prompt)


def escape_dot(text):
    return str(text).replace('"', '\\"')


def relationship_dot():
    dot = [
        "graph G {",
        "rankdir=LR;",
        'bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fillcolor="#F7F7F7", fontname="Microsoft YaHei"];',
        'edge [fontname="Microsoft YaHei", fontsize=10];',
    ]

    for a, b, rel in RELATIONSHIPS:
        dot.append(f'"{escape_dot(a)}" -- "{escape_dot(b)}" [label="{escape_dot(rel)}"];')

    dot.append("}")

    return "\n".join(dot)


if "model_name" not in st.session_state:
    st.session_state.model_name = DEFAULT_MODEL

if "history" not in st.session_state:
    st.session_state.history = []

sections, loaded, message = load_sections()
chunks = make_chunks(sections)

st.title("📚《卡拉马佐夫兄弟》AI 互动文学档案馆")

with st.sidebar:
    page = st.radio(
        "导航",
        ["首页", "阅读助手", "人物档案", "人物关系图", "主题面板", "证据检索", "分析历史/导出", "项目说明"],
    )

    st.divider()

    st.session_state.model_name = st.text_input("模型名称", value=st.session_state.model_name)

    st.divider()

    st.write("文本状态")
    if loaded:
        st.success(message)
    else:
        st.warning(message)


if page == "首页":
    st.subheader("首页")

    if loaded:
        st.success(message)
    else:
        st.warning(message)

    st.write(f"章节/段落数量：{len(sections)}")
    st.write(f"检索片段数量：{len(chunks)}")

    st.markdown("### 章节预览")
    for s in sections[:30]:
        st.write("- " + s["title"])

    if len(sections) > 30:
        st.write(f"... 还有 {len(sections) - 30} 个章节/段落")


elif page == "阅读助手":
    with st.sidebar:
        idx = st.selectbox("选择章节", range(len(sections)), format_func=lambda i: sections[i]["title"])
        spoiler_free = st.checkbox("不剧透模式", value=True)
        task = st.radio("选择功能", ["章节摘要", "人物心理分析", "思想/主题分析", "伏笔/线索提醒", "自由提问"])
        question = st.text_area("具体问题 / 需求（可选）", height=130)
        top_k = st.slider("证据片段数量", 3, 10, 6)
        run = st.button("开始 AI 分析")

    section = sections[idx]
    evidence = retrieve(chunks, f"{section['title']} {task} {question} {section['text'][:800]}", idx, spoiler_free, top_k)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("章节预览")
        st.write(section["text"][:2600] + ("..." if len(section["text"]) > 2600 else ""))
        st.subheader("证据片段")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 分析")

        if run:
            with st.spinner("AI 正在分析..."):
                ans = ask_ai(task, section["title"], evidence, question, spoiler_free)
                st.write(ans)
                st.session_state.history.insert(0, {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "page": "阅读助手",
                    "section": section["title"],
                    "task": task,
                    "question": question,
                    "answer": ans,
                })
        else:
            st.info("选择章节和任务后点击开始。")


elif page == "人物档案":
    with st.sidebar:
        idx = st.selectbox("当前阅读进度", range(len(sections)), format_func=lambda i: sections[i]["title"])
        name = st.selectbox("选择人物", list(CHARACTERS.keys()))
        question = st.text_area("关于这个人物的问题（可选）", height=130)
        run = st.button("生成人物分析")

    data = CHARACTERS[name]
    evidence = retrieve(chunks, f"{name} {' '.join(data['aliases'])} {question}", idx, True, 7)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(name)
        st.write("**身份：**", data["identity"])
        st.write("**核心困境：**", data["conflict"])
        st.write("**别名：**", safe_join(data["aliases"]))
        st.subheader("相关证据")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 人物分析")

        if run:
            prompt = f"请分析人物：{name}\n身份：{data['identity']}\n核心困境：{data['conflict']}\n用户问题：{question}\n证据：\n{format_chunks(evidence)}"
            st.write(call_ai("你是中文文学人物分析助手。请用中文分析，并引用证据编号。", prompt))
        else:
            st.info("选择人物后点击生成人物分析。")


elif page == "人物关系图":
    st.subheader("人物关系图")
    st.graphviz_chart(relationship_dot(), use_container_width=True)

    st.markdown("### 关系说明")
    for a, b, rel in RELATIONSHIPS:
        st.write(f"- **{a}** — **{b}**：{rel}")


elif page == "主题面板":
    with st.sidebar:
        idx = st.selectbox("当前阅读进度", range(len(sections)), format_func=lambda i: sections[i]["title"])
        theme = st.selectbox("选择主题", list(THEMES.keys()))
        question = st.text_area("关于主题的问题（可选）", height=130)
        run = st.button("AI 解读主题")

    evidence = retrieve(chunks, f"{theme} {' '.join(THEMES[theme])} {question}", idx, True, 8)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(theme)
        st.write("关键词：" + safe_join(THEMES[theme]))
        st.subheader("相关证据")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 主题分析")

        if run:
            prompt = f"主题：{theme}\n关键词：{safe_join(THEMES[theme])}\n问题：{question}\n证据：\n{format_chunks(evidence)}"
            st.write(call_ai("你是中文文学主题分析助手。请根据证据分析，并引用证据编号。", prompt))
        else:
            st.info("选择主题后点击解读。")


elif page == "证据检索":
    with st.sidebar:
        idx = st.selectbox("当前阅读进度", range(len(sections)), format_func=lambda i: sections[i]["title"])
        spoiler_free = st.checkbox("不剧透模式", value=True)
        query = st.text_area("检索问题 / 关键词", height=120)
        top_k = st.slider("返回片段数量", 3, 12, 7)
        run = st.button("检索并让 AI 解读")

    evidence = retrieve(chunks, query, idx, spoiler_free, top_k)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("检索结果")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 证据解读")

        if run:
            prompt = f"问题：{query}\n证据：\n{format_chunks(evidence)}"
            st.write(call_ai("你只能根据证据回答。如果证据不足，请说明。请用中文回答并引用证据编号。", prompt))
        else:
            st.info("输入关键词后点击检索。")


elif page == "分析历史/导出":
    st.subheader("分析历史 / 导出")

    if not st.session_state.history:
        st.info("当前还没有分析历史。")
    else:
        for i, item in enumerate(st.session_state.history):
            with st.expander(f"{i + 1}. {item['time']}｜{item['page']}｜{item['section']}｜{item['task']}"):
                st.write("**问题：**")
                st.write(item["question"])
                st.write("**回答：**")
                st.write(item["answer"])

        st.download_button(
            "下载分析历史 JSON",
            data=json.dumps(st.session_state.history, ensure_ascii=False, indent=2),
            file_name="karamazov_analysis_history.json",
            mime="application/json",
        )


elif page == "项目说明":
    st.subheader("项目说明")
    st.write("这是《卡拉马佐夫兄弟》AI 互动文学档案馆。你可以用它进行章节阅读、人物分析、主题分析、关系查看和证据检索。")
    st.warning("如果文本资料包含现代中文译本全文，不建议公开上传到 GitHub。")
