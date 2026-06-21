import os
import re
import io
import json
import zipfile
import posixpath
import html as html_lib
import xml.etree.ElementTree as ET
from datetime import datetime

import streamlit as st
from openai import OpenAI


# ============================================================
# 页面设置
# ============================================================

st.set_page_config(
    page_title="Karamazov Interactive Archive",
    page_icon="📚",
    layout="wide",
)


# ============================================================
# OpenAI API 设置
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
# 基础资料
# ============================================================

DEFAULT_MODEL = "gpt-4.1-mini"

CHARACTERS = {
    "Alyosha / 阿廖沙": {
        "aliases": ["Alyosha", "Alexey", "Alexei", "阿廖沙", "阿列克谢"],
        "identity": "The youngest Karamazov brother; spiritually oriented, close to Zosima, often a listener and moral witness.",
        "core_conflict": "He wants to believe in active love and faith, but he is surrounded by corruption, suffering, sensuality, and intellectual rebellion.",
        "keywords": ["faith", "active love", "compassion", "witness", "Zosima", "信仰", "爱", "佐西马"],
    },
    "Dmitri / 德米特里": {
        "aliases": ["Dmitri", "Mitya", "Mitka", "德米特里", "米佳"],
        "identity": "The eldest Karamazov brother; passionate, impulsive, sensual, and caught in conflict over money, love, and guilt.",
        "core_conflict": "He is torn between sensual excess, jealousy, pride, guilt, and a desire for moral rebirth.",
        "keywords": ["passion", "guilt", "jealousy", "honor", "Grushenka", "欲望", "罪感", "格鲁申卡"],
    },
    "Ivan / 伊万": {
        "aliases": ["Ivan", "Vanya", "伊万"],
        "identity": "The intellectual brother; skeptical, brilliant, tormented by God, evil, freedom, and responsibility.",
        "core_conflict": "He rejects easy faith because of innocent suffering, yet cannot escape moral responsibility for ideas and consequences.",
        "keywords": ["reason", "atheism", "rebellion", "suffering", "responsibility", "理性", "无神论", "反抗", "苦难", "责任"],
    },
    "Fyodor Pavlovich / 老卡拉马佐夫": {
        "aliases": ["Fyodor Pavlovich", "Fyodor", "老卡拉马佐夫", "费奥多尔", "费尧多尔"],
        "identity": "The father of the Karamazov brothers; vulgar, greedy, sensual, theatrical, and morally degraded.",
        "core_conflict": "He embodies corruption and irresponsibility, becoming the central object of hatred, inheritance conflict, and suspected parricide.",
        "keywords": ["father", "sensuality", "money", "parricide", "degradation", "父亲", "弑父", "堕落", "金钱"],
    },
    "Smerdyakov / 斯麦尔佳科夫": {
        "aliases": ["Smerdyakov", "Pavel", "斯麦尔佳科夫", "斯乜尔加科夫"],
        "identity": "A servant in Fyodor Pavlovich's house; resentful, calculating, and central to the murder plot.",
        "core_conflict": "He internalizes humiliation and resentment, then turns ideas about moral permission into destructive action.",
        "keywords": ["servant", "resentment", "murder", "responsibility", "Ivan", "仆人", "怨恨", "谋杀", "伊万"],
    },
    "Grushenka / 格鲁申卡": {
        "aliases": ["Grushenka", "Agrafena", "格鲁申卡", "格露莘卡"],
        "identity": "A charismatic woman desired by Dmitri and Fyodor Pavlovich; more complex than a simple temptress figure.",
        "core_conflict": "She is caught between wounded pride, desire, manipulation, revenge, and possible transformation.",
        "keywords": ["desire", "wounded pride", "Dmitri", "Fyodor", "transformation", "欲望", "骄傲", "德米特里"],
    },
    "Katerina / 卡捷琳娜": {
        "aliases": ["Katerina", "Katya", "Katerina Ivanovna", "卡捷琳娜", "卡嘉"],
        "identity": "Dmitri's former fiancée; proud, morally intense, indebted, wounded, and emotionally bound to both Dmitri and Ivan.",
        "core_conflict": "She confuses sacrifice, pride, love, revenge, and moral superiority.",
        "keywords": ["pride", "debt", "sacrifice", "Dmitri", "Ivan", "骄傲", "牺牲", "债", "伊万"],
    },
    "Zosima / 佐西马长老": {
        "aliases": ["Zosima", "Father Zosima", "Elder Zosima", "佐西马", "长老"],
        "identity": "A spiritual elder and Alyosha's mentor; teaches active love, humility, and universal responsibility.",
        "core_conflict": "His teachings answer moral decay and suffering, but are challenged by scandal, skepticism, and bodily mortality.",
        "keywords": ["active love", "faith", "humility", "responsibility", "Alyosha", "积极的爱", "信仰", "谦卑"],
    },
    "Ilyusha / 伊柳沙": {
        "aliases": ["Ilyusha", "Ilyushechka", "Ilyusha Snegiryov", "伊柳沙"],
        "identity": "A suffering child who draws together themes of innocence, cruelty, compassion, and moral education.",
        "core_conflict": "His suffering forces the novel to ask what love, guilt, and responsibility mean in relation to children.",
        "keywords": ["children", "suffering", "innocence", "Alyosha", "schoolboys", "儿童", "苦难", "无辜"],
    },
}

