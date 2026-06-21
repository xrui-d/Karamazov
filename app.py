import os
import re
import json
from datetime import datetime

import requests
import streamlit as st
from openai import OpenAI


# ============================================================
# 基本设置
# ============================================================

st.set_page_config(
    page_title="Karamazov Interactive Archive",
    page_icon="📚",
    layout="wide",
)


# ============================================================
# OpenAI API 设置
# 云端：从 Streamlit Secrets 读取 OPENAI_API_KEY
# 本地：也可以从环境变量读取 OPENAI_API_KEY
# ============================================================

api_key = None

try:
    api_key = st.secrets.get("OPENAI_API_KEY", None)
except Exception:
    api_key = None

if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key) if api_key else None


# ============================================================
# 内置资料：人物 / 主题 / 关系
# ============================================================

DEFAULT_MODEL = "gpt-4.1-mini"

CHARACTERS = {
    "Alyosha / 阿廖沙": {
        "aliases": ["Alyosha", "Alexey", "Alexei", "阿廖沙", "阿列克谢"],
        "identity": "The youngest Karamazov brother; spiritually oriented, close to Zosima, often a listener and moral witness.",
        "core_conflict": "He wants to believe in active love and faith, but he is surrounded by corruption, suffering, sensuality, and intellectual rebellion.",
        "keywords": ["faith", "active love", "compassion", "witness", "Zosima"],
    },
    "Dmitri / 德米特里": {
        "aliases": ["Dmitri", "Mitya", "Mitka", "德米特里", "米佳"],
        "identity": "The eldest Karamazov brother; passionate, impulsive, sensual, and caught in conflict over money, love, and guilt.",
        "core_conflict": "He is torn between sensual excess, jealousy, pride, guilt, and a desire for moral rebirth.",
        "keywords": ["passion", "guilt", "jealousy", "honor", "Grushenka"],
    },
    "Ivan / 伊万": {
        "aliases": ["Ivan", "Vanya", "伊万"],
        "identity": "The intellectual brother; skeptical, brilliant, tormented by God, evil, freedom, and responsibility.",
        "core_conflict": "He rejects easy faith because of innocent suffering, yet cannot escape moral responsibility for ideas and consequences.",
        "keywords": ["reason", "atheism", "rebellion", "suffering", "responsibility"],
    },
    "Fyodor Pavlovich / 老卡拉马佐夫": {
        "aliases": ["Fyodor Pavlovich", "Fyodor", "老卡拉马佐夫", "费奥多尔"],
        "identity": "The father of the Karamazov brothers; vulgar, greedy, sensual, theatrical, and morally degraded.",
        "core_conflict": "He embodies corruption and irresponsibility, becoming the central object of hatred, inheritance conflict, and suspected parricide.",
        "keywords": ["father", "sensuality", "money", "parricide", "degradation"],
    },
    "Smerdyakov / 斯麦尔佳科夫": {
        "aliases": ["Smerdyakov", "Pavel", "斯麦尔佳科夫"],
        "identity": "A servant in Fyodor Pavlovich's house; resentful, calculating, and central to the murder plot.",
        "core_conflict": "He internalizes humiliation and resentment, then turns ideas about moral permission into destructive action.",
        "keywords": ["servant", "resentment", "murder", "responsibility", "Ivan"],
    },
    "Grushenka / 格鲁申卡": {
        "aliases": ["Grushenka", "Agrafena", "格鲁申卡"],
        "identity": "A charismatic woman desired by Dmitri and Fyodor Pavlovich; more complex than a simple temptress figure.",
        "core_conflict": "She is caught between wounded pride, desire, manipulation, revenge, and possible transformation.",
        "keywords": ["desire", "wounded pride", "Dmitri", "Fyodor", "transformation"],
    },
    "Katerina / 卡捷琳娜": {
        "aliases": ["Katerina", "Katya", "Katerina Ivanovna", "卡捷琳娜"],
        "identity": "Dmitri's former fiancée; proud, morally intense, indebted, wounded, and emotionally bound to both Dmitri and Ivan.",
        "core_conflict": "She confuses sacrifice, pride, love, revenge, and moral superiority.",
        "keywords": ["pride", "debt", "sacrifice", "Dmitri", "Ivan"],
    },
    "Zosima / 佐西马长老": {
        "aliases": ["Zosima", "Father Zosima", "Elder Zosima", "佐西马"],
        "identity": "A spiritual elder and Alyosha's mentor; teaches active love, humility, and universal responsibility.",
        "core_conflict": "His teachings answer moral decay and suffering, but are challenged by scandal, skepticism, and bodily mortality.",
        "keywords": ["active love", "faith", "humility", "responsibility", "Alyosha"],
    },
    "Ilyusha / 伊柳沙": {
        "aliases": ["Ilyusha", "Ilyushechka", "Ilyusha Snegiryov", "伊柳沙"],
        "identity": "A suffering child who draws together themes of innocence, cruelty, compassion, and moral education.",
        "core_conflict": "His suffering forces the novel to ask what love, guilt, and responsibility mean in relation to children.",
        "keywords": ["children", "suffering", "innocence", "Alyosha", "schoolboys"],
    },
}

