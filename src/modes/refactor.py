"""
Refactor Mode - AI-powered semantic code refactoring.
Understands what the code does, then rewrites it for the target version/loader.
"""

import os
import re
import json
import shutil
from pathlib import Path


# System prompt for the AI refactoring
SYSTEM_PROMPT = """You are an expert Minecraft mod developer. You deeply understand both Forge and Fabric mod loaders,
and all Minecraft versions from 1.16 to 1.21+.

Your task: Given Java source code from a Minecraft mod, REWRITE it for the target loader and version.
Do NOT just do text replacement. Think about:
1. What does this code DO? (its purpose and logic)
2. What APIs/patterns does it use on the source platform?
3. What is the CORRECT way to achieve the same result on the target platform?
4. Are there better patterns available on the target platform?

Rules:
- Output ONLY the rewritten Java code, no explanations
- Keep the same package structure and class names where possible
- Use the idiomatic patterns of the target loader (not awkward translations)
- Add TODO comments for anything that needs manual verification
- Preserve the mod's functionality, not its exact implementation
- Include all necessary imports for the target platform
- Make sure the code would actually compile on the target platform
"""


class RefactorMode:
    """AI-powered mod refactoring."""

    def __init__(self, source_version, source_loader, target_version, target_loader,
                 api_key, api_base=None, model="gpt-4o"):
        self.source_version = source_version
        self.source_loader = source_loader
        self.target_version = target_version
        self.target_loader = target_loader
        self.api_key = api_key
        self.api_base = api_base or "https://api.openai.com/v1"
        self.model = model
        self.refactor_log = []

    def refactor(self, source_dir: str, output_dir: str):
        """Full refactoring pipeline."""
        print(f"🧠 AI Refactoring: {self.source_loader} {self.source_version} → {self.target_loader} {self.target_version}")
        print(f"  🤖 Model: {self.model}")

        src_dir = os.path.join(source_dir, "src")
        if not os.path.isdir(src_dir):
            src_dir = source_dir

        out_src = os.path.join(output_dir, "src")
        os.makedirs(out_src, exist_ok=True)

        # Copy resources
        res_dir = os.path.join(source_dir, "resources")
        if os.path.isdir(res_dir):
            out_res = os.path.join(output_dir, "resources")
            shutil.copytree(res_dir, out_res, dirs_exist_ok=True)

        # Process files in dependency order
        java_files = self._sort_by_dependency(list(Path(src_dir).rglob("*.java")))
        print(f"  📄 Processing {len(java_files)} Java files...")

        # First pass: analyze the whole project
        project_context = self._build_project_context(java_files, src_dir)

        # Second pass: refactor each file with full context
        for i, jf in enumerate(java_files):
            rel_path = jf.relative_to(src_dir)
            out_file = out_src / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)

            content = jf.read_text(encoding="utf-8", errors="replace")
            print(f"  [{i+1}/{len(java_files)}] Refactoring: {rel_path}")

            refactored = self._refactor_file(content, str(jf), project_context)
            out_file.write_text(refactored, encoding="utf-8")

        # Generate metadata
        self._generate_metadata(output_dir)

        print(f"\n📊 Refactoring Summary:")
        print(f"  Files processed: {len(java_files)}")
        print(f"  Issues flagged: {sum(1 for l in self.refactor_log if 'TODO' in l.get('note', ''))}")

    def _build_project_context(self, java_files: list, src_dir: str) -> str:
        """Build a context summary of the entire project for the AI."""
        context_parts = []
        class_map = {}

        for jf in java_files:
            content = jf.read_text(encoding="utf-8", errors="replace")
            rel = jf.relative_to(src_dir)

            # Extract class info
            class_match = re.search(r'(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)', content)
            if class_match:
                class_name = class_match.group(1)
                class_map[class_name] = str(rel)

            # Extract package and key info
            pkg_match = re.search(r'package\s+([\w.]+);', content)
            pkg = pkg_match.group(1) if pkg_match else "unknown"

            # Count key features
            features = []
            if "@Mod" in content or "ModInitializer" in content:
                features.append("MAIN_CLASS")
            if "@SubscribeEvent" in content:
                features.append("EVENTS")
            if "DeferredRegister" in content:
                features.append("REGISTRY")
            if "SimpleChannel" in content:
                features.append("NETWORKING")
            if "@Mixin" in content:
                features.append("MIXIN")
            if "extends Item" in content:
                features.append("ITEM")
            if "extends Block" in content:
                features.append("BLOCK")
            if "Screen" in content:
                features.append("GUI")

            context_parts.append(f"File: {rel} | Package: {pkg} | Features: {', '.join(features) or 'utility'}")

        summary = "=== PROJECT STRUCTURE ===\n"
        summary += "\n".join(context_parts)
        summary += f"\n\n=== CLASS MAP ===\n"
        for cls, path in class_map.items():
            summary += f"{cls} → {path}\n"

        return summary

    def _refactor_file(self, content: str, filepath: str, project_context: str) -> str:
        """Refactor a single file using AI."""
        # Build the prompt
        user_prompt = self._build_prompt(content, filepath, project_context)

        try:
            result = self._call_ai(user_prompt)
            if result:
                # Validate the result has basic structure
                if "class " in result or "interface " in result:
                    self.refactor_log.append({
                        "file": filepath,
                        "status": "refactored",
                        "note": "AI refactored successfully",
                    })
                    return result
                else:
                    self.refactor_log.append({
                        "file": filepath,
                        "status": "fallback",
                        "note": "AI output invalid, using rule-based conversion",
                    })
                    return self._fallback_convert(content)
            else:
                self.refactor_log.append({
                    "file": filepath,
                    "status": "error",
                    "note": "AI call failed, using rule-based conversion",
                })
                return self._fallback_convert(content)

        except Exception as e:
            self.refactor_log.append({
                "file": filepath,
                "status": "error",
                "note": str(e),
            })
            return self._fallback_convert(content)

    def _build_prompt(self, content: str, filepath: str, project_context: str) -> str:
        """Build the refactoring prompt for a single file."""
        prompt = f"""Refactor this Minecraft mod Java file.

Source: {self.source_loader} for Minecraft {self.source_version}
Target: {self.target_loader} for Minecraft {self.target_version}

{project_context}

=== SOURCE CODE ({filepath}) ===
{content}

=== TASK ===
Rewrite this code for {self.target_loader} on Minecraft {self.target_version}.
- Use the idiomatic APIs and patterns of the target loader
- Preserve all functionality
- Add TODO comments where manual verification is needed
- Output ONLY the Java code, no markdown or explanations
"""
        return prompt

    def _call_ai(self, user_prompt: str) -> str:
        """Call the AI API for refactoring."""
        import urllib.request
        import ssl

        url = f"{self.api_base}/chat/completions"

        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 8000,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        # Allow custom SSL context
        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"    ⚠️  AI API error: {e}")
            return None

    def _fallback_convert(self, content: str) -> str:
        """Fallback: rule-based conversion (same as ConvertMode)."""
        from .convert import ConvertMode
        converter = ConvertMode(
            self.source_version, self.source_loader,
            self.target_version, self.target_loader
        )
        return converter._convert_file(content, "fallback")

    def _sort_by_dependency(self, java_files: list) -> list:
        """Sort files so dependencies are processed first (simple heuristic)."""
        # Main mod class last, utilities first
        main_classes = []
        other_classes = []

        for jf in java_files:
            try:
                content = jf.read_text(encoding="utf-8", errors="replace")
                if "@Mod(" in content or "ModInitializer" in content or "ClientModInitializer" in content:
                    main_classes.append(jf)
                else:
                    other_classes.append(jf)
            except Exception:
                other_classes.append(jf)

        return other_classes + main_classes

    def _generate_metadata(self, output_dir: str):
        """Generate metadata for target loader."""
        if self.target_loader == "fabric":
            fabric_json = {
                "schemaVersion": 1,
                "id": "refactored_mod",
                "version": "1.0.0",
                "name": "Refactored Mod",
                "environment": "*",
                "entrypoints": {
                    "main": ["com.example.refactored.RefactoredMod"]
                },
                "depends": {
                    "fabricloader": ">=0.14.0",
                    "fabric-api": "*",
                    "minecraft": f"~{self.target_version}"
                }
            }
            meta_dir = os.path.join(output_dir, "resources")
            os.makedirs(meta_dir, exist_ok=True)
            with open(os.path.join(meta_dir, "fabric.mod.json"), "w") as f:
                json.dump(fabric_json, f, indent=2)
            print("  📝 Generated fabric.mod.json")
        elif self.target_loader in ("forge", "neoforge"):
            mods_toml = f'''modLoader = "javafml"
loaderVersion = "[47,)"
license = "All Rights Reserved"

[[mods]]
modId = "refactored_mod"
version = "1.0.0"
displayName = "Refactored Mod"

[[dependencies.refactored_mod]]
modId = "forge"
mandatory = true
versionRange = "[47,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.refactored_mod]]
modId = "minecraft"
mandatory = true
versionRange = "[{self.target_version},)"
ordering = "NONE"
side = "BOTH"
'''
            meta_dir = os.path.join(output_dir, "resources", "META-INF")
            os.makedirs(meta_dir, exist_ok=True)
            with open(os.path.join(meta_dir, "mods.toml"), "w") as f:
                f.write(mods_toml)
            print("  📝 Generated META-INF/mods.toml")