THEMES = {
    "Faith and Doubt / 信仰与怀疑": {
        "description": "The novel stages the conflict between religious faith, skeptical reason, rebellion against God, and active love.",
        "keywords": ["God", "faith", "doubt", "atheism", "Zosima", "Alyosha", "Ivan", "上帝", "信仰", "怀疑", "无神论"],
    },
    "Parricide and Responsibility / 弑父与责任": {
        "description": "The murder plot is not only legal but moral: who desired the father's death, who acted, and who is responsible?",
        "keywords": ["father", "murder", "parricide", "responsibility", "Dmitri", "Ivan", "Smerdyakov", "父亲", "谋杀", "弑父", "责任"],
    },
    "Suffering of Children / 儿童苦难": {
        "description": "The suffering of innocent children is central to Ivan's rebellion and to the novel's moral test of faith and love.",
        "keywords": ["children", "child", "Ilyusha", "suffering", "innocent", "tears", "儿童", "孩子", "苦难", "无辜", "眼泪"],
    },
    "Sensuality and Desire / 欲望与堕落": {
        "description": "The Karamazov world is driven by money, erotic rivalry, humiliation, and bodily appetite.",
        "keywords": ["sensual", "desire", "money", "jealousy", "Grushenka", "Dmitri", "Fyodor", "欲望", "金钱", "嫉妒"],
    },
    "Pride and Humiliation / 骄傲与羞辱": {
        "description": "Love is often mixed with pride, debt, revenge, public moral performance, and humiliation.",
        "keywords": ["pride", "humiliation", "Katerina", "Grushenka", "Dmitri", "Ivan", "骄傲", "羞辱", "复仇"],
    },
    "Active Love / 积极的爱": {
        "description": "Zosima and Alyosha represent concrete active love rather than abstract doctrine or theatrical morality.",
        "keywords": ["active love", "love", "Zosima", "Alyosha", "responsibility", "humility", "积极的爱", "爱", "责任", "谦卑"],
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
        st.session_state.load_message = "当前使用内置演示资料。请在首页上传你电脑里的 EPUB 或 TXT。"


init_state()


# ============================================================
# 基础工具函数
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
            if keyword.lower() in lower or keyword in text:
                found.append(name)
                break

    return found


# ============================================================
# 本地 EPUB / TXT 解析
# ============================================================

def html_to_text(raw_html):
    if not raw_html:
        return ""

    text = raw_html

    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<nav.*?>.*?</nav>", " ", text)

    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?i)</div\s*>", "\n", text)
    text = re.sub(r"(?i)</h[1-6]\s*>", "\n\n", text)
    text = re.sub(r"(?i)</li\s*>", "\n", text)

    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)

    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n\n".join(lines).strip()