THEMES = {
    "Faith and Doubt / 信仰与怀疑": {
        "description": "The novel stages the conflict between religious faith, skeptical reason, rebellion against God, and active love.",
        "keywords": ["God", "faith", "doubt", "atheism", "Zosima", "Alyosha", "Ivan"],
    },
    "Parricide and Responsibility / 弑父与责任": {
        "description": "The murder plot is not only legal but moral: who desired the father's death, who acted, and who is responsible?",
        "keywords": ["father", "murder", "parricide", "responsibility", "Dmitri", "Ivan", "Smerdyakov"],
    },
    "Suffering of Children / 儿童苦难": {
        "description": "The suffering of innocent children is central to Ivan's rebellion and to the novel's moral test of faith and love.",
        "keywords": ["children", "child", "Ilyusha", "suffering", "innocent", "tears"],
    },
    "Sensuality and Desire / 欲望与堕落": {
        "description": "The Karamazov world is driven by money, erotic rivalry, humiliation, and bodily appetite.",
        "keywords": ["sensual", "desire", "money", "jealousy", "Grushenka", "Dmitri", "Fyodor"],
    },
    "Pride and Humiliation / 骄傲与羞辱": {
        "description": "Love is often mixed with pride, debt, revenge, public moral performance, and humiliation.",
        "keywords": ["pride", "humiliation", "Katerina", "Grushenka", "Dmitri", "Ivan"],
    },
    "Active Love / 积极的爱": {
        "description": "Zosima and Alyosha represent concrete active love rather than abstract doctrine or theatrical morality.",
        "keywords": ["active love", "love", "Zosima", "Alyosha", "responsibility", "humility"],
    },
}

RELATIONSHIPS = [
    ("Fyodor Pavlovich / 老卡拉马佐夫", "Dmitri / 德米特里", "father / son; money and rivalry", 1),
    ("Fyodor Pavlovich / 老卡拉马佐夫", "Ivan / 伊万", "father / son; contempt and distance", 1),
    ("Fyodor Pavlovich / 老卡拉马佐夫", "Alyosha / 阿廖沙", "father / son; moral contrast", 1),
    ("Dmitri / 德米特里", "Ivan / 伊万", "brothers; judgment and rivalry", 1),
    ("Dmitri / 德米特里", "Alyosha / 阿廖沙", "brothers; confession and trust", 1),
    ("Ivan / 伊万", "Alyosha / 阿廖沙", "brothers; faith vs doubt", 1),
    ("Dmitri / 德米特里", "Grushenka / 格鲁申卡", "passionate love / jealousy", 1),
    ("Fyodor Pavlovich / 老卡拉马佐夫", "Grushenka / 格鲁申卡", "desire / rivalry with son", 1),
    ("Dmitri / 德米特里", "Katerina / 卡捷琳娜", "engagement, debt, wounded pride", 2),
    ("Ivan / 伊万", "Katerina / 卡捷琳娜", "intellectual and emotional tension", 3),
    ("Alyosha / 阿廖沙", "Zosima / 佐西马长老", "disciple / spiritual elder", 1),
    ("Ivan / 伊万", "Smerdyakov / 斯麦尔佳科夫", "ideas, influence, moral guilt", 5),
    ("Fyodor Pavlovich / 老卡拉马佐夫", "Smerdyakov / 斯麦尔佳科夫", "master / servant; hidden paternity shadow", 2),
    ("Alyosha / 阿廖沙", "Ilyusha / 伊柳沙", "compassion and moral education", 4),
]

ROMAN_MAP = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,
    "XII": 12,
}


# ============================================================
# 内置演示章节
# 这部分不需要联网，所以网页能秒开。
# 用户之后可以手动加载 Gutenberg 全书。
# ============================================================

