"""
DeepSeek V3.2 文本分析机器人
- 支持对.txt, .docx,.pdf文件类型的分析功能
- 目前支持的skill: summary
-请预先安装python-docx, pymupdf,openai库
"""

from openai import OpenAI
import os
from docx import Document
import fitz
from dotenv import load_dotenv

# ====== API KEY ======
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("❌ 未找到 DEEPSEEK_API_KEY，请在 .env 文件中设置")

# ====== 初始化客户端 ======
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# ====== 1. 文件读取能力（核心能力）======

def read_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def read_docx(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)

def read_pdf(file_path):
    pdf = fitz.open(file_path)
    full_text = []
    for page in pdf:
        text_page = page.get_text()
        full_text.append(text_page)
    pdf.close()
    return "\n".join(full_text)

def read_file(file_path):
    if not os.path.exists(file_path):
        return "文件不存在"

    if file_path.endswith(".txt"):
        return read_txt(file_path)

    elif file_path.endswith(".docx"):
        return read_docx(file_path)

    elif file_path.endswith(".pdf"):
        return read_pdf(file_path)

    else:
        return "暂不支持该文件类型"

def list_files():
    # 文本存储目录
    os.makedirs("text_file_repository", exist_ok=True)
    all_files = os.listdir("text_file_repository")
    files = []
    for file in all_files:
        if file.endswith((".txt", ".docx", ".pdf")):
            files.append(file)
        else:
            continue
    return files

# ====== 2. Skills ======

# ====== summary功能 ======
def summary(text):
    response_3 = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是一个专业的学术助手，请用清晰的语言总结文本的核心内容。"},
            {"role": "user", "content": f"请将以下文本总结为：1. 背景;2. 问题;3. 方法;4. 结果;5. 意义。\n{text}"}
        ],
        temperature = 0.7
    )
    return response_3.choices[0].message.content

# ====== explain功能 ======
def explain(text):
    response_2 = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是一个专业的学术助手，请用“像教授授课一样”的方式讲解文本的核心内容。"},
            {"role": "user", "content": f"请用相对通俗的语言解释以下内容，如果涉及专业术语，请给出简单解释，但请避免滥用比喻和类比。\n{text}"}
        ],
        temperature=0.7
    )
    return response_2.choices[0].message.content

# ======extract keywords功能 ======
def key_words(text):
    response_3 = client.chat.completions.create(model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是一个专业的学术助手，请用精炼严谨的语言回答问题。"},
            {"role": "user", "content": f"请提取文本中的关键概念，并用列表列出，每个概念附带一句简要解释。\n{text}"}
        ],
        temperature=0.7)
    return response_3.choices[0].message.content

# ====== skill选择菜单 ======
agent_skills = {
    "1": ("summary", "结构化总结", summary),
    "2": ("explain", "解释文本", explain),
    "3": ("keywords", "提取关键词", key_words)
}

def select_skill():
    print("\n🔑 已有的功能：")
    for skill_num, skill in agent_skills.items():
        print(f"{skill_num}.{skill[1]}")
    while True:
        choice = input("\n请选择序号：: ").strip()
        if not choice:
            print("⚠️请输入序号")
            continue

        if not choice.isdigit():
            print("❌ 请输入数字")
            continue

        if choice not in agent_skills:
            print("❌ 无效序号，请重新输入")
            continue

        return agent_skills[choice]


# ====== 3. 工具注册 ======



# ====== 4. 文件选择菜单 ======

def select_file():
    file_list = list_files()
    print("\n📁 已有的文本：")
    if file_list:
        for i,file in enumerate(file_list,1):
            print(f"{i}. {file}")
        print("若无目标文件，请确认是否添加文件到根目录的text_file_repository中。")
    else:
        print("暂无文件，请手动添加到根目录的text_file_repository中，或手动创建该目录。")
        return None

    while True:
        choice = input("\n请选择序号: ").strip()
        if not choice:
            print("⚠️请输入序号")
            continue

        # 尝试解析为序号
        if choice.isdigit():
            idx = int(choice)
            if file_list and 1 <= idx <= len(file_list):
                selected_file = file_list[idx - 1]
                return os.path.join("text_file_repository", selected_file)
            else:
                print("❌ 无效序号，请重新输入。")
                continue

# ====== 5. Agent主程序 ======

def deep_agent(file_path, skill_key, skill_name, skill_func):

    print(f"\n📂 目标文件: {file_path}")

    # Step 1: 读取文件
    content = read_file(file_path)

    if content.startswith("文件不存在") or content.startswith("暂不支持"):
        print(content)
        return

    print("\n📖 文件读取成功，长度:", len(content))

    # Step 2: 调用总结
    print(f"\n🧠 正在执行：{skill_name}...\n")
    result = skill_func(content[:5000])

    # Step 3: 生成结果并保存
    print("📝 结果：\n")
    print(result)
    output_dir = os.path.join("papers_analysis_output", f"{skill_key}_outputs")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_{skill_key}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {skill_name}：{os.path.basename(file_path)}\n\n")
        f.write(result)
    print(f"\n💾 结果已自动保存至：{output_path}")

# ====== 6. 运行 ======

if __name__ == "__main__":
    file_path = select_file()
    if file_path is None:        # ✅ 先判断文件是否有效
        print("❌ 未选择文件，程序退出。")
        exit()
    skill_key, skill_name, skill_func = select_skill()
    deep_agent(file_path, skill_key, skill_name, skill_func)