def extract_title_from_html(raw_html, fallback):
    if not raw_html:
        return fallback

    patterns = [
        r"(?is)<h1[^>]*>(.*?)</h1>",
        r"(?is)<h2[^>]*>(.*?)</h2>",
        r"(?is)<h3[^>]*>(.*?)</h3>",
        r"(?is)<title[^>]*>(.*?)</title>",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_html)
        if match:
            title = html_to_text(match.group(1))
            title = re.sub(r"\s+", " ", title).strip()
            if 2 <= len(title) <= 120:
                return title

    return fallback


def decode_bytes(data):
    for enc in ["utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"]:
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", errors="ignore")


def infer_book_number(title, text, fallback_index):
    sample = f"{title}\n{text[:800]}"

    match = re.search(r"\bBook\s+([IVX]+)\b", sample, re.I)
    if match:
        value = roman_to_int(match.group(1))
        if value:
            return value

    chinese_map = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "十一": 11,
        "十二": 12,
    }

    match = re.search(r"第(十一|十二|十|一|二|三|四|五|六|七|八|九)卷", sample)
    if match:
        return chinese_map.get(match.group(1), fallback_index)

    return fallback_index


def split_text_by_chapter_markers(section):
    title = section["title"]
    text = section["text"]

    pattern = re.compile(
        r"(?m)^(Chapter\s+[IVXLC]+\b.*?|第[一二三四五六七八九十百零〇\d]+章.*?|第[一二三四五六七八九十百零〇\d]+回.*?)$",
        re.I,
    )

    matches = list(pattern.finditer(text))

    if len(matches) < 2:
        return [section]

    result = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        chapter_title = re.sub(r"\s+", " ", match.group(1)).strip()
        chapter_text = text[start:end].strip()

        if len(chapter_text) < 100:
            continue

        result.append(
            {
                "title": f"{title} | {chapter_title}",
                "book_number": section.get("book_number", 1),
                "source": section.get("source", ""),
                "text": chapter_text,
            }
        )

    return result if result else [section]


def parse_txt_bytes(data, filename):
    text = decode_bytes(data)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip()

    chapter_pattern = re.compile(
        r"(?m)^(Chapter\s+[IVXLC]+\b.*?|Book\s+[IVXLC]+\b.*?|第[一二三四五六七八九十百零〇\d]+章.*?|第[一二三四五六七八九十百零〇\d]+回.*?|第[一二三四五六七八九十百零〇\d]+卷.*?)$",
        re.I,
    )

    matches = list(chapter_pattern.finditer(text))
    sections = []

    if len(matches) >= 2:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            section_title = re.sub(r"\s+", " ", match.group(1)).strip()
            section_text = text[start:end].strip()

            if len(section_text) < 100:
                continue

            sections.append(
                {
                    "title": section_title,
                    "book_number": infer_book_number(section_title, section_text, i + 1),
                    "source": f"Uploaded TXT: {filename}",
                    "text": section_text,
                }
            )
    else:
        max_len = 9000
        for i in range(0, len(text), max_len):
            piece = text[i:i + max_len].strip()
            if len(piece) < 100:
                continue
            sections.append(
                {
                    "title": f"{filename} | Part {len(sections) + 1}",
                    "book_number": len(sections) + 1,
                    "source": f"Uploaded TXT: {filename}",
                    "text": piece,
                }
            )

    return sections


