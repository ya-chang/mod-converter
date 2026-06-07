#!/usr/bin/env python3
"""
Minecraft Mod Converter & Refactor Tool
Convert/rebuild mods between versions and loaders (Forge ↔ Fabric)
"""

import argparse
import sys
import os

from src.core.decompiler import Decompiler
from src.core.analyzer import Analyzer
from src.core.rebuilder import Rebuilder
from src.modes.convert import ConvertMode
from src.modes.refactor import RefactorMode


BANNER = """
╔══════════════════════════════════════════════╗
║   Minecraft Mod Converter & Refactor Tool    ║
║   Forge ↔ Fabric | Version Up/Down          ║
╚══════════════════════════════════════════════╝
"""


def detect_mod_info(jar_path: str) -> dict:
    """Auto-detect source mod version and loader from jar metadata."""
    import zipfile
    import json
    import tomllib

    info = {"version": None, "loader": None, "mod_id": None, "name": None}

    with zipfile.ZipFile(jar_path, "r") as zf:
        names = zf.namelist()

        # Forge: META-INF/mods.toml or mcmod.info
        if "META-INF/mods.toml" in names:
            with zf.open("META-INF/mods.toml") as f:
                data = tomllib.loads(f.read().decode("utf-8"))
                mods = data.get("mods", [{}])
                if mods:
                    info["mod_id"] = mods[0].get("modId")
                    info["name"] = mods[0].get("display")
                deps = data.get("dependencies", {})
                for key, dep_list in deps.items():
                    for dep in dep_list:
                        if dep.get("modId") == "forge":
                            info["loader"] = "forge"
                            mc_version = dep.get("versionRange", "")
                            if "[" in mc_version:
                                info["version"] = mc_version.split("[")[1].split(",")[0].strip()
                            break

        # NeoForge: META-INF/neoforge.mods.toml
        if "META-INF/neoforge.mods.toml" in names:
            info["loader"] = "neoforge"
            with zf.open("META-INF/neoforge.mods.toml") as f:
                data = tomllib.loads(f.read().decode("utf-8"))
                mods = data.get("mods", [{}])
                if mods:
                    info["mod_id"] = mods[0].get("modId")
                    info["name"] = mods[0].get("display")

        # Fabric: fabric.mod.json
        if "fabric.mod.json" in names:
            info["loader"] = "fabric"
            with zf.open("fabric.mod.json") as f:
                data = json.loads(f.read().decode("utf-8"))
                info["mod_id"] = data.get("id")
                info["name"] = data.get("name")
                env = data.get("depends", {})
                mc = env.get("minecraft", "")
                if ">=" in mc:
                    info["version"] = mc.replace(">=", "").strip()
                elif mc:
                    info["version"] = mc.strip()

        # Fallback: check class files for Forge/Fabric signatures
        if not info["loader"]:
            for name in names:
                if name.startswith("net/minecraftforge/"):
                    info["loader"] = "forge"
                    break
                if name.startswith("net/fabricmc/"):
                    info["loader"] = "fabric"
                    break

    return info


def print_detected(info: dict):
    print(f"  📦 Mod: {info.get('name', 'Unknown')}")
    print(f"  🔧 Loader: {info.get('loader', 'Unknown')}")
    print(f"  🎮 MC Version: {info.get('version', 'Unknown')}")
    print(f"  🆔 Mod ID: {info.get('mod_id', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Mod Converter & Refactor Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s convert input.jar -t 1.20.1 -l fabric -o output.jar
  %(prog)s refactor input.jar -t 1.20.1 -l fabric --api-key sk-xxx
  %(prog)s analyze input.jar
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- analyze ---
    p_analyze = subparsers.add_parser("analyze", help="Analyze a mod jar")
    p_analyze.add_argument("jar", help="Path to mod jar file")
    p_analyze.add_argument("--deep", action="store_true", help="Deep analysis of all classes")

    # --- convert ---
    p_convert = subparsers.add_parser("convert", help="Rule-based conversion")
    p_convert.add_argument("jar", help="Path to mod jar file")
    p_convert.add_argument("-t", "--target-version", required=True, help="Target MC version (e.g. 1.20.1)")
    p_convert.add_argument("-l", "--target-loader", required=True, choices=["forge", "fabric", "neoforge"],
                           help="Target mod loader")
    p_convert.add_argument("-o", "--output", default=None, help="Output jar path")
    p_convert.add_argument("--keep-mappings", action="store_true", help="Keep obfuscation mappings")

    # --- refactor ---
    p_refactor = subparsers.add_parser("refactor", help="AI-powered code refactoring")
    p_refactor.add_argument("jar", help="Path to mod jar file")
    p_refactor.add_argument("-t", "--target-version", required=True, help="Target MC version")
    p_refactor.add_argument("-l", "--target-loader", required=True, choices=["forge", "fabric", "neoforge"],
                            help="Target mod loader")
    p_refactor.add_argument("-o", "--output", default=None, help="Output directory")
    p_refactor.add_argument("--api-key", default=None, help="OpenAI API key (or set OPENAI_API_KEY env)")
    p_refactor.add_argument("--api-base", default=None, help="API base URL (for compatible providers)")
    p_refactor.add_argument("--model", default="gpt-4o", help="Model to use for refactoring")

    args = parser.parse_args()

    print(BANNER)

    if args.command == "analyze":
        print("🔍 Analyzing mod...\n")
        info = detect_mod_info(args.jar)
        print_detected(info)
        print()

        analyzer = Analyzer(args.jar)
        report = analyzer.analyze(deep=args.deep)
        analyzer.print_report(report)

    elif args.command == "convert":
        print("🔄 Converting mod...\n")
        info = detect_mod_info(args.jar)
        print("Source:")
        print_detected(info)
        print(f"\nTarget: {args.target_version} / {args.target_loader}\n")

        decompiler = Decompiler()
        source_dir = decompiler.decompile(args.jar)

        converter = ConvertMode(
            source_version=info.get("version"),
            source_loader=info.get("loader"),
            target_version=args.target_version,
            target_loader=args.target_loader,
        )
        converted_dir = converter.convert(source_dir)

        rebuilder = Rebuilder()
        output = args.output or f"converted-{args.target_version}-{args.target_loader}.jar"
        rebuilder.build(converted_dir, output, target_version=args.target_version, target_loader=args.target_loader)
        print(f"\n✅ Output: {output}")

    elif args.command == "refactor":
        print("🧠 AI Refactoring mod...\n")
        info = detect_mod_info(args.jar)
        print("Source:")
        print_detected(info)
        print(f"\nTarget: {args.target_version} / {args.target_loader}\n")

        api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("❌ API key required. Use --api-key or set OPENAI_API_KEY env var.")
            sys.exit(1)

        decompiler = Decompiler()
        source_dir = decompiler.decompile(args.jar)

        refactorer = RefactorMode(
            source_version=info.get("version"),
            source_loader=info.get("loader"),
            target_version=args.target_version,
            target_loader=args.target_loader,
            api_key=api_key,
            api_base=args.api_base,
            model=args.model,
        )
        output_dir = args.output or f"refactored-{args.target_version}-{args.target_loader}"
        refactorer.refactor(source_dir, output_dir)
        print(f"\n✅ Output: {output_dir}/")


if __name__ == "__main__":
    main()
