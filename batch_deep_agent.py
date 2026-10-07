"""
批量处理脚本 - 对多篇论文同时执行所有 Skill
使用方法：将所有论文放在 papers/ 文件夹下，运行本脚本即可。
"""

import os
import sys

# 将 deep_agent.py 所在目录加入系统路径，确保可以导入（如果两个文件在同一目录下则不需要）
sys.path.append(os.path.dirname(__file__))

# 从你的 deep_agent 模块中导入核心函数和技能字典
from deep_agent import deep_agent, agent_skills, list_files

# ====== 配置区域 ======
# 你可以修改这里来指定存放论文的文件夹
PAPER_DIR = "paper_batch"          # 论文存放目录
# 是否对每篇论文执行全部三种技能？设为 False 则可以每次手动选择
RUN_ALL_SKILLS = True
# =====================

def batch_process():
    # 确保论文目录存在
    os.makedirs(PAPER_DIR, exist_ok=True)

    # 收集所有支持的文件
    supported_ext = (".txt", ".docx", ".pdf")
    all_files = []
    for f in os.listdir(PAPER_DIR):
        if f.lower().endswith(supported_ext):
            all_files.append(os.path.join(PAPER_DIR, f))

    if not all_files:
        print(f"⚠️ 在 '{PAPER_DIR}' 中没有找到支持的文件（.txt/.docx/.pdf）")
        return

    print(f"📚 发现 {len(all_files)} 篇论文待处理\n")
    print("📋 待处理文件清单：")
    for i, f in enumerate(all_files, 1):
        print(f"   {i}. {os.path.basename(f)}")
    print()  # 空行分隔

    # 用户自行决定是否开始运行
    while True:
        confirm = input("是否开始自动分析？(yes/no): ").strip().lower()
        if confirm == "yes" or confirm == "y":
            break  # 继续执行
        elif confirm == "no" or confirm == "n":
            print("🛑 已取消批量处理，程序退出。")
            return
        else:
            print("⚠️ 无效输入，请输入 yes 或 no。")

    # 决定要执行的技能列表
    if RUN_ALL_SKILLS:
        skills_to_run = list(agent_skills.values())  # 所有技能
        print(f"⚙️ 将对每篇论文执行全部 {len(skills_to_run)} 种分析\n")
    else:
        # 如果不想全部运行，可以在这里改为交互式选择（略）
        pass

    # 逐个处理文件
    for idx, file_path in enumerate(all_files, 1):
        print(f"\n{'='*50}")
        print(f"📄 [{idx}/{len(all_files)}] 正在处理: {os.path.basename(file_path)}")
        print('='*50)

        for skill_key, skill_name, skill_func in skills_to_run:
            try:
                deep_agent(file_path, skill_key, skill_name, skill_func)
            except Exception as e:
                print(f"❌ 处理文件 {file_path} 时出错（技能 {skill_name}）: {e}")
                continue

    print("\n🎉 批量处理全部完成！结果已保存至对应 papers_analysis_output 文件夹中。")

if __name__ == "__main__":
    batch_process()

