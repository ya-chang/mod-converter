"""
Convert Mode - Rule-based automated conversion.
Applies pattern matching and known mappings to transform source code.
"""

import os
import re
import shutil
from pathlib import Path
from ..utils.mappings import (
    get_mappings, get_version_changes, get_text_transforms,
    FORGE_TO_FABRIC, FABRIC_TO_FORGE,
)


class ConvertMode:
    """Rule-based mod conversion between loaders and versions."""

    def __init__(self, source_version, source_loader, target_version, target_loader):
        self.source_version = source_version
        self.source_loader = source_loader
        self.target_version = target_version
        self.target_loader = target_loader
        self.changes_log = []

    def convert(self, source_dir: str, output_dir: str = None) -> str:
        """Run full conversion pipeline."""
        if output_dir is None:
            output_dir = source_dir + "-converted"

        print(f"🔄 Converting: {self.source_loader} {self.source_version} → {self.target_loader} {self.target_version}")

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

        # Process all Java files
        java_files = list(Path(src_dir).rglob("*.java"))
        print(f"  📄 Processing {len(java_files)} Java files...")

        for jf in java_files:
            rel_path = jf.relative_to(src_dir)
            out_file = out_src / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)

            content = jf.read_text(encoding="utf-8", errors="replace")
            converted = self._convert_file(content, str(jf))
            out_file.write_text(converted, encoding="utf-8")

        # Generate metadata files for target loader
        self._generate_metadata(output_dir)

        # Print summary
        print(f"\n📊 Conversion Summary:")
        print(f"  Total changes: {len(self.changes_log)}")
        categories = {}
        for change in self.changes_log:
            cat = change["category"]
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items()):
            print(f"  - {cat}: {count}")

        return output_dir

    def _convert_file(self, content: str, filepath: str) -> str:
        """Apply all conversion rules to a single file."""
        original = content

        # Step 1: Loader-specific transforms
        if self.source_loader in ("forge", "neoforge") and self.target_loader == "fabric":
            content = self._forge_to_fabric(content, filepath)
        elif self.source_loader == "fabric" and self.target_loader in ("forge", "neoforge"):
            content = self._fabric_to_forge(content, filepath)

        # Step 2: Version transforms
        if self.source_version != self.target_version:
            content = self._version_transform(content, filepath)

        # Step 3: General text transforms
        content = self._apply_text_transforms(content, filepath)

        # Step 4: Clean up
        content = self._cleanup(content)

        return content

    def _forge_to_fabric(self, content: str, filepath: str) -> str:
        """Transform Forge-specific code to Fabric."""

        # 1. Mod class: @Mod annotation → implements ModInitializer
        if "@Mod(" in content:
            content = self._transform_mod_class(content, filepath)

        # 2. Event system: @SubscribeEvent → callback registration
        content = self._transform_events(content, filepath)

        # 3. Registry: DeferredRegister → direct registration
        content = self._transform_registry(content, filepath)

        # 4. Networking: SimpleChannel → Fabric networking
        content = self._transform_networking(content, filepath)

        # 5. Config: Forge config → Fabric config
        content = self._transform_config(content, filepath)

        # 6. Import transformations
        content = self._transform_imports(content, filepath, "forge_to_fabric")

        return content

    def _fabric_to_forge(self, content: str, filepath: str) -> str:
        """Transform Fabric-specific code to Forge."""

        # 1. ModInitializer → @Mod
        if "implements ModInitializer" in content or "implements ClientModInitializer" in content:
            content = self._transform_mod_class_fabric_to_forge(content, filepath)

        # 2. Events: callbacks → @SubscribeEvent
        content = self._transform_events_fabric_to_forge(content, filepath)

        # 3. Registry: direct registration → DeferredRegister
        content = self._transform_registry_fabric_to_forge(content, filepath)

        # 4. Imports
        content = self._transform_imports(content, filepath, "fabric_to_forge")

        return content

    def _transform_mod_class(self, content: str, filepath: str) -> str:
        """Transform Forge @Mod class to Fabric ModInitializer."""
        # Extract mod ID from @Mod annotation
        mod_id_match = re.search(r'@Mod\s*\(\s*["\']?(\w+)["\']?\s*\)', content)
        mod_id = mod_id_match.group(1) if mod_id_match else "modid"
        if not mod_id_match:
            # Handle variable references like @Mod(TestMod.MODID)
            mod_id_match = re.search(r'@Mod\s*\(\s*([\w.]+)\s*\)', content)
            if mod_id_match:
                mod_id = mod_id_match.group(1)

        # Remove @Mod annotation
        content = re.sub(r'@Mod\s*\([^)]*\)\s*\n?', '', content)

        # Remove FML lifecycle imports
        content = re.sub(r'import\s+net\.minecraftforge\.fml\.\w+.*\n', '', content)

        # Add Fabric imports if not present
        if "net.fabricmc.api.ModInitializer" not in content:
            content = content.replace(
                "public class",
                "import net.fabricmc.api.ModInitializer;\n\npublic class",
                1
            )

        # Add implements ModInitializer (handle abstract classes too)
        if "implements" in content:
            content = re.sub(
                r'(public\s+(?:abstract\s+)?class\s+\w+[^{]*?)\{',
                r' implements ModInitializer {',
                content, count=1
            )
        else:
            content = re.sub(
                r'(public\s+(?:abstract\s+)?class\s+\w+)\s*\{',
                r' implements ModInitializer {',
                content, count=1
            )

        # Transform constructor/FMLCommonSetupEvent to onInitialize
        # Find the common setup event handler and convert to onInitialize
        setup_pattern = r'(?:public\s+void\s+\w*\s*\([^)]*FMLCommonSetupEvent[^)]*\)[^{]*\{)'
        if re.search(setup_pattern, content):
            content = re.sub(setup_pattern, '    @Override\n    public void onInitialize() {', content, count=1)
        elif re.search(r'public\s+\w+\s*\([^)]*\)\s*\{', content):
            # Try to find constructor and convert
            content = re.sub(
                r'(public\s+)\w+(\s*\([^)]*\)\s*\{)',
                r'\1void onInitialize\2',
                content, count=1
            )

        self.changes_log.append({"file": filepath, "category": "mod_class", "change": "@Mod → ModInitializer"})
        return content

    def _transform_events(self, content: str, filepath: str) -> str:
        """Transform Forge event system to Fabric callbacks."""
        changes = 0

        # Common event patterns
        event_mappings = {
            r'@SubscribeEvent\s*\n\s*public\s+void\s+\w*\s*\([^)]*ServerTickEvent[^)]*\)': {
                "replacement": "public void onServerTick(MinecraftServer server)",
                "register": "ServerTickEvents.END_SERVER_TICK.register(this::onServerTick);",
                "import": "net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents",
            },
            r'@SubscribeEvent\s*\n\s*public\s+void\s+\w*\s*\([^)]*PlayerLoggedInEvent[^)]*\)': {
                "replacement": "public void onPlayerJoin(ServerPlayerEntity player)",
                "register": "ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> onPlayerJoin(handler.player));",
                "import": "net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents",
            },
            r'@SubscribeEvent\s*\n\s*public\s+void\s+\w*\s*\([^)]*BlockEvent\.BreakEvent[^)]*\)': {
                "replacement": "public boolean onBlockBreak(World world, PlayerEntity player, BlockPos pos, BlockState state, BlockEntity blockEntity)",
                "register": "PlayerBlockBreakEvents.BEFORE.register(this::onBlockBreak);",
                "import": "net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents",
            },
        }

        for pattern, mapping in event_mappings.items():
            if re.search(pattern, content):
                # Remove @SubscribeEvent
                content = re.sub(r'@SubscribeEvent\s*\n', '', content)
                # Replace method signature
                content = re.sub(pattern, mapping["replacement"], content)
                # Add import
                if mapping["import"] not in content:
                    content = self._add_import(content, mapping["import"])
                changes += 1

        # Remove any remaining @SubscribeEvent annotations (catch-all)
        sub_count = len(re.findall(r'@SubscribeEvent\s*\n?', content))
        content = re.sub(r'@SubscribeEvent\s*\n?', '', content)
        if sub_count:
            changes += sub_count

        # Remove EventBus registration
        if re.search(r'MinecraftForge\.EVENT_BUS', content):
            content = re.sub(r'MinecraftForge\.EVENT_BUS\.register\s*\([^)]*\)\s*;?\s*?', '', content)
            changes += 1

        # Remove MinecraftForge import if no more references
        if "MinecraftForge" not in content.replace("import net.minecraftforge.common.MinecraftForge;", ""):
            content = re.sub(r'import\s+net\.minecraftforge\.common\.MinecraftForge\s*;\s*?', '', content)

        if changes:
            self.changes_log.append({"file": filepath, "category": "events", "change": f"{changes} event transformations"})

        return content

    def _transform_registry(self, content: str, filepath: str) -> str:
        """Transform Forge DeferredRegister to Fabric direct registration."""
        changes = 0

        # DeferredRegister.create → direct registration
        # Pattern: DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MODID);
        deferred_pattern = r'DeferredRegister<(\w+)>\s+(\w+)\s*=\s*DeferredRegister\.create\(\s*ForgeRegistries\.(\w+)\s*,\s*["\']?(\w+)["\']?\s*\)\s*;'
        match = re.search(deferred_pattern, content)
        if match:
            reg_type = match.group(1)
            var_name = match.group(2)
            forge_type = match.group(3)
            mod_id = match.group(4)

            # Replace with Fabric-style registration
            content = re.sub(deferred_pattern, f'// Registration: use Registry.register() directly', content)

            # Transform .register() calls
            reg_pattern = rf'{var_name}\.register\s*\(\s*["\'](\w+)["\']\s*,\s*(\w+::\w+|new\s+\w+[^)]*\))\s*\)'
            for reg_match in re.finditer(reg_pattern, content):
                item_id = reg_match.group(1)
                factory = reg_match.group(2)
                fabric_reg = f"Registry.register(Registries.{forge_type}, new Identifier(\"{mod_id}\", \"{item_id}\"), {factory})"
                content = content.replace(reg_match.group(0), fabric_reg)

            # Add imports
            content = self._add_import(content, "net.minecraft.registry.Registry")
            content = self._add_import(content, "net.minecraft.registry.Registries")
            content = self._add_import(content, "net.minecraft.util.Identifier")
            changes += 1

        # RegistryObject → direct reference
        content = re.sub(r'RegistryObject<(\w+)>\s+(\w+)\s*=\s*\w+\.register\([^)]*\);',
                        r'\1 \2; // Registered in onInitialize', content)
        content = re.sub(r'RegistryObject<(\w+)>', r'\1', content)

        # Remove DeferredRegister imports
        content = re.sub(r'import\s+net\.minecraftforge\.registries\.DeferredRegister\s*;\s*\n?', '', content)
        content = re.sub(r'import\s+net\.minecraftforge\.registries\.RegistryObject\s*;\s*\n?', '', content)
        content = re.sub(r'import\s+net\.minecraftforge\.registries\.ForgeRegistries\s*;\s*\n?', '', content)

        if changes:
            self.changes_log.append({"file": filepath, "category": "registry", "change": f"{changes} registry transformations"})

        return content

    def _transform_networking(self, content: str, filepath: str) -> str:
        """Transform Forge networking to Fabric networking."""
        changes = 0

        # SimpleChannel registration
        if "SimpleChannel" in content:
            # Replace SimpleChannel with Fabric networking
            content = re.sub(
                r'(?:private\s+)?(?:static\s+)?(?:final\s+)?SimpleChannel\s+(\w+)\s*=\s*[^;]+;',
                r'// Use ServerPlayNetworking/ClientPlayNetworking for packets',
                content
            )
            content = re.sub(r'import\s+net\.minecraftforge\.network\.simple\.SimpleChannel\s*;\s*\n?', '', content)
            content = self._add_import(content, "net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking")
            changes += 1

        # NetworkRegistry
        if "NetworkRegistry" in content:
            content = re.sub(r'import\s+net\.minecraftforge\.network\.NetworkRegistry\s*;\s*\n?', '', content)
            changes += 1

        if changes:
            self.changes_log.append({"file": filepath, "category": "networking", "change": f"{changes} networking transformations"})

        return content

    def _transform_config(self, content: str, filepath: str) -> str:
        """Transform Forge config to Fabric config approach."""
        if "ForgeConfigSpec" in content or "ModConfigSpec" in content:
            content = re.sub(r'import\s+net\.minecraftforge\.common\.ForgeConfigSpec\s*;\s*\n?', '', content)
            content = re.sub(r'import\s+net\.minecraftforge\.common\.ModConfigSpec\s*;\s*\n?', '', content)
            # Replace ForgeConfigSpec.Builder with a placeholder
            content = content.replace("ForgeConfigSpec.Builder", "/* TODO: Cloth Config Builder */ Object")
            content = content.replace("ForgeConfigSpec", "/* TODO: Cloth Config */ Object")
            content = content.replace("ModConfigSpec", "/* TODO: Cloth Config */ Object")
            # Add comment about config migration
            content = "// TODO: Migrate config to Cloth Config API or manual JSON config\n" + content
            self.changes_log.append({"file": filepath, "category": "config", "change": "Config system needs manual migration"})
        return content

    def _transform_imports(self, content: str, filepath: str, direction: str) -> str:
        """Transform import statements."""
        transforms = get_text_transforms(
            self.source_loader, self.target_loader,
            self.source_version, self.target_version
        )

        import_changes = transforms.get("import", {})
        count = 0
        if direction == "forge_to_fabric":
            for old_import, new_import in import_changes.items():
                if old_import in content:
                    content = content.replace(f"import {old_import}", f"import {new_import}")
                    count += 1
        elif direction == "fabric_to_forge":
            # Apply reverse: replace fabric imports with forge imports
            for forge_import, fabric_import in import_changes.items():
                if fabric_import in content:
                    content = content.replace(f"import {fabric_import}", f"import {forge_import}")
                    count += 1

        if count:
            self.changes_log.append({"file": filepath, "category": "imports", "change": f"{count} import transformations"})

        return content

    def _version_transform(self, content: str, filepath: str) -> str:
        """Apply version-specific transforms."""
        changes = get_version_changes(self.source_version, self.target_version)
        if not changes.get("changes"):
            return content

        for change in changes["changes"]:
            if "pattern_old" in change and "pattern_new" in change:
                matches = re.findall(change["pattern_old"], content)
                if matches:
                    # Add TODO comment for complex changes
                    content = f"// TODO: Version change ({self.source_version} → {self.target_version}): {change['note']}\n" + content
                    self.changes_log.append({
                        "file": filepath,
                        "category": "version",
                        "change": change.get("note", "version transform"),
                    })

        return content

    def _apply_text_transforms(self, content: str, filepath: str) -> str:
        """Apply general text-based transforms."""
        transforms = get_text_transforms(
            self.source_loader, self.target_loader,
            self.source_version, self.target_version
        )

        # Package renames
        count = 0
        for old_pkg, new_pkg in transforms.get("package", {}).items():
            if old_pkg in content:
                content = content.replace(old_pkg, new_pkg)
                count += 1

        # Class name renames
        class_map = transforms.get("class", {})
        for old_class, new_class in sorted(class_map.items(), key=lambda x: -len(x[0])):
            # Only replace standalone class names (word boundary)
            pattern = r'\b' + re.escape(old_class) + r'\b'
            if re.search(pattern, content):
                content = re.sub(pattern, new_class, content)
                count += 1

        # Method renames
        for old_method, new_method in transforms.get("method", {}).items():
            if old_method in content:
                content = content.replace(old_method, new_method)
                count += 1

        # Version-specific method changes
        ver_transforms = transforms.get("version", {}).get("method_changes", {})
        for old_method, new_method in ver_transforms.items():
            if old_method in content:
                content = content.replace(old_method, new_method)
                count += 1

        if count:
            self.changes_log.append({"file": filepath, "category": "text_transform", "change": f"{count} text replacements"})

        return content

    def _transform_mod_class_fabric_to_forge(self, content: str, filepath: str) -> str:
        """Transform Fabric ModInitializer to Forge @Mod class."""
        # Add @Mod annotation
        mod_id = "modid"  # Default, should be detected from fabric.mod.json
        content = re.sub(
            r'(public\s+class\s+(\w+)[^{]*?)implements\s+(?:Client)?ModInitializer\s*',
            rf'@Mod("{mod_id}")\n\1',
            content, count=1
        )

        # onInitialize → constructor or setup event
        content = re.sub(
            r'@Override\s*\n\s*public\s+void\s+onInitialize\s*\(\s*\)',
            'public void onCommonSetup(FMLCommonSetupEvent event)',
            content
        )

        # Add Forge imports
        content = self._add_import(content, "net.minecraftforge.fml.common.Mod")
        content = self._add_import(content, "net.minecraftforge.event.lifecycle.FMLCommonSetupEvent")

        # Remove Fabric imports
        content = re.sub(r'import\s+net\.fabricmc\.api\.\w+\s*;\s*\n?', '', content)

        self.changes_log.append({"file": filepath, "category": "mod_class", "change": "ModInitializer → @Mod"})
        return content

    def _transform_events_fabric_to_forge(self, content: str, filepath: str) -> str:
        """Transform Fabric event callbacks to Forge @SubscribeEvent."""
        # This is a simplified reverse transform
        event_replacements = {
            "ServerTickEvents.END_SERVER_TICK.register": "// TODO: Add @SubscribeEvent for TickEvent.ServerTickEvent\n// ServerTickEvents.END_SERVER_TICK.register",
            "ServerPlayConnectionEvents.JOIN.register": "// TODO: Add @SubscribeEvent for PlayerLoggedInEvent\n// ServerPlayConnectionEvents.JOIN.register",
            "PlayerBlockBreakEvents.BEFORE.register": "// TODO: Add @SubscribeEvent for BlockEvent.BreakEvent\n// PlayerBlockBreakEvents.BEFORE.register",
        }

        for fabric_pattern, forge_comment in event_replacements.items():
            if fabric_pattern in content:
                content = content.replace(fabric_pattern, forge_comment)
                self.changes_log.append({"file": filepath, "category": "events", "change": f"Fabric → Forge event"})

        return content

    def _transform_registry_fabric_to_forge(self, content: str, filepath: str) -> str:
        """Transform Fabric direct registration to Forge DeferredRegister."""
        # Registry.register → DeferredRegister pattern
        reg_pattern = r'Registry\.register\s*\(\s*Registries\.(\w+)\s*,\s*new\s+Identifier\s*\(\s*["\'](\w+)["\']\s*,\s*["\'](\w+)["\']\s*\)\s*,\s*([^)]+)\)'
        matches = list(re.finditer(reg_pattern, content))

        if matches:
            first_match = matches[0]
            reg_type = first_match.group(1)
            mod_id = first_match.group(2)

            # Add DeferredRegister declaration
            deferred_decl = f'DeferredRegister<{reg_type}> {reg_type.upper()}S = DeferredRegister.create(ForgeRegistries.{reg_type.upper()}S, "{mod_id}");\n'
            content = deferred_decl + content

            # Replace each registration
            for m in reversed(matches):
                item_id = m.group(3)
                factory = m.group(4)
                reg_call = f'{reg_type.upper()}S.register("{item_id}", () -> {factory})'
                content = content[:m.start()] + reg_call + content[m.end():]

            content = self._add_import(content, "net.minecraftforge.registries.DeferredRegister")
            content = self._add_import(content, "net.minecraftforge.registries.ForgeRegistries")
            self.changes_log.append({"file": filepath, "category": "registry", "change": f"{len(matches)} registrations → DeferredRegister"})

        # Remove Fabric imports
        content = re.sub(r'import\s+net\.minecraft\.registry\.Registry\s*;\s*\n?', '', content)
        content = re.sub(r'import\s+net\.minecraft\.registry\.Registries\s*;\s*\n?', '', content)

        return content

    def _add_import(self, content: str, import_path: str) -> str:
        """Add an import statement if not already present."""
        if import_path in content:
            return content
        # Find the last existing import
        last_import = content.rfind("import ")
        if last_import >= 0:
            end_of_line = content.find("\n", last_import)
            content = content[:end_of_line + 1] + f"import {import_path};\n" + content[end_of_line + 1:]
        else:
            # Add after package declaration
            pkg_end = content.find("\n", content.find("package "))
            if pkg_end >= 0:
                content = content[:pkg_end + 1] + f"\nimport {import_path};\n" + content[pkg_end + 1:]
        return content

    def _cleanup(self, content: str) -> str:
        """Clean up converted code."""
        # Remove double blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        # Remove empty import lines
        content = re.sub(r'import\s*;\s*\n', '', content)
        return content

    def _generate_metadata(self, output_dir: str):
        """Generate metadata files for target loader."""
        if self.target_loader == "fabric":
            self._generate_fabric_mod_json(output_dir)
        elif self.target_loader in ("forge", "neoforge"):
            self._generate_forge_mods_toml(output_dir)

    def _generate_fabric_mod_json(self, output_dir: str):
        """Generate fabric.mod.json."""
        fabric_json = {
            "schemaVersion": 1,
            "id": "converted_mod",
            "version": "1.0.0",
            "name": "Converted Mod",
            "environment": "*",
            "entrypoints": {
                "main": ["com.example.converted.ConvertedMod"]
            },
            "depends": {
                "fabricloader": ">=0.14.0",
                "fabric-api": "*",
                "minecraft": f"~{self.target_version}"
            }
        }

        import json
        meta_dir = os.path.join(output_dir, "resources")
        os.makedirs(meta_dir, exist_ok=True)
        with open(os.path.join(meta_dir, "fabric.mod.json"), "w") as f:
            json.dump(fabric_json, f, indent=2)
        print("  📝 Generated fabric.mod.json")

    def _generate_forge_mods_toml(self, output_dir: str):
        """Generate META-INF/mods.toml."""
        mods_toml = f'''modLoader = "javafml"
loaderVersion = "[47,)"
license = "All Rights Reserved"

[[mods]]
modId = "converted_mod"
version = "1.0.0"
displayName = "Converted Mod"

[[dependencies.converted_mod]]
modId = "forge"
mandatory = true
versionRange = "[47,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.converted_mod]]
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