def parse_epub_bytes(data, filename):
    sections = []

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"这不是有效的 EPUB 文件：{e}")

    names = zf.namelist()

    opf_path = None

    try:
        container_xml = zf.read("META-INF/container.xml")
        root = ET.fromstring(container_xml)
        for elem in root.iter():
            if elem.tag.endswith("rootfile"):
                opf_path = elem.attrib.get("full-path")
                break
    except Exception:
        opf_path = None

    if not opf_path:
        for name in names:
            if name.lower().endswith(".opf"):
                opf_path = name
                break

    ordered_files = []

    if opf_path:
        opf_dir = posixpath.dirname(opf_path)

        try:
            opf_xml = zf.read(opf_path)
            root = ET.fromstring(opf_xml)

            manifest = {}
            spine_ids = []

            for elem in root.iter():
                tag = elem.tag.split("}")[-1]

                if tag == "item":
                    item_id = elem.attrib.get("id")
                    href = elem.attrib.get("href")
                    media_type = elem.attrib.get("media-type", "")
                    if item_id and href:
                        manifest[item_id] = {
                            "href": href,
                            "media_type": media_type,
                        }

                elif tag == "itemref":
                    idref = elem.attrib.get("idref")
                    if idref:
                        spine_ids.append(idref)

            for idref in spine_ids:
                item = manifest.get(idref)
                if not item:
                    continue

                href = item["href"]
                media_type = item["media_type"]

                if (
                    href.lower().endswith((".xhtml", ".html", ".htm"))
                    or "html" in media_type.lower()
                ):
                    full_path = posixpath.normpath(posixpath.join(opf_dir, href))
                    if full_path in names:
                        ordered_files.append(full_path)

        except Exception:
            ordered_files = []

    if not ordered_files:
        ordered_files = [
            name for name in names
            if name.lower().endswith((".xhtml", ".html", ".htm"))
            and "nav" not in name.lower()
            and "toc" not in name.lower()
        ]
        ordered_files.sort()

    for index, file_path in enumerate(ordered_files):
        try:
            raw = decode_bytes(zf.read(file_path))
        except Exception:
            continue

        title = extract_title_from_html(raw, f"{filename} | Section {index + 1}")
        text = html_to_text(raw)

        lower_title = title.lower()
        lower_path = file_path.lower()

        if "contents" in lower_title or "table of contents" in lower_title:
            continue
        if "toc" in lower_path or "nav" in lower_path:
            continue
        if len(text) < 120:
            continue

        section = {
            "title": title,
            "book_number": infer_book_number(title, text, index + 1),
            "source": f"Uploaded EPUB: {filename}",
            "text": text,
        }

        sections.extend(split_text_by_chapter_markers(section))

    cleaned = []
    seen = set()

    for section in sections:
        key = (section["title"], section["text"][:120])
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(section)

    if not cleaned:
        raise ValueError("EPUB 读取到了，但没有解析出有效正文。可能是加密 EPUB、扫描版，或格式不标准。")

    return cleaned


def load_uploaded_book(uploaded_file):
    filename = uploaded_file.name
    data = uploaded_file.read()

    if filename.lower().endswith(".epub"):
        sections = parse_epub_bytes(data, filename)
    elif filename.lower().endswith(".txt"):
        sections = parse_txt_bytes(data, filename)
    else:
        raise ValueError("目前只支持 EPUB 和 TXT。")

    if not sections:
        raise ValueError("没有解析出章节。")

    st.session_state.sections = sections
    st.session_state.book_loaded = True
    st.session_state.load_message = f"已从本地上传文件解析：{filename}。共 {len(sections)} 个章节/段落。"
    return sections


# ============================================================
# 切片与检索
# ============================================================

def make_chunks(sections):
    chunks = []

    for section_index, section in enumerate(sections):
        text = section["text"]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

        if not paragraphs:
            paragraphs = [text]

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
        return "没有读取到 OpenAI API key。请在 Streamlit Cloud 的 Secrets 里设置 OPENAI_API_KEY，或在本地环境变量里设置 OPENAI_API_KEY。"

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

