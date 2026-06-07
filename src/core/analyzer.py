"""
Analyzer module - Understands mod structure, dependencies, and API usage.
Generates a report of what the mod does and what needs to change.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict


# Known API patterns for detection
FORGE_PATTERNS = {
    "event_system": [
        r"@SubscribeEvent",
        r"import\s+net\.minecraftforge\.event",
        r"MinecraftForge\.EVENT_BUS",
        r"EventBus\.register",
    ],
    "registry": [
        r"@ObjectHolder",
        r"DeferredRegister",
        r"ForgeRegistries\.",
        r"RegistryObject<",
        r"import\s+net\.minecraftforge\.registries",
    ],
    "capabilities": [
        r"ICapabilityProvider",
        r"LazyOptional",
        r"@CapabilityInject",
        r"Capability<",
        r"import\s+net\.minecraftforge\.common\.capabilities",
    ],
    "networking": [
        r"SimpleChannel",
        r"NetworkRegistry",
        r"import\s+net\.minecraftforge\.network",
    ],
    "config": [
        r"ModConfigSpec",
        r"ForgeConfigSpec",
        r"@Config\(",
        r"import\s+net\.minecraftforge\.common\.ModConfig",
    ],
    "mixin": [
        r"@Mixin",
        r"@Inject",
        r"@Redirect",
        r"@Overwrite",
    ],
    "entities": [
        r"EntityType\.Builder",
        r"registerEntityRenderingHandler",
        r"import\s+net\.minecraftforge\.entity",
    ],
    "items_blocks": [
        r"extends\s+Item\b",
        r"extends\s+Block\b",
        r"extends\s+BlockItem",
        r"ItemProperties",
        r"BlockBehaviour\.Properties",
    ],
    "gui": [
        r"AbstractContainerScreen",
        r"MenuType",
        r"ContainerLevelAccess",
        r"Screen\b.*extends",
    ],
    "rendering": [
        r"RenderType",
        r"BakedModel",
        r"BlockEntityRenderer",
        r"import\s+net\.minecraft\.client\.renderer",
    ],
}

FABRIC_PATTERNS = {
    "event_system": [
        r"ServerLifecycleEvents",
        r"ServerTickEvents",
        r"AttackBlockCallback",
        r"import\s+net\.fabricmc\.fabric\.api\.event",
        r"ServerPlayConnectionEvents",
    ],
    "registry": [
        r"Registry\.register",
        r"\bRegistries\.",
        r"import\s+net\.fabricmc\.fabric\.api\.object\.builder",
    ],
    "networking": [
        r"ServerPlayNetworking",
        r"ClientPlayNetworking",
        r"import\s+net\.fabricmc\.fabric\.api\.networking",
    ],
    "config": [
        r"ModConfig",
        r"import\s+net\.fabricmc\.loader\.api",
    ],
    "mixin": [
        r"@Mixin",
        r"@Inject",
        r"@Redirect",
        r"@Overwrite",
    ],
    "items_blocks": [
        r"extends\s+Item\b",
        r"extends\s+Block\b",
        r"FabricItemSettings",
        r"FabricBlockSettings",
    ],
    "gui": [
        r"HandledScreen",
        r"ScreenHandler",
        r"ScreenHandlerContext",
    ],
    "rendering": [
        r"RenderLayer",
        r"BakedModel",
        r"BlockEntityRenderer",
    ],
}


class Analyzer:
    """Analyzes mod source code to understand structure and API usage."""

    def __init__(self, jar_path: str = None, source_dir: str = None):
        self.jar_path = jar_path
        self.source_dir = source_dir

    def _get_java_files(self, directory: str) -> list:
        """Recursively find all Java files."""
        return list(Path(directory).rglob("*.java"))

    def _read_file_safe(self, path: str) -> str:
        """Read file with encoding fallback."""
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                return Path(path).read_text(encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return ""

    def analyze(self, deep: bool = False) -> dict:
        """Run full analysis on source code."""
        report = {
            "structure": {},
            "api_usage": defaultdict(list),
            "dependencies": [],
            "complexity": {},
            "classes": [],
            "warnings": [],
        }

        # Analyze jar metadata if available
        if self.jar_path:
            report["metadata"] = self._analyze_jar_metadata()

        # Analyze source files
        if self.source_dir:
            src_dir = self.source_dir
        elif self.jar_path:
            # Will be set by decompiler before calling this
            return report
        else:
            return report

        java_files = self._get_java_files(src_dir)
        report["structure"]["total_files"] = len(java_files)
        if not java_files:
            report["warnings"].append("No Java source files found")
            return report

        # Scan each file
        all_imports = set()
        package_counts = defaultdict(int)

        for jf in java_files:
            content = self._read_file_safe(str(jf))
            if not content:
                continue

            # Extract package
            pkg_match = re.search(r"package\s+([\w.]+);", content)
            if pkg_match:
                pkg = pkg_match.group(1)
                package_counts[pkg] += 1

            # Extract imports
            imports = re.findall(r"import\s+([\w.]+);", content)
            all_imports.update(imports)

            # Detect API patterns (Forge)
            for category, patterns in FORGE_PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        report["api_usage"][f"forge:{category}"].append({
                            "file": str(jf),
                            "pattern": pattern,
                            "count": len(matches),
                        })

            # Detect API patterns (Fabric)
            for category, patterns in FABRIC_PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        report["api_usage"][f"fabric:{category}"].append({
                            "file": str(jf),
                            "pattern": pattern,
                            "count": len(matches),
                        })

            # Class analysis
            class_info = self._analyze_class(content, str(jf))
            if class_info:
                report["classes"].append(class_info)

            if deep:
                # Count lines, methods, fields
                lines = content.count("\n")
                methods = len(re.findall(r"(public|private|protected)\s+\w+\s+\w+\s*\(", content))
                fields = len(re.findall(r"(public|private|protected)\s+(static\s+)?(final\s+)?\w+\s+\w+\s*[;=]", content))
                report["classes"][-1].update({
                    "lines": lines,
                    "methods": methods,
                    "fields": fields,
                })

        # Package structure
        report["structure"]["packages"] = dict(
            sorted(package_counts.items(), key=lambda x: -x[1])[:20]
        )

        # Dependencies from imports
        mc_imports = [i for i in all_imports if i.startswith("net.minecraft")]
        forge_imports = [i for i in all_imports if i.startswith("net.minecraftforge")]
        fabric_imports = [i for i in all_imports if i.startswith("net.fabricmc")]
        other_imports = [i for i in all_imports if not any(i.startswith(p) for p in
                         ["net.minecraft", "net.minecraftforge", "net.fabricmc", "java.", "javax."])]

        report["dependencies"] = {
            "minecraft": sorted(mc_imports),
            "forge": sorted(forge_imports),
            "fabric": sorted(fabric_imports),
            "third_party": sorted(other_imports),
        }

        # Complexity assessment
        forge_score = sum(len(v) for k, v in report["api_usage"].items() if k.startswith("forge:"))
        fabric_score = sum(len(v) for k, v in report["api_usage"].items() if k.startswith("fabric:"))

        total_patterns = forge_score + fabric_score
        if forge_score > fabric_score * 3:
            report["complexity"]["detected_loader"] = "forge"
        elif fabric_score > forge_score * 3:
            report["complexity"]["detected_loader"] = "fabric"
        else:
            report["complexity"]["detected_loader"] = "mixed"

        report["complexity"]["forge_score"] = forge_score
        report["complexity"]["fabric_score"] = fabric_score
        report["complexity"]["total_api_patterns"] = total_patterns

        # Difficulty rating
        if total_patterns < 10:
            report["complexity"]["difficulty"] = "easy"
        elif total_patterns < 30:
            report["complexity"]["difficulty"] = "medium"
        else:
            report["complexity"]["difficulty"] = "hard"

        return report

    def _analyze_jar_metadata(self) -> dict:
        """Extract metadata from jar."""
        import zipfile
        import tomllib

        meta = {}
        try:
            with zipfile.ZipFile(self.jar_path, "r") as zf:
                names = zf.namelist()

                if "META-INF/mods.toml" in names:
                    with zf.open("META-INF/mods.toml") as f:
                        meta["mods_toml"] = tomllib.loads(f.read().decode("utf-8"))

                if "fabric.mod.json" in names:
                    with zf.open("fabric.mod.json") as f:
                        meta["fabric_mod_json"] = json.loads(f.read().decode("utf-8"))

                if "quilt.mod.json" in names:
                    with zf.open("quilt.mod.json") as f:
                        meta["quilt_mod_json"] = json.loads(f.read().decode("utf-8"))

        except Exception as e:
            meta["error"] = str(e)

        return meta

    def _analyze_class(self, content: str, filepath: str) -> dict:
        """Analyze a single Java class."""
        info = {"file": filepath}

        # Class name and type
        class_match = re.search(
            r"(public\s+)?(abstract\s+)?(class|interface|enum)\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?",
            content
        )
        if not class_match:
            return None

        info["type"] = class_match.group(3)  # class/interface/enum
        info["name"] = class_match.group(4)
        info["extends"] = class_match.group(5)
        info["implements"] = [
            i.strip() for i in (class_match.group(6) or "").split(",") if i.strip()
        ]

        # Check if it's a main mod class
        if "@Mod" in content or "onInitialize" in content or "ModInitializer" in content:
            info["role"] = "main_class"
        elif "extends Item" in content:
            info["role"] = "item"
        elif "extends Block" in content:
            info["role"] = "block"
        elif "extends BlockEntity" in content or "extends BlockEntityRenderer" in content:
            info["role"] = "block_entity"
        elif "extends Entity" in content or "extends EntityType" in content:
            info["role"] = "entity"
        elif "Screen" in content and ("extends" in content):
            info["role"] = "gui"
        elif "@Mixin" in content:
            info["role"] = "mixin"

        return info

    def print_report(self, report: dict):
        """Pretty-print the analysis report."""
        print("=" * 50)
        print("📊 MOD ANALYSIS REPORT")
        print("=" * 50)

        # Structure
        struct = report.get("structure", {})
        print(f"\n📁 Structure:")
        print(f"  Total Java files: {struct.get('total_files', 0)}")

        if struct.get("packages"):
            print(f"  Top packages:")
            for pkg, count in list(struct["packages"].items())[:10]:
                print(f"    {pkg}: {count} files")

        # API Usage
        api = report.get("api_usage", {})
        if api:
            print(f"\n🔌 API Usage:")
            for category, usages in sorted(api.items()):
                total = sum(u["count"] for u in usages)
                print(f"  {category}: {total} usages in {len(usages)} files")

        # Dependencies
        deps = report.get("dependencies", {})
        if deps:
            print(f"\n📚 Dependencies:")
            print(f"  Minecraft APIs: {len(deps.get('minecraft', []))} imports")
            print(f"  Forge APIs: {len(deps.get('forge', []))} imports")
            print(f"  Fabric APIs: {len(deps.get('fabric', []))} imports")
            print(f"  Third-party: {len(deps.get('third_party', []))} imports")

            if deps.get("third_party"):
                print(f"\n  Third-party libraries:")
                for lib in deps["third_party"][:15]:
                    print(f"    - {lib}")

        # Complexity
        cx = report.get("complexity", {})
        if cx:
            print(f"\n⚡ Complexity:")
            print(f"  Detected loader: {cx.get('detected_loader', 'unknown')}")
            print(f"  Difficulty: {cx.get('difficulty', 'unknown')}")
            print(f"  API pattern count: {cx.get('total_api_patterns', 0)}")

        # Classes by role
        classes = report.get("classes", [])
        roles = defaultdict(list)
        for c in classes:
            role = c.get("role", "other")
            roles[role].append(c["name"])

        if roles:
            print(f"\n🏗️  Classes by role:")
            for role, names in sorted(roles.items()):
                print(f"  {role}: {len(names)}")
                if len(names) <= 5:
                    for n in names:
                        print(f"    - {n}")

        # Warnings
        if report.get("warnings"):
            print(f"\n⚠️  Warnings:")
            for w in report["warnings"]:
                print(f"  - {w}")

        print("\n" + "=" * 50)
