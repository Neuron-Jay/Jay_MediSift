"""
DeepSeek V4 多对话管理 + 流式输出 + JSON持久化
- 支持创建/选择多个独立对话，每个对话单独保存
- 自动保存聊天记录，对话名由用户指定
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# ==================== 加载 API Key ====================
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("❌ 错误：未找到 API Key，请在 .env 文件中设置 DEEPSEEK_API_KEY")
    exit(1)

# ==================== 初始化客户端 ====================
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# ==================== 对话存储目录 ====================
CONVERSATIONS_DIR = "conversations"
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)  # 确保文件夹存在

def list_conversations():
    """返回现有对话名列表（不含 .json 后缀）"""
    files = [f for f in os.listdir(CONVERSATIONS_DIR) if f.endswith(".json")]
    # 按修改时间排序，最新的在前
    files.sort(key=lambda x: os.path.getmtime(os.path.join(CONVERSATIONS_DIR, x)), reverse=True)
    return [f[:-5] for f in files]  # 去掉 .json

def load_conversation(conversation_name):
    """加载指定对话的历史，如果不存在则返回新对话（带 system 消息）"""
    file_path = os.path.join(CONVERSATIONS_DIR, f"{conversation_name}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ 历史文件损坏，将创建新对话。")
    # 默认新对话
    return [{"role": "system", "content": "你是一个乐于助人的AI助手。"}]

def save_conversation(conversation, conversation_name):
    """保存指定对话的历史"""
    file_path = os.path.join(CONVERSATIONS_DIR, f"{conversation_name}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)

# ==================== 对话选择菜单 ====================
def select_conversation():
    """让用户选择或新建一个对话，返回对话名"""
    conv_list = list_conversations()
    print("\n📁 已有的对话：")
    if conv_list:
        for i, name in enumerate(conv_list, 1):
            print(f"  {i}. {name}")
        print(f"  {len(conv_list)+1}.（新建更多对话） ")
    else:
        print("（暂无对话，请新建）")

    while True:
        choice = input("\n请选择序号（或输入新对话名直接创建）: ").strip()
        if not choice:
            continue

        # 尝试解析为序号
        if choice.isdigit():
            idx = int(choice)
            if conv_list and 1 <= idx <= len(conv_list):
                return conv_list[idx-1]
            elif conv_list and idx == len(conv_list)+1:
                # 新建
                break
            elif not conv_list and idx == 1:
                break
            else:
                print("❌ 无效序号，请重新输入。")
                continue
        else:
            # 直接作为新对话名
            # 简单过滤非法字符
            safe_name = "".join(c for c in choice if c.isalnum() or c in " _-")
            if not safe_name:
                print("❌ 对话名不能为空，请重新输入。")
                continue
            return safe_name

    # 新建对话：输入名称
    while True:
        new_name = input("请输入新对话名称: ").strip()
        if not new_name:
            print("❌ 名称不能为空。")
            continue
        # 过滤非法字符
        safe_name = "".join(c for c in new_name if c.isalnum() or c in " _-")
        if not safe_name:
            print("❌ 名称只能包含汉字、字母、数字、空格、下划线、连字符。")
            continue
        # 检查是否已存在
        if safe_name in list_conversations():
            print("⚠️ 该名称已存在，请使用其他名称。")
            continue
        return safe_name

# ==================== 其他功能 ====================
def get_temperature(default: float = 0.7) -> float:
    while True:
        user_input = input(f"请设置 temperature（默认 {default}，回车直接使用）：").strip()

        if user_input == "":
            print(f"✅ 使用默认值 {default}")
            return default

        try:
            temp = float(user_input)
            if 0 <= temp <= 1.5:
                print(f"✅ 设置成功：{temp}")
                return temp
            else:
                print("⚠️ 超出范围（0~1.5）")
        except ValueError:
            print("❌ 请输入数字")




# ==================== 主程序 ====================
def deepseek_chat():
    # 选择或新建对话
    current_name = select_conversation()
    conversation = load_conversation(current_name)
    print(f"\n📂 当前对话：{current_name} （已加载 {len(conversation)-1} 条历史消息）")
    user_temperature = get_temperature()

    print("""⚠️使用前请确保您已关闭网络代理服务⚠️
    🤖 使用教程👇
    输入 'exit' 退出并保存；
    输入 'save' 手动快捷保存;
    输入 'new' 保存当前对话并建立新对话;
    输入 'delete' 删除当前对话。 """)
    print("👋我是DeepSeek V4，想和我聊点什么😉？")

    while True:
        user_input = input("你：")

        if user_input.lower() == "exit":
            save_conversation(conversation, current_name)
            print(f"✅ 对话“{current_name}”已保存此对话，再见！")
            break

        if user_input.lower() == "save":
            save_conversation(conversation, current_name)
            print(f"✅ 已快速保存当前对话“{current_name}”。")
            continue

        if user_input.lower() == "new":
            save_conversation(conversation, current_name)
            print(f"✅ 已保存原对话“{current_name}”。")
            # 重新选择或新建对话
            current_name = select_conversation()
            conversation = load_conversation(current_name)
            print(f"\n📂 将为您切换到新对话：{current_name} （已加载 {len(conversation)-1} 条历史消息）")
            continue

        if user_input.lower() == "delete":
            confirm = input(f"⚠️ 确定删除对话“{current_name}”吗？(y/n): ")
            if confirm.lower() == 'y':
                file_path = os.path.join(CONVERSATIONS_DIR, f"{current_name}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"✅ 已删除对话“{current_name}”。")
                # 删除后，重新选择对话（可以是新建或已有）
                current_name = select_conversation()
                conversation = load_conversation(current_name)
                print(f"\n📂 当前切换到对话：{current_name}")
                # 直接 continue 跳过后续的对话处理，回到主循环开头
                continue
            elif confirm.lower() == 'n':
                # 用户取消删除，继续当前对话
                print("操作已取消，请继续当前对话。")
                continue
            else:
                print("请输入有效字符！")

        # 正常对话
        conversation.append({"role": "user", "content": user_input})
        print("AI：", end="", flush=True)

        try:
            stream = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=conversation,
                temperature=user_temperature,
                max_tokens=1000,
                stream=True
            )

            full_reply = ""
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    print(delta.content, end="", flush=True)
                    full_reply += delta.content
            print()

            conversation.append({"role": "assistant", "content": full_reply})
            # 自动保存每一轮（避免丢失）
            save_conversation(conversation, current_name)

        except Exception as e:
            print(f"\n❌ 发生错误：{e}")
            conversation.pop()  # 移除刚才的用户消息

if __name__ == "__main__":
    deepseek_chat()