sections = st.session_state.sections
chunks = make_chunks(sections)
all_chunks = chunks + st.session_state.extra_chunks
section_titles = [section["title"] for section in sections]

st.title("📚《卡拉马佐夫兄弟》AI 互动文学档案馆")
st.caption("The Brothers Karamazov Interactive Literary Archive v1.4 local-epub-parser")

with st.sidebar:
    st.header("导航")

    page = st.radio(
        "选择页面",
        [
            "首页 / 本地文本加载",
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
        st.success("已加载本地文本")
    else:
        st.warning("当前为内置演示资料")
    st.caption(st.session_state.load_message)


# ============================================================
# 首页
# ============================================================

if page == "首页 / 本地文本加载":
    st.subheader("首页 / 本地文本加载")

    st.write("这个版本优先使用你本地的 EPUB / TXT，不再依赖网上下载。网页会先打开，然后你手动上传文件解析。")

    if st.session_state.book_loaded:
        st.success(f"文本已加载。当前共有 {len(sections)} 个章节/段落，{len(chunks)} 个检索片段。")
    else:
        st.warning("当前使用内置演示资料。请上传你电脑里的 EPUB 或 TXT。")

    st.divider()

    st.markdown("### 上传你的 EPUB / TXT")

    uploaded_file = st.file_uploader(
        "选择本地文件",
        type=["epub", "txt"],
        help="推荐 EPUB。TXT 也可以。文件只在当前 Streamlit 会话中解析，不需要放进 GitHub。",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("读取本地文件", type="primary"):
            if uploaded_file is None:
                st.error("你还没有选择文件。请先上传 EPUB 或 TXT。")
            else:
                try:
                    with st.spinner("正在本地解析文件，EPUB 可能需要几十秒..."):
                        loaded_sections = load_uploaded_book(uploaded_file)

                    st.success(f"解析成功：共 {len(loaded_sections)} 个章节/段落。")
                    st.rerun()

                except Exception as e:
                    st.error(f"解析失败：{e}")
                    st.info("如果 EPUB 解析失败，可以用 Calibre 把它转换成 TXT 或另一个 EPUB 再试。")

    with col2:
        if st.button("恢复内置演示资料"):
            st.session_state.sections = DEMO_SECTIONS
            st.session_state.book_loaded = False
            st.session_state.load_message = "已恢复内置演示资料。"
            st.rerun()

    st.divider()

    st.markdown("### 当前资料状态")
    st.write(f"章节/段落数量：{len(sections)}")
    st.write(f"检索片段数量：{len(chunks)}")
    st.write("Parser version: v1.4 local-epub-parser")

    st.markdown("### 当前章节列表预览")
    for s in sections[:20]:
        st.write(f"- {s['title']}")

    if len(sections) > 20:
        st.write(f"... 还有 {len(sections) - 20} 个章节/段落")

    st.divider()

    st.markdown("### 重要提醒")
    st.write("如果你的 EPUB 是现代中文译本，不建议上传到 GitHub 公开仓库。这个上传功能是在网页运行时临时解析文件，更适合私人阅读和测试。")


# ============================================================
# 阅读助手
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
# 人物档案
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
# 人物关系图
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
# 主题面板
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
# 证据检索
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
# 上传补充资料
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
# 历史导出
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
# 项目说明
# ============================================================

elif page == "项目说明":
    st.subheader("项目说明")

    st.markdown(
        """
这是一个基于 **Streamlit + OpenAI API + 本地 EPUB/TXT 上传** 的《卡拉马佐夫兄弟》互动文学档案馆。

这个版本是 **v1.4 local-epub-parser 本地文本版**。

它不会自动下载 Project Gutenberg，也不会在启动时联网读取整本书。

使用方式：

1. 在首页上传你电脑里的 EPUB 或 TXT；
2. 点击“读取本地文件”；
3. 等待解析成功；
4. 进入阅读助手、人物档案、证据检索等页面使用。

功能包括：

- 首页 / 本地文本加载
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
