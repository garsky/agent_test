from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()


HELP_TEXT = """
╔══════════════════════════════════════════════════════════╗
║              Camera Driver Agent (CDA) 帮助             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  命令:                                                    ║
║    quit       退出程序                                    ║
║    reset      重置当前对话                                ║
║    switch     切换平台/项目                               ║
║    help       显示此帮助                                  ║
║    kb         知识库管理                                  ║
║    config     查看当前配置                                ║
║                                                          ║
║  提问技巧:                                                ║
║    1. 描述问题时附上平台信息                              ║
║       例: "MTK24E上imx586点不亮"                         ║
║    2. 粘贴关键日志片段                                    ║
║       例: "dmesg报 i2c transfer failed"                  ║
║    3. 上传DTS/代码文件可获得更精准的分析                  ║
║    4. 指定问题类型: 点亮/功能bug/timing                   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

KB_HELP = """
╔══════════════════════════════════════════════════════════╗
║                    知识库管理                            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  kb add <文件路径>    添加知识库文件到当前平台            ║
║  kb list             列出当前平台的知识库文件            ║
║  kb build            重新构建向量索引                    ║
║  kb search <关键词>   搜索知识库内容                     ║
║                                                          ║
║  知识库文件格式:                                          ║
║    支持 .md (Markdown) / .txt (纯文本) 格式              ║
║    建议使用 Markdown 格式，结构更清晰                     ║
║                                                          ║
║  添加知识库文件步骤:                                      ║
║    1. 将文件放入 knowledge/<厂商>/<子平台>/platform_docs/ ║
║    2. 运行 kb build 重建向量索引                         ║
║                                                          ║
║  示例:                                                    ║
║    kb add ./my_sensor_guide.md                           ║
║    kb list                                               ║
║    kb build                                              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""


def select_platform() -> tuple[str, str, str]:
    from platforms.manager import PlatformManager

    manager = PlatformManager()

    vendors = manager.get_vendors()
    print("\n" + "=" * 55)
    print("  欢迎使用 Camera Driver Agent (CDA)")
    print("  手机 Camera 驱动工程师智能助手")
    print("=" * 55)

    print("\n请选择平台厂商:")
    for i, v in enumerate(vendors, 1):
        print(f"  [{i}] {v['display_name']}")
    vendor_idx = int(input("\n> ")) - 1
    if vendor_idx < 0 or vendor_idx >= len(vendors):
        print("无效选择")
        sys.exit(1)
    vendor_id = vendors[vendor_idx]["id"]

    sub_platforms = manager.get_sub_platforms(vendor_id)
    print(f"\n请选择子平台:")
    for i, sp in enumerate(sub_platforms, 1):
        print(f"  [{i}] {sp['display_name']}")
    sp_idx = int(input("\n> ")) - 1
    if sp_idx < 0 or sp_idx >= len(sub_platforms):
        print("无效选择")
        sys.exit(1)
    sub_platform_id = sub_platforms[sp_idx]["id"]

    projects = manager.get_projects(vendor_id, sub_platform_id)
    print(f"\n请选择项目:")
    for i, p in enumerate(projects, 1):
        print(f"  [{i}] {p['name']}")
    print(f"  [{len(projects) + 1}] + 新建项目")

    proj_idx = int(input("\n> ")) - 1
    if proj_idx == len(projects):
        project_name = input("请输入项目名称: ").strip()
        if not project_name:
            print("项目名称不能为空")
            sys.exit(1)
        project_data = manager.create_project(vendor_id, sub_platform_id, project_name)
        project_id = project_data["id"]
    elif 0 <= proj_idx < len(projects):
        project_id = projects[proj_idx]["id"]
    else:
        print("无效选择")
        sys.exit(1)

    return vendor_id, sub_platform_id, project_id