DEMO_SECTIONS = [
    {
        "title": "Demo 01｜人物与主题入口",
        "book_number": 1,
        "source": "Built-in demo notes",
        "text": """
This is a built-in demo section. It is not the full novel text.

The Brothers Karamazov is organized around a family whose emotional, moral, and philosophical conflicts become increasingly destructive. Fyodor Pavlovich is the degraded father. Dmitri is passionate and guilty. Ivan is intellectually rebellious and tormented by questions of God, evil, and responsibility. Alyosha is spiritually oriented and connected with Zosima's teaching of active love.

Core reading questions:
- What does fatherhood mean in a corrupt family?
- Can faith answer the suffering of innocent children?
- Are people responsible only for actions, or also for ideas and wishes?
- Can active love survive humiliation, desire, and moral chaos?
""",
    },
    {
        "title": "Demo 02｜Ivan / 伊万：信仰、怀疑与儿童苦难",
        "book_number": 5,
        "source": "Built-in demo notes",
        "text": """
This is a built-in demo note for Ivan.

Ivan's conflict is not simple atheism. His rebellion grows from the problem of innocent suffering, especially the suffering of children. He cannot accept a harmony or salvation that seems to require innocent pain. This makes his intellectual position morally serious, but also dangerous, because ideas about rejection, permission, and responsibility begin to affect the lives of others.

Important themes:
- faith and doubt
- innocent suffering
- responsibility for ideas
- rebellion against God
""",
    },
    {
        "title": "Demo 03｜Dmitri / 德米特里：欲望、罪感与重生",
        "book_number": 8,
        "source": "Built-in demo notes",
        "text": """
This is a built-in demo note for Dmitri.

Dmitri is driven by passion, jealousy, money conflict, humiliation, and desire. Yet he is not only a sensual or violent character. He repeatedly shows a need to confess, suffer, and be morally reborn. His tragedy is that his emotional truth, impulsive actions, and reputation all make him appear guilty even when the deeper moral problem is more complicated.

Important themes:
- desire and guilt
- father-son rivalry
- honor and humiliation
- punishment and redemption
""",
    },
    {
        "title": "Demo 04｜Zosima and Alyosha / 积极的爱",
        "book_number": 6,
        "source": "Built-in demo notes",
        "text": """
This is a built-in demo note for Zosima and Alyosha.

Zosima teaches active love: not abstract love for humanity, but concrete responsibility toward real people. Alyosha carries this teaching into the chaotic Karamazov world. The novel tests whether active love can respond to suffering, doubt, cruelty, family corruption, and the breakdown of moral order.

Important themes:
- active love
- humility
- universal responsibility
- spiritual witness
""",
    },
]


# ============================================================
# Session state
# ============================================================

def init_state():
    if "model_name" not in st.session_state:
        st.session_state.model_name = DEFAULT_MODEL

    if "history" not in st.session_state:
        st.session_state.history = []

    if "extra_chunks" not in st.session_state:
        st.session_state.extra_chunks = []

    if "sections" not in st.session_state:
        st.session_state.sections = DEMO_SECTIONS

    if "book_loaded" not in st.session_state:
        st.session_state.book_loaded = False

    if "load_message" not in st.session_state:
        st.session_state.load_message = "当前使用内置演示资料。网页不会在启动时联网，所以不会卡死。"


init_state()


# ============================================================
# 工具函数
# ============================================================

def safe_join(items, sep="、"):
    if not items:
        return "暂无资料"
    return sep.join(str(x) for x in items)


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def roman_to_int(roman):
    return ROMAN_MAP.get(roman.upper().strip("."), 0)


def escape_dot(text):
    return str(text).replace('"', '\\"')


def add_history(page, section, task, question, answer):
    st.session_state.history.insert(
        0,
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "page": page,
            "section": section,
            "task": task,
            "question": question,
            "answer": answer,
        },
    )
    st.session_state.history = st.session_state.history[:30]


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

    for name, data in THEMES.items():
        for keyword in data["keywords"]:
            if keyword.lower() in lower:
                found.append(name)
                break

    return found


# ============================================================
# Gutenberg 下载与解析：只在用户点击按钮后运行
# ============================================================

@st.cache_data(show_spinner=False)
def fetch_gutenberg_text():
    urls = [
        "https://www.gutenberg.org/cache/epub/28054/pg28054.txt",
        "https://www.gutenberg.org/files/28054/28054-0.txt",
    ]

    headers = {"User-Agent": "karamazov-interactive-archive"}

    last_error = ""

    for url in urls:
        try:
            response = requests.get(url, timeout=20, headers=headers)
            if response.status_code == 200 and "Karamazov" in response.text:
                return response.text, f"成功读取：{url}"
            last_error = f"HTTP {response.status_code} from {url}"
        except Exception as e:
            last_error = str(e)

    return "", f"读取失败：{last_error}"


def strip_boilerplate(text):
    if not text:
        return ""

    start = re.search(r"\*\*\*\s*START OF .*?EBOOK.*?\*\*\*", text, re.I | re.S)
    end = re.search(r"\*\*\*\s*END OF .*?EBOOK.*?\*\*\*", text, re.I | re.S)

    if start:
        text = text[start.end():]

    if end:
        text = text[:end.start()]

    return text.strip()


