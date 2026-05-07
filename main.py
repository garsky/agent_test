from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()

WELCOME_BANNER = """
╔══════════════════════════════════════════════════════════╗
║        Camera Driver Agent (CDA) v1.0.2                  ║
║        手机 Camera 驱动工程师智能助手                     ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
╔══════════════════════════════════════════════════════════╗
║              Camera Driver Agent (CDA) 帮助             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  命令:                                                    ║
║    quit       退出程序                                    ║
║    reset      重置当前对话                                ║
║    switch     切换平台                                    ║
║    help       显示此帮助                                  ║
║    kb         知识库管理 (输入 kb 查看详情)               ║
║    platform   平台管理 (输入 platform 查看详情)           ║
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
║  知识库层级:                                              ║
║    全局通用: knowledge/common/                             ║
║      所有平台共享的知识和经验                              ║
║    厂商公共: knowledge/<厂商>/common/                      ║
║      同一厂商下多平台共享 (如 MTK 公共)                    ║
║    平台专属: knowledge/<厂商>/<子平台>/                    ║
║      仅当前子平台可见                                      ║
║                                                          ║
║  知识库:                                                  ║
║    kb add <文件>   添加文档到当前平台知识库               ║
║      支持: .md .txt .pdf .docx .pptx .xlsx               ║
║    kb update      检测变更并增量更新索引 (推荐)           ║
║    kb list        查看知识库文件列表 (含所有层级)         ║
║    kb build       全量重建向量索引                        ║
║    kb search <词> 搜索知识库内容                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

KB_HELP = """
╔══════════════════════════════════════════════════════════╗
║                    知识库管理                            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  知识库层级:                                              ║
║    全局通用: knowledge/common/platform_docs/              ║
║      所有平台共享 (如通用调试经验、术语表)                ║
║    厂商公共: knowledge/<厂商>/common/platform_docs/       ║
║      同一厂商多平台共享 (如 MTK 公共架构)                 ║
║    平台专属: knowledge/<厂商>/<子平台>/platform_docs/     ║
║      仅当前子平台可见 (如 mt6985 特有配置)                ║
║                                                          ║
║  命令:                                                    ║
║    kb add <文件路径>    添加知识库文件                      ║
║      支持: .md .txt .pdf .docx .pptx .xlsx                ║
║      默认添加到平台专属目录                                ║
║      kb add <文件> --global  添加到全局目录                ║
║      kb add <文件> --vendor  添加到厂商公共目录            ║
║    kb update           检测变更并增量更新索引 (推荐)       ║
║      自动检测新增/修改/删除                                ║
║      源文件删除时自动清理转换后的MD和索引                  ║
║    kb list             列出所有层级的知识库文件            ║
║    kb build            全量重建向量索引                    ║
║    kb search <关键词>   搜索知识库内容                     ║
║                                                          ║
║  文件格式:                                                ║
║    - 直接添加: .md (Markdown) / .txt (纯文本)             ║
║    - 自动转换: .pdf / .docx / .pptx / .xlsx               ║
║    - 文件编码: UTF-8                                      ║
║                                                          ║
║  文档内容建议:                                            ║
║    - 使用 ## 标题分段，便于检索定位                       ║
║    - 包含: 现象描述 / 根因分析 / 解决步骤                 ║
║    - 代码示例用 ``` 包裹                                  ║
║    - 关键参数用 **加粗** 标注                             ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

DEFAULT_PROJECT_ID = "1"

PLATFORM_HELP = """
╔══════════════════════════════════════════════════════════╗
║                    平台管理                              ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  命令:                                                    ║
║    platform list                        列出所有平台      ║
║    platform add vendor <id> [显示名]     添加厂商         ║
║    platform add sub <厂商> <id> [显示名] 添加子平台       ║
║    platform remove vendor <id>           移除厂商         ║
║    platform remove sub <厂商> <id>       移除子平台       ║
║                                                          ║
║  示例:                                                    ║
║    platform add vendor hisilicon                          ║
║    platform add vendor hisilicon "海思 (HiSilicon)"      ║
║    platform add sub hisilicon hi3660                      ║
║    platform remove sub hisilicon hi3660                   ║
║                                                          ║
║  说明:                                                    ║
║    - 显示名可选，不填时自动识别 (如 hisilicon→海思)       ║
║    - 内置厂商(高通/MTK/展锐)不可删除                      ║
║    - 添加后自动创建知识库目录                              ║
║    - 配置持久化到 knowledge/platforms.yaml                ║
║    - knowledge/ 下已有目录会自动发现                      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""


def handle_platform_command(args: str) -> None:
    from platforms.registry import _sanitize_id
    parts = args.strip().split()
    if not parts:
        print(PLATFORM_HELP)
        return

    from platforms.manager import PlatformManager
    manager = PlatformManager()

    sub_cmd = parts[0]

    if sub_cmd == "list":
        vendors = manager.get_vendors()
        print("\n  已注册平台:")
        for v in vendors:
            sps = manager.get_sub_platforms(v["id"])
            sp_names = ", ".join(sp["display_name"] for sp in sps) if sps else "无子平台"
            print(f"    {v['display_name']} ({v['id']})")
            print(f"      子平台: {sp_names}")
        print()

    elif sub_cmd == "add":
        if len(parts) < 2:
            print("  用法:")
            print("    platform add vendor <id> <显示名>")
            print("    platform add sub <厂商id> <子平台id> <显示名>")
            return
        target = parts[1]
        if target == "vendor":
            if len(parts) < 3:
                print("  用法: platform add vendor <id> [显示名]")
                print('  示例: platform add vendor hisilicon')
                print('        platform add vendor hisilicon "海思 (HiSilicon)"')
                return
            vid = _sanitize_id(parts[2])
            display_name = " ".join(parts[3:]).strip('"').strip("'") if len(parts) > 3 else ""
            result = manager.add_vendor(vid, display_name)
            print(f"  {result['message']}")
        elif target == "sub":
            if len(parts) < 4:
                print("  用法: platform add sub <厂商id> <子平台id> [显示名]")
                print('  示例: platform add sub hisilicon hi3660')
                print('        platform add sub hisilicon hi3660 "Hi3660"')
                return
            vendor_id = parts[2]
            spid = _sanitize_id(parts[3])
            display_name = " ".join(parts[4:]).strip('"').strip("'") if len(parts) > 4 else ""
            result = manager.add_sub_platform(vendor_id, spid, display_name)
            print(f"  {result['message']}")
        else:
            print(f"  未知添加目标: {target}")
            print("  支持: vendor / sub")

    elif sub_cmd == "remove":
        if len(parts) < 2:
            print("  用法:")
            print("    platform remove vendor <id>")
            print("    platform remove sub <厂商id> <子平台id>")
            return
        target = parts[1]
        if target == "vendor":
            if len(parts) < 3:
                print("  用法: platform remove vendor <id>")
                return
            result = manager.remove_vendor(parts[2])
            print(f"  {result['message']}")
        elif target == "sub":
            if len(parts) < 4:
                print("  用法: platform remove sub <厂商id> <子平台id>")
                return
            result = manager.remove_sub_platform(parts[2], parts[3])
            print(f"  {result['message']}")
        else:
            print(f"  未知移除目标: {target}")

    else:
        print(PLATFORM_HELP)


def select_platform() -> tuple[str, str, str]:
    from platforms.manager import PlatformManager

    manager = PlatformManager()

    vendors = manager.get_vendors()
    print(WELCOME_BANNER)

    print("请选择平台厂商:")
    for i, v in enumerate(vendors, 1):
        print(f"  [{i}] {v['display_name']}")
    print("  [q] 退出")
    raw = input("\n> ").strip().lower()
    if raw in ("q", "quit", "exit"):
        print("再见！")
        sys.exit(0)
    try:
        vendor_idx = int(raw) - 1
    except ValueError:
        print("无效输入，请输入数字")
        sys.exit(1)
    if vendor_idx < 0 or vendor_idx >= len(vendors):
        print("无效选择")
        sys.exit(1)
    vendor_id = vendors[vendor_idx]["id"]

    sub_platforms = manager.get_sub_platforms(vendor_id)
    print(f"\n请选择子平台:")
    for i, sp in enumerate(sub_platforms, 1):
        print(f"  [{i}] {sp['display_name']}")
    print("  [q] 退出")
    raw = input("\n> ").strip().lower()
    if raw in ("q", "quit", "exit"):
        print("再见！")
        sys.exit(0)
    try:
        sp_idx = int(raw) - 1
    except ValueError:
        print("无效输入，请输入数字")
        sys.exit(1)
    if sp_idx < 0 or sp_idx >= len(sub_platforms):
        print("无效选择")
        sys.exit(1)
    sub_platform_id = sub_platforms[sp_idx]["id"]

    return vendor_id, sub_platform_id, DEFAULT_PROJECT_ID


def _get_level_label(docs_dir: Path, vendor_id: str) -> str:
    path_str = str(docs_dir).replace("\\", "/")
    if "/common/platform_docs" in path_str and f"/{vendor_id}/" not in path_str:
        return "全局通用"
    elif f"/{vendor_id}/common/" in path_str:
        return f"{vendor_id} 厂商公共"
    else:
        return "平台专属"


def handle_kb_command(args: str, platform_context) -> None:
    from pathlib import Path
    import shutil

    parts = args.strip().split(maxsplit=1)
    sub_cmd = parts[0] if parts else ""
    sub_args = parts[1] if len(parts) > 1 else ""

    from knowledge.builder import get_all_doc_dirs

    docs_dir = Path(platform_context.sub_platform.knowledge_path) / "platform_docs"

    if sub_cmd == "list":
        vendor_id = platform_context.vendor.id
        sub_platform_id = platform_context.sub_platform.id
        all_dirs = get_all_doc_dirs(vendor_id, sub_platform_id)

        total_files = 0
        for d in all_dirs:
            level = _get_level_label(d, vendor_id)
            files = list(d.glob("*.md")) + list(d.glob("*.txt"))
            source_files = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() not in (".md", ".txt")]
            if files or source_files:
                print(f"\n  [{level}] {d}")
                for f in sorted(files):
                    size = f.stat().st_size
                    marker = ""
                    for sf in source_files:
                        if sf.stem == f.stem and sf.suffix.lower() in (".pdf", ".docx", ".pptx", ".xlsx"):
                            marker = f" (← {sf.name})"
                            break
                    print(f"    - {f.name} ({size:,} bytes){marker}")
                for sf in sorted(source_files):
                    if sf.suffix.lower() in (".pdf", ".docx", ".pptx", ".xlsx"):
                        has_md = (d / (sf.stem + ".md")).exists()
                        if not has_md:
                            print(f"    - {sf.name} (未转换)")
                total_files += len(files)

        if total_files == 0:
            print("  知识库为空")
            print("  运行 'kb add <文件>' 添加文档")
        else:
            print(f"\n  共 {total_files} 个文档文件")

    elif sub_cmd == "add":
        if not sub_args:
            print("  用法: kb add <文件路径> [--global|--vendor]")
            print("  示例: kb add ./my_sensor_guide.md")
            print("        kb add ./report.pdf")
            print("        kb add ./mtk_common.md --vendor")
            print("        kb add ./debug_tips.md --global")
            print()
            print("  支持格式:")
            print("    直接添加: .md / .txt (UTF-8编码)")
            print("    自动转换: .pdf / .docx / .pptx / .xlsx")
            print()
            print("  目标层级:")
            print("    (默认)     平台专属 knowledge/<厂商>/<子平台>/")
            print("    --vendor   厂商公共 knowledge/<厂商>/common/")
            print("    --global   全局通用 knowledge/common/")
            return
        args_parts = sub_args.strip().split()
        src_path = args_parts[0].strip('"').strip("'")
        target_level = "platform"
        if "--global" in args_parts:
            target_level = "global"
        elif "--vendor" in args_parts:
            target_level = "vendor"

        src = Path(src_path)
        if not src.exists():
            print(f"  文件不存在: {src}")
            return

        from knowledge.converter import is_direct, is_convertible, process_file
        from config.settings import settings

        if not is_direct(src) and not is_convertible(src):
            print(f"  不支持的格式: {src.suffix}")
            print("  支持: .md / .txt / .pdf / .docx / .pptx / .xlsx")
            return

        kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
        vendor_id = platform_context.vendor.id
        sub_platform_id = platform_context.sub_platform.id

        if target_level == "global":
            target_docs_dir = kb_dir / "common" / "platform_docs"
            level_label = "全局通用"
        elif target_level == "vendor":
            target_docs_dir = kb_dir / vendor_id / "common" / "platform_docs"
            level_label = f"{vendor_id} 厂商公共"
        else:
            target_docs_dir = docs_dir
            level_label = "平台专属"

        target_docs_dir.mkdir(parents=True, exist_ok=True)
        result_path = process_file(src, target_docs_dir)
        if result_path is None:
            print(f"  添加失败")
            return

        print(f"  已添加: {src.name} -> {result_path.name}")
        print(f"  层级: {level_label}")
        print(f"  存储到: {result_path}")
        print(f"  正在自动更新索引...")
        try:
            from knowledge.builder import update_knowledge_base
            result = update_knowledge_base(vendor_id, sub_platform_id)
            if result.get("status") == "up_to_date":
                print("  索引已是最新")
            elif result.get("status") == "updated":
                print(f"  索引更新完成: +{result.get('new',0)} 修改{result.get('changed',0)} -{result.get('deleted',0)}")
        except Exception as e:
            print(f"  自动更新索引失败: {e}，请手动运行 'kb update'")

    elif sub_cmd == "update":
        print("  正在检测知识库变更...")
        try:
            from knowledge.builder import update_knowledge_base
            result = update_knowledge_base(
                platform_context.vendor.id,
                platform_context.sub_platform.id,
            )
            if result.get("status") == "up_to_date":
                print("  知识库已是最新")
            elif result.get("status") == "updated":
                print(f"  更新完成: +{result.get('new',0)} 修改{result.get('changed',0)} -{result.get('deleted',0)}")
            else:
                print(f"  更新结果: {result}")
        except Exception as e:
            print(f"  更新失败: {e}")

    elif sub_cmd == "build":
        print("  正在构建向量索引...")
        try:
            from knowledge.builder import build_knowledge_base
            build_knowledge_base(
                platform_context.vendor.id,
                platform_context.sub_platform.id,
            )
            print("  知识库构建完成")
        except Exception as e:
            print(f"  构建失败: {e}")

    elif sub_cmd == "search":
        if not sub_args:
            print("  用法: kb search <关键词>")
            print("  示例: kb search I2C")
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
    print(f"    平台: {platform_context.vendor.display_name} / {platform_context.sub_platform.display_name}")
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

    print(f"\n  已进入: {context.vendor.display_name} / {context.sub_platform.display_name}")

    print("\n  正在检测知识库变更...")
    try:
        from knowledge.builder import update_knowledge_base
        result = update_knowledge_base(
            context.vendor.id,
            context.sub_platform.id,
        )
        if result.get("status") == "up_to_date":
            print("  知识库已是最新")
        elif result.get("status") == "updated":
            print(f"  知识库已更新: +{result.get('new',0)} 修改{result.get('changed',0)} -{result.get('deleted',0)}")
        elif result.get("status") == "error":
            print(f"  知识库检测跳过: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"  知识库检测跳过: {e}")

    print()
    print("  快速入门:")
    print("    help     - 查看完整帮助")
    print("    kb list  - 查看知识库文件")
    print("    kb add   - 添加知识库文档")
    print("    config   - 查看当前配置")
    print("    quit     - 退出")
    print()
    print("  直接输入问题即可开始对话")
    print()

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
            print(f"\n  已切换到: {context.vendor.display_name} / {context.sub_platform.display_name}\n")
            continue
        if cmd == "help":
            print(HELP_TEXT)
            continue
        if cmd.startswith("kb"):
            handle_kb_command(user_input[2:].strip(), context)
            continue
        if cmd.startswith("platform"):
            handle_platform_command(user_input[8:].strip())
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