def handle_kb_command(args: str, platform_context) -> None:
    from pathlib import Path
    import shutil

    parts = args.strip().split(maxsplit=1)
    sub_cmd = parts[0] if parts else ""
    sub_args = parts[1] if len(parts) > 1 else ""

    docs_dir = Path(platform_context.sub_platform.knowledge_path) / "platform_docs"

    if sub_cmd == "list":
        if not docs_dir.exists():
            print(f"  知识库目录不存在: {docs_dir}")
            return
        files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
        if not files:
            print("  知识库为空，使用 'kb add <文件>' 添加文件")
        else:
            print(f"  知识库文件 ({len(files)} 个):")
            for f in files:
                size = f.stat().st_size
                print(f"    - {f.name} ({size} bytes)")

    elif sub_cmd == "add":
        if not sub_args:
            print("  用法: kb add <文件路径>")
            print("  将文件复制到当前平台的知识库目录")
            return
        src = Path(sub_args.strip().strip('"').strip("'"))
        if not src.exists():
            print(f"  文件不存在: {src}")
            return
        docs_dir.mkdir(parents=True, exist_ok=True)
        dst = docs_dir / src.name
        shutil.copy2(str(src), str(dst))
        print(f"  ✓ 已添加: {src.name} → {dst}")
        print(f"  提示: 运行 'kb build' 重建向量索引以使新文件生效")

    elif sub_cmd == "build":
        print("  正在构建向量索引...")
        try:
            from knowledge.builder import build_knowledge_base
            build_knowledge_base(
                platform_context.vendor.id,
                platform_context.sub_platform.id,
            )
            print("  ✓ 知识库构建完成")
        except Exception as e:
            print(f"  ✗ 构建失败: {e}")

    elif sub_cmd == "search":
        if not sub_args:
            print("  用法: kb search <关键词>")
            return
        from tools.knowledge_search import KnowledgeSearchTool
        tool = KnowledgeSearchTool(platform_context=platform_context)
        result = tool._run(sub_args)
        print(f"  搜索结果:\n{result}")

    else:
        print(KB_HELP)


def show_config(platform_context) -> None:
    from config.settings import settings
    from config.llm_config import LLMConfig, EmbeddingConfig

    llm_config = LLMConfig.from_settings()
    emb_config = EmbeddingConfig.from_settings()

    print(f"\n  当前配置:")
    print(f"    平台: {platform_context.display_string}")
    print(f"    LLM: {llm_config.provider} / {llm_config.model}")
    print(f"    Embedding: {emb_config.provider} / {emb_config.model or 'default'}")
    print(f"    API Key: {'已配置' if llm_config.api_key else '未配置'}")
    print(f"    Group ID: {'已配置' if settings.MINIMAX_GROUP_ID else '未配置'}")
    print()


def run_cli():
    from platforms.manager import PlatformManager
    from agent.core import CameraDriverAgent

    vendor_id, sub_platform_id, project_id = select_platform()

    manager = PlatformManager()
    context = manager.set_context(vendor_id, sub_platform_id, project_id)

    print(f"\n✓ 已进入: {context.display_string}")
    print(f"  输入 'help' 查看帮助，'quit' 退出\n")

    agent = CameraDriverAgent(context)

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd == "quit":
            print("再见！")
            break
        if cmd == "reset":
            agent.reset_conversation()
            print("对话已重置\n")
            continue
        if cmd == "switch":
            vendor_id, sub_platform_id, project_id = select_platform()
            context = manager.set_context(vendor_id, sub_platform_id, project_id)
            agent = CameraDriverAgent(context)
            print(f"\n✓ 已切换到: {context.display_string}\n")
            continue
        if cmd == "help":
            print(HELP_TEXT)
            continue
        if cmd.startswith("kb"):
            handle_kb_command(user_input[2:].strip(), context)
            continue
        if cmd == "config":
            show_config(context)
            continue

        print("\nAgent: ", end="", flush=True)
        try:
            response = agent.chat_sync(user_input)
            print(response)
        except Exception as e:
            print(f"错误: {e}")
        print()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        import uvicorn
        from api.server import create_app
        uvicorn.run(create_app(), host="127.0.0.1", port=8000)
    else:
        run_cli()


if __name__ == "__main__":
    main()