@st.cache_data(show_spinner=False)
def parse_sections(raw_text):
    text = strip_boilerplate(raw_text)

    if not text:
        return []

    lines = text.splitlines()

    current_part = ""
    current_book = ""
    current_book_number = 0
    current_chapter = ""
    current_lines = []
    sections = []

    def flush():
        nonlocal current_lines, current_chapter, current_book, current_part, current_book_number

        content = "\n".join(current_lines).strip()

        if current_chapter and content:
            title_parts = []
            if current_part:
                title_parts.append(current_part)
            if current_book:
                title_parts.append(current_book)
            title_parts.append(current_chapter)

            sections.append(
                {
                    "title": " | ".join(title_parts),
                    "book_number": current_book_number,
                    "source": "Project Gutenberg eBook #28054",
                    "text": content,
                }
            )

        current_lines = []

    for line in lines:
        s = line.strip()

        part_match = re.match(r"^PART\s+([IVX]+)\.?\s*$", s, re.I)
        book_match = re.match(r"^Book\s+([IVX]+)\.\s+(.+)$", s, re.I)
        chapter_match = re.match(r"^Chapter\s+([IVX]+)\.\s+(.+)$", s, re.I)

        if part_match:
            current_part = s
            continue

        if book_match:
            current_book = s
            current_book_number = roman_to_int(book_match.group(1))
            continue

        if chapter_match:
            flush()
            current_chapter = s
            continue

        if current_chapter:
            current_lines.append(line)

    flush()

    if not sections:
        sections = [
            {
                "title": "Full Text Sample",
                "book_number": 1,
                "source": "Project Gutenberg eBook #28054",
                "text": text[:12000],
            }
        ]

    return sections


@st.cache_data(show_spinner=False)
def make_chunks(sections):
    chunks = []

    for section_index, section in enumerate(sections):
        text = section["text"]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

        current = ""
        chunk_number = 1

        def add_chunk(content):
            nonlocal chunk_number

            if not content.strip():
                return

            chunk_id = f"K-{section_index + 1:03d}-{chunk_number:02d}"
            chunk_number += 1

            chunks.append(
                {
                    "id": chunk_id,
                    "section_index": section_index,
                    "section_title": section["title"],
                    "book_number": section.get("book_number", 0),
                    "source": section.get("source", ""),
                    "content": content.strip(),
                    "characters": detect_characters(content),
                    "themes": detect_themes(content),
                }
            )

        for para in paragraphs:
            if len(current) + len(para) <= 2400:
                current = current + "\n\n" + para if current else para
            else:
                add_chunk(current)
                current = current[-250:] + "\n\n" + para

        add_chunk(current)

    return chunks


def load_full_book():
    raw_text, message = fetch_gutenberg_text()

    if not raw_text:
        st.session_state.book_loaded = False
        st.session_state.load_message = message
        return False, message

    sections = parse_sections(raw_text)

    if not sections:
        st.session_state.book_loaded = False
        st.session_state.load_message = "文本读取到了，但章节解析失败。仍保留内置演示资料。"
        return False, st.session_state.load_message

    st.session_state.sections = sections
    st.session_state.book_loaded = True
    st.session_state.load_message = f"已加载完整英文公版文本，共 {len(sections)} 个章节。"
    return True, st.session_state.load_message


# ============================================================
# 检索
# ============================================================

def expand_query(query):
    q = query or ""

    mapping = {
        "阿廖沙": "Alyosha Alexey faith active love Zosima",
        "德米特里": "Dmitri Mitya passion Grushenka guilt money",
        "米佳": "Dmitri Mitya passion Grushenka guilt money",
        "伊万": "Ivan rebellion God suffering responsibility Grand Inquisitor",
        "老卡拉马佐夫": "Fyodor Pavlovich father murder money sensuality",
        "斯麦尔佳科夫": "Smerdyakov Ivan murder responsibility servant",
        "格鲁申卡": "Grushenka Dmitri Fyodor desire",
        "卡捷琳娜": "Katerina Katya pride debt Dmitri Ivan",
        "佐西马": "Zosima active love faith Alyosha",
        "大审判官": "Grand Inquisitor Ivan Christ freedom miracle authority",
        "信仰": "faith God Zosima Alyosha",
        "怀疑": "doubt atheism Ivan suffering",
        "弑父": "parricide father murder Dmitri Ivan Smerdyakov",
        "儿童": "children child Ilyusha suffering",
        "苦难": "suffering children Ivan rebellion",
        "责任": "responsibility guilt Ivan Smerdyakov",
        "欲望": "desire sensuality Dmitri Grushenka Fyodor",
        "审判": "trial court Dmitri evidence",
    }

    for key, value in mapping.items():
        if key in q:
            q += " " + value

    return q


def visible_chunks(chunks, current_index, spoiler_free):
    if not spoiler_free:
        return chunks
    return [c for c in chunks if c["section_index"] <= current_index]


