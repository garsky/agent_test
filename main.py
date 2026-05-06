from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()


def select_platform() -> tuple[str, str, str]:
    from platform.manager import PlatformManager

    manager = PlatformManager()

    vendors = manager.get_vendors()
    print("\n" + "=" * 50)
    print("  欢迎使用 Camera Driver Agent (CDA)")
    print("=" * 50)

    print("\n请选择平台:")
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


def run_cli():
    from platform.manager import PlatformManager
    from agent.core import CameraDriverAgent

    vendor_id, sub_platform_id, project_id = select_platform()

    manager = PlatformManager()
    context = manager.set_context(vendor_id, sub_platform_id, project_id)

    print(f"\n✓ 已进入: {context.display_string}")
    print("知识库已加载，可以开始提问了")
    print("输入 'quit' 退出，'reset' 重置对话，'switch' 切换平台\n")

    agent = CameraDriverAgent(context)

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break
        if user_input.lower() == "reset":
            agent.reset_conversation()
            print("对话已重置\n")
            continue
        if user_input.lower() == "switch":
            vendor_id, sub_platform_id, project_id = select_platform()
            context = manager.set_context(vendor_id, sub_platform_id, project_id)
            agent = CameraDriverAgent(context)
            print(f"\n✓ 已切换到: {context.display_string}\n")
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
        uvicorn.run(create_app(), host="0.0.0.0", port=8000)
    else:
        run_cli()


if __name__ == "__main__":
    main()