def retrieve_chunks(chunks, query, current_index, spoiler_free, top_k=6):
    pool = visible_chunks(chunks, current_index, spoiler_free)

    if not pool:
        return []

    q = normalize_text(expand_query(query)).lower()

    if not q:
        current = [c for c in pool if c["section_index"] == current_index]
        return current[:top_k] if current else pool[:top_k]

    terms = [x for x in re.split(r"[\s,，。；;:：!?？、]+", q) if len(x) >= 2]
    scored = []

    for chunk in pool:
        text = normalize_text(
            chunk["id"]
            + " "
            + chunk["section_title"]
            + " "
            + chunk["content"]
            + " "
            + " ".join(chunk["characters"])
            + " "
            + " ".join(chunk["themes"])
        ).lower()

        score = 0

        if chunk["section_index"] == current_index:
            score += 4

        for term in terms:
            if term in text:
                score += 5

        for character in chunk["characters"]:
            if character.lower() in q:
                score += 8

        for theme in chunk["themes"]:
            if theme.lower() in q:
                score += 8

        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    result = [chunk for score, chunk in scored if score > 0][:top_k]

    if not result:
        current = [c for c in pool if c["section_index"] == current_index]
        result = current[:top_k] if current else pool[:top_k]

    return result


def format_chunks(chunks):
    if not chunks:
        return "No evidence chunks found."

    parts = []

    for chunk in chunks:
        parts.append(
            f"""
[{chunk["id"]}] {chunk["section_title"]}
Source: {chunk.get("source", "")}
Characters: {safe_join(chunk["characters"])}
Themes: {safe_join(chunk["themes"])}
Text:
{chunk["content"]}
"""
        )

    return "\n".join(parts)


def display_chunks(chunks):
    if not chunks:
        st.write("暂无检索到的证据片段。")
        return

    for chunk in chunks:
        with st.expander(f"[{chunk['id']}] {chunk['section_title']}"):
            st.markdown("**来源**")
            st.write(chunk.get("source", "未标明"))

            st.markdown("**人物**")
            st.write(safe_join(chunk["characters"]))

            st.markdown("**主题**")
            st.write(safe_join(chunk["themes"]))

            st.markdown("**文本片段**")
            st.write(chunk["content"])


# ============================================================
# AI
# ============================================================

def call_ai(system_prompt, user_prompt, temperature=0.35):
    if client is None:
        return "没有读取到 OpenAI API key。请在 Streamlit Cloud 的 Secrets 里设置 OPENAI_API_KEY。"

    response = client.chat.completions.create(
        model=st.session_state.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content


def reading_ai(section, evidence, task, question, spoiler_free):
    system_prompt = f"""
You are an interactive literary reading assistant for Dostoevsky's The Brothers Karamazov.

Rules:
1. Base your answer primarily on the provided evidence chunks.
2. Do not pretend to know text not provided.
3. If spoiler-free mode is ON, do not reveal later plot events.
4. Cite evidence chunk IDs like [K-003-01].
5. Answer in Chinese.
6. Be literary, precise, and useful.

Spoiler-free mode: {"ON" if spoiler_free else "OFF"}
"""

    user_prompt = f"""
Current section:
{section["title"]}

Task:
{task}

User question:
{question if question.strip() else "No extra question."}

Evidence:
{format_chunks(evidence)}

Please answer in Chinese.
"""

    return call_ai(system_prompt, user_prompt)


def character_ai(character_name, data, evidence, question):
    system_prompt = """
You are a character archive assistant for The Brothers Karamazov.
Use the character profile and evidence chunks.
Cite evidence IDs.
Answer in Chinese.
"""

    user_prompt = f"""
Character:
{character_name}

Identity:
{data["identity"]}

Core conflict:
{data["core_conflict"]}

Keywords:
{safe_join(data["keywords"])}

Evidence:
{format_chunks(evidence)}

Question:
{question if question.strip() else "Generate a character analysis."}
"""

    return call_ai(system_prompt, user_prompt)


def theme_ai(theme_name, data, evidence, question):
    system_prompt = """
You are a theme analyst for The Brothers Karamazov.
Use the theme profile and evidence chunks.
Cite evidence IDs.
Answer in Chinese.
"""

    user_prompt = f"""
Theme:
{theme_name}

Description:
{data["description"]}

Keywords:
{safe_join(data["keywords"])}

Evidence:
{format_chunks(evidence)}

Question:
{question if question.strip() else "Explain this theme based on the evidence."}
"""

    return call_ai(system_prompt, user_prompt)


def evidence_ai(evidence, question):
    system_prompt = """
Answer only from the provided evidence chunks.
If evidence is insufficient, say so.
Cite chunk IDs.
Answer in Chinese.
"""

    user_prompt = f"""
Evidence:
{format_chunks(evidence)}

Question:
{question if question.strip() else "Explain what these chunks show."}
"""

    return call_ai(system_prompt, user_prompt)


# ============================================================
# 关系图
# ============================================================

def build_relationship_dot(current_book, spoiler_free, selected_character):
    edges = []

    for source, target, relation, reveal_book in RELATIONSHIPS:
        if spoiler_free and reveal_book > current_book:
            continue

        if selected_character != "全部人物":
            if source != selected_character and target != selected_character:
                continue

        edges.append((source, target, relation))

    nodes = set()

    for source, target, _ in edges:
        nodes.add(source)
        nodes.add(target)

    if selected_character != "全部人物":
        nodes.add(selected_character)

    dot = [
        "graph G {",
        "rankdir=LR;",
        'bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fillcolor="#F7F7F7", fontname="Microsoft YaHei"];',
        'edge [fontname="Microsoft YaHei", fontsize=10];',
    ]

    for node in nodes:
        dot.append(f'"{escape_dot(node)}";')

    for source, target, relation in edges:
        dot.append(f'"{escape_dot(source)}" -- "{escape_dot(target)}" [label="{escape_dot(relation)}"];')

    dot.append("}")

    return "\n".join(dot)


def relationship_text(current_book, spoiler_free, selected_character):
    lines = []

    for source, target, relation, reveal_book in RELATIONSHIPS:
        if spoiler_free and reveal_book > current_book:
            continue

        if selected_character != "全部人物":
            if source != selected_character and target != selected_character:
                continue

        lines.append(f"- {source} — {target}: {relation}")

    return "\n".join(lines) if lines else "暂无可见关系。"


# ============================================================
# 主界面
# ============================================================

st.title("📚《卡拉马佐夫兄弟》AI 互动文学档案馆")
st.caption("The Brothers Karamazov Interactive Literary Archive v1.1 lazy-load")

with st.sidebar:
    st.header("导航")

    page = st.radio(
        "选择页面",
        [
            "首页 / 文本加载",
            "阅读助手",
            "人物档案",
            "人物关系图",
            "主题面板",
            "证据检索",
            "上传/扩展资料",
            "分析历史/导出",
            "项目说明",
        ],
    )

    st.divider()

    st.header("模型设置")
    st.session_state.model_name = st.text_input("模型名称", value=st.session_state.model_name)

    st.divider()

    st.header("文本状态")
    if st.session_state.book_loaded:
        st.success("已加载完整英文文本")
    else:
        st.warning("当前为内置演示资料")
    st.caption(st.session_state.load_message)


sections = st.session_state.sections
chunks = make_chunks(sections)
all_chunks = chunks + st.session_state.extra_chunks
section_titles = [section["title"] for section in sections]


# ============================================================
# Page: Home / Load
# ============================================================

if page == "首页 / 文本加载":
    st.subheader("首页 / 文本加载")

    st.write("这个版本不会在网页启动时自动联网下载整本书，所以页面应该能很快打开。")

    if st.session_state.book_loaded:
        st.success(f"完整文本已加载。当前共有 {len(sections)} 个章节，{len(chunks)} 个检索片段。")
    else:
        st.warning("当前使用内置演示资料。你可以先测试 AI 功能，也可以手动加载 Project Gutenberg 英文公版全文。")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("加载 Project Gutenberg 英文全文", type="primary"):
            with st.spinner("正在下载并解析文本，可能需要几十秒..."):
                ok, message = load_full_book()
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
                st.info("加载失败也没关系，内置演示资料仍然可用。")

    with col2:
        if st.button("恢复内置演示资料"):
            st.session_state.sections = DEMO_SECTIONS
            st.session_state.book_loaded = False
            st.session_state.load_message = "已恢复内置演示资料。"
            st.rerun()

    st.divider()

    st.markdown("### 当前资料状态")
    st.write(f"章节数量：{len(sections)}")
    st.write(f"检索片段数量：{len(chunks)}")

    st.markdown("### 当前章节列表预览")
    for s in sections[:12]:
        st.write(f"- {s['title']}")


# ============================================================
# Page: Reading Assistant
# ============================================================

elif page == "阅读助手":
    with st.sidebar:
        st.header("阅读控制")

        selected_title = st.selectbox("选择章节", section_titles)
        section_index = section_titles.index(selected_title)
        current_section = sections[section_index]

        spoiler_free = st.checkbox("不剧透模式", value=True)

        task = st.radio(
            "选择功能",
            ["章节摘要", "人物心理分析", "思想/主题分析", "伏笔/线索提醒", "自由提问"],
        )

        question = st.text_area("具体问题 / 需求（可选）", height=140)
        top_k = st.slider("证据片段数量", 3, 10, 6)
        run_button = st.button("开始 AI 分析")

    query = f"{selected_title} {task} {question} {current_section['text'][:800]}"
    evidence = retrieve_chunks(all_chunks, query, section_index, spoiler_free, top_k)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"当前章节：{selected_title}")

        st.markdown("### 章节预览")
        preview = current_section["text"][:2600]
        st.write(preview + ("..." if len(current_section["text"]) > 2600 else ""))

        st.markdown("### 自动检索到的证据片段")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 分析区")

        if run_button:
            with st.spinner("AI 正在分析..."):
                try:
                    answer = reading_ai(current_section, evidence, task, question, spoiler_free)
                    st.write(answer)
                    add_history("阅读助手", selected_title, task, question, answer)
                except Exception as e:
                    st.error(f"出错了：{e}")
        else:
            st.info("请选择章节和功能，然后点击“开始 AI 分析”。")


# ============================================================
# Page: Character Archive
# ============================================================

elif page == "人物档案":
    with st.sidebar:
        st.header("人物控制")

        selected_title = st.selectbox("当前阅读进度", section_titles)
        section_index = section_titles.index(selected_title)

        character_name = st.selectbox("选择人物", list(CHARACTERS.keys()))
        question = st.text_area("关于这个人物的问题（可选）", height=140)
        run_button = st.button("生成人物分析")

    data = CHARACTERS[character_name]
    query = f"{character_name} {' '.join(data['aliases'])} {question}"
    evidence = retrieve_chunks(all_chunks, query, section_index, True, 7)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"人物档案：{character_name}")

        st.markdown("### 身份")
        st.write(data["identity"])

        st.markdown("### 核心困境")
        st.write(data["core_conflict"])

        st.markdown("### 关键词")
        st.write(safe_join(data["keywords"]))

        st.markdown("### 相关证据片段")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 人物分析区")

        if run_button:
            with st.spinner("AI 正在分析人物..."):
                try:
                    answer = character_ai(character_name, data, evidence, question)
                    st.write(answer)
                    add_history("人物档案", selected_title, character_name, question, answer)
                except Exception as e:
                    st.error(f"出错了：{e}")
        else:
            st.info("选择人物后点击“生成人物分析”。")


# ============================================================
# Page: Relationship Graph
# ============================================================

elif page == "人物关系图":
    with st.sidebar:
        st.header("关系图控制")

        selected_title = st.selectbox("当前阅读进度", section_titles)
        section_index = section_titles.index(selected_title)
        current_book = sections[section_index].get("book_number", 1)

        spoiler_free = st.checkbox("不剧透模式", value=True)
        selected_character = st.selectbox("聚焦人物", ["全部人物"] + list(CHARACTERS.keys()))

        question = st.text_area("关于关系图的问题（可选）", height=140)
        run_button = st.button("AI 解读关系图")

    st.subheader("人物关系图")

    dot = build_relationship_dot(current_book, spoiler_free, selected_character)
    st.graphviz_chart(dot, use_container_width=True)

    rel_text = relationship_text(current_book, spoiler_free, selected_character)
    evidence = retrieve_chunks(all_chunks, f"{selected_character} {question} {rel_text}", section_index, spoiler_free, 6)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 当前可见关系")
        st.write(rel_text)

        st.markdown("### 相关证据片段")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 关系分析区")

        if run_button:
            with st.spinner("AI 正在分析关系图..."):
                try:
                    answer = evidence_ai(evidence, question or rel_text)
                    st.write(answer)
                    add_history("人物关系图", selected_title, selected_character, question, answer)
                except Exception as e:
                    st.error(f"出错了：{e}")
        else:
            st.info("选择阅读进度和人物后，可以点击“AI 解读关系图”。")


# ============================================================
# Page: Theme Panel
# ============================================================

elif page == "主题面板":
    with st.sidebar:
        st.header("主题控制")

        selected_title = st.selectbox("当前阅读进度", section_titles)
        section_index = section_titles.index(selected_title)

        theme_name = st.selectbox("选择主题", list(THEMES.keys()))
        question = st.text_area("关于主题的问题（可选）", height=140)
        run_button = st.button("AI 解读主题")

    data = THEMES[theme_name]
    query = f"{theme_name} {' '.join(data['keywords'])} {question}"
    evidence = retrieve_chunks(all_chunks, query, section_index, True, 8)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(theme_name)
        st.write(data["description"])

        st.markdown("### 关键词")
        st.write(safe_join(data["keywords"]))

        st.markdown("### 相关证据片段")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 主题分析区")

        if run_button:
            with st.spinner("AI 正在分析主题..."):
                try:
                    answer = theme_ai(theme_name, data, evidence, question)
                    st.write(answer)
                    add_history("主题面板", selected_title, theme_name, question, answer)
                except Exception as e:
                    st.error(f"出错了：{e}")
        else:
            st.info("选择主题后点击“AI 解读主题”。")


# ============================================================
# Page: Evidence Search
# ============================================================

elif page == "证据检索":
    with st.sidebar:
        st.header("证据检索控制")

        selected_title = st.selectbox("当前阅读进度", section_titles)
        section_index = section_titles.index(selected_title)

        spoiler_free = st.checkbox("不剧透模式", value=True)
        query = st.text_area("检索问题 / 关键词", height=120)
        top_k = st.slider("返回片段数量", 3, 12, 7)

        run_button = st.button("检索并让 AI 解读")

    evidence = retrieve_chunks(all_chunks, query, section_index, spoiler_free, top_k)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("检索到的证据片段")
        display_chunks(evidence)

    with col2:
        st.subheader("AI 证据解读")

        if run_button:
            with st.spinner("AI 正在解读证据..."):
                try:
                    answer = evidence_ai(evidence, query)
                    st.write(answer)
                    add_history("证据检索", selected_title, "证据解读", query, answer)
                except Exception as e:
                    st.error(f"出错了：{e}")
        else:
            st.info("输入关键词后点击“检索并让 AI 解读”。")


# ============================================================
# Page: Upload
# ============================================================

elif page == "上传/扩展资料":
    st.subheader("上传 / 扩展资料")

    st.info("这里上传的资料只保存在当前会话里。重启后会消失。")

    selected_title = st.selectbox("资料属于哪个阅读位置？", section_titles)
    section_index = section_titles.index(selected_title)

    title_prefix = st.text_input("片段标题前缀", value="用户补充片段")
    raw_characters = st.text_input("相关人物，用英文逗号分隔", value="")
    raw_themes = st.text_input("相关主题，用英文逗号分隔", value="")

    characters = [x.strip() for x in raw_characters.split(",") if x.strip()]
    themes = [x.strip() for x in raw_themes.split(",") if x.strip()]

    text = st.text_area("粘贴你的笔记 / 摘录 / 分析", height=260)

    if st.button("加入资料库"):
        pieces = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        timestamp = datetime.now().strftime("%H%M%S")

        new_chunks = []

        for i, piece in enumerate(pieces):
            new_chunks.append(
                {
                    "id": f"U-{timestamp}-{i + 1:03d}",
                    "section_index": section_index,
                    "section_title": selected_title,
                    "book_number": sections[section_index].get("book_number", 1),
                    "source": "User upload",
                    "content": piece,
                    "characters": characters if characters else detect_characters(piece),
                    "themes": themes if themes else detect_themes(piece),
                }
            )

        st.session_state.extra_chunks.extend(new_chunks)
        st.success(f"已加入 {len(new_chunks)} 个片段。")

    st.markdown("### 当前补充片段")
    display_chunks(st.session_state.extra_chunks[:10])


# ============================================================
# Page: History
# ============================================================

elif page == "分析历史/导出":
    st.subheader("分析历史 / 导出")

    if not st.session_state.history:
        st.info("当前还没有分析历史。")
    else:
        for i, item in enumerate(st.session_state.history):
            with st.expander(f"{i + 1}. {item['time']}｜{item['page']}｜{item['section']}｜{item['task']}"):
                st.markdown("**问题 / 需求**")
                st.write(item["question"])

                st.markdown("**AI 回答**")
                st.write(item["answer"])

        export_json = json.dumps(st.session_state.history, ensure_ascii=False, indent=2)

        st.download_button(
            "下载分析历史 JSON",
            data=export_json,
            file_name="karamazov_analysis_history.json",
            mime="application/json",
        )

    if st.button("清空分析历史"):
        st.session_state.history = []
        st.rerun()


# ============================================================
# Page: Project Intro
# ============================================================

elif page == "项目说明":
    st.subheader("项目说明")

    st.markdown(
        """
这是一个基于 **Streamlit + OpenAI API + Project Gutenberg 英文公版文本** 的《卡拉马佐夫兄弟》互动文学档案馆。

这个版本是 **v1.1 lazy-load 稳定版**：

- 启动时不会自动下载整本书；
- 页面会先打开；
- 你可以手动点击“加载 Project Gutenberg 英文全文”；
- 如果全文加载失败，内置演示资料仍然可以使用；
- AI 回答默认为中文；
- 底层证据片段为英文或你的补充资料。

功能包括：

- 首页 / 文本加载
- 阅读助手
- 人物档案
- 人物关系图
- 主题面板
- 证据检索
- 上传补充资料
- 分析历史导出
"""
    )

    st.markdown("### Streamlit Cloud Secrets")

    st.code(
        'OPENAI_API_KEY = "你的真实 API key"',
        language="toml",
    )

    st.warning("不要把 API key 上传到 GitHub。别人使用你的网页时，会消耗你的 API 额度。")
