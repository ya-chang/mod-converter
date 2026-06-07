"""
Tests for the mod converter tool.
"""

import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.mappings import (
    FORGE_TO_FABRIC, FABRIC_TO_FORGE, get_mappings,
    get_version_changes, get_text_transforms,
)
from src.core.analyzer import Analyzer, FORGE_PATTERNS, FABRIC_PATTERNS


class TestMappings:
    """Test the API mapping system."""

    def test_forge_to_fabric_not_empty(self):
        assert len(FORGE_TO_FABRIC) > 0

    def test_fabric_to_forge_not_empty(self):
        assert len(FABRIC_TO_FORGE) > 0

    def test_get_mappings_forge_to_fabric(self):
        mappings = get_mappings("forge", "fabric")
        assert len(mappings) > 0
        assert all("fabric" in v for v in mappings.values())

    def test_get_mappings_fabric_to_forge(self):
        mappings = get_mappings("fabric", "forge")
        assert len(mappings) > 0

    def test_get_version_changes_known(self):
        changes = get_version_changes("1.20.1", "1.21")
        assert "changes" in changes
        assert len(changes["changes"]) > 0

    def test_get_version_changes_unknown(self):
        changes = get_version_changes("1.0.0", "2.0.0")
        assert "changes" in changes

    def test_get_text_transforms(self):
        transforms = get_text_transforms("forge", "fabric", "1.20.1", "1.21")
        assert "package" in transforms
        assert "import" in transforms

    def test_mod_class_mapping(self):
        assert "net.minecraftforge.fml.common.Mod" in FORGE_TO_FABRIC
        mapping = FORGE_TO_FABRIC["net.minecraftforge.fml.common.Mod"]
        assert "ModInitializer" in mapping["fabric"]

    def test_registry_mapping(self):
        assert "net.minecraftforge.registries.DeferredRegister" in FORGE_TO_FABRIC
        mapping = FORGE_TO_FABRIC["net.minecraftforge.registries.DeferredRegister"]
        assert "Registry" in mapping["fabric"]


class TestAnalyzer:
    """Test the code analyzer."""

    def test_forge_pattern_detection(self):
        """Test that Forge patterns are detected in sample code."""
        sample = '''
@Mod("testmod")
public class TestMod {
    @SubscribeEvent
    public void onTick(TickEvent.ServerTickEvent event) {
        MinecraftForge.EVENT_BUS.register(this);
    }
}
'''
        # Check patterns match
        for category, patterns in FORGE_PATTERNS.items():
            for pattern in patterns:
                import re
                if re.search(pattern, sample):
                    # Found a forge pattern
                    assert True
                    return
        assert False, "No Forge patterns detected in sample Forge code"

    def test_fabric_pattern_detection(self):
        """Test that Fabric patterns are detected in sample code."""
        sample = '''
public class TestMod implements ModInitializer {
    @Override
    public void onInitialize() {
        Registry.register(Registries.ITEM, new Identifier("testmod", "test_item"), new TestItem());
    }
}
'''
        for category, patterns in FABRIC_PATTERNS.items():
            for pattern in patterns:
                import re
                if re.search(pattern, sample):
                    assert True
                    return
        assert False, "No Fabric patterns detected in sample Fabric code"

    def test_analyzer_class_analysis(self):
        """Test class analysis on sample code."""
        analyzer = Analyzer()
        sample = '''
@Mod("testmod")
public class TestMod {
    public TestMod() {
        FMLJavaModLoadingContext.get().getModEventBus().register(this);
    }
}
'''
        result = analyzer._analyze_class(sample, "TestMod.java")
        assert result is not None
        assert result["name"] == "TestMod"
        assert result["type"] == "class"


class TestConvertMode:
    """Test the rule-based conversion mode."""

    def _get_converter(self):
        from src.modes.convert import ConvertMode
        return ConvertMode("1.20.1", "forge", "1.20.1", "fabric")

    def test_mod_class_transform(self):
        converter = self._get_converter()
        source = '''
@Mod("mymod")
public class MyMod {
    public MyMod() {
        FMLJavaModLoadingContext.get().getModEventBus().register(this);
    }

    private void setup(final FMLCommonSetupEvent event) {
        // setup code
    }
}
'''
        result = converter._transform_mod_class(source, "MyMod.java")
        assert "ModInitializer" in result
        assert "@Mod" not in result
        assert "onInitialize" in result

    def test_registry_transform(self):
        converter = self._get_converter()
        source = '''
public class ModItems {
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, "mymod");
    public static final RegistryObject<Item> TEST_ITEM = ITEMS.register("test_item", () -> new Item(new Item.Properties()));
}
'''
        result = converter._transform_registry(source, "ModItems.java")
        assert "DeferredRegister" not in result
        assert "Registry.register" in result or "Registration" in result

    def test_import_transform(self):
        converter = self._get_converter()
        source = 'import net.minecraftforge.fml.common.Mod;\nimport net.minecraftforge.event;\n'
        result = converter._transform_imports(source, "test.java", "forge_to_fabric")
        assert "fml.common.Mod" not in result or "fabricmc" in result

    def test_add_import(self):
        converter = self._get_converter()
        source = 'package com.test;\n\nimport java.util.List;\n\nclass Foo {}'
        result = converter._add_import(source, "net.minecraft.util.Identifier")
        assert "import net.minecraft.util.Identifier;" in result


class TestRefactorMode:
    """Test the AI refactoring mode (mocked)."""

    def test_prompt_building(self):
        from src.modes.refactor import RefactorMode
        refactorer = RefactorMode(
            "1.20.1", "forge", "1.20.1", "fabric",
            api_key="test-key", model="test-model"
        )
        prompt = refactorer._build_prompt(
            "class Test {}", "Test.java", "=== PROJECT ===\nTest → Test.java"
        )
        assert "forge" in prompt.lower()
        assert "fabric" in prompt.lower()
        assert "1.20.1" in prompt

    def test_fallback_convert(self):
        from src.modes.refactor import RefactorMode
        refactorer = RefactorMode(
            "1.20.1", "forge", "1.20.1", "fabric",
            api_key="test-key"
        )
        source = '@Mod("test")\npublic class Test {}'
        result = refactorer._fallback_convert(source)
        # Should at least do something
        assert result is not None


class TestJarDetection:
    """Test jar metadata detection."""

    def test_detect_fabric_mod(self):
        """Test detection of Fabric mod metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake fabric.mod.json
            import json
            meta_dir = os.path.join(tmpdir)
            meta = {
                "schemaVersion": 1,
                "id": "testmod",
                "version": "1.0.0",
                "name": "Test Mod",
                "depends": {"minecraft": ">=1.20.1"}
            }
            with open(os.path.join(meta_dir, "fabric.mod.json"), "w") as f:
                json.dump(meta, f)

            # Create a minimal jar
            jar_path = os.path.join(tmpdir, "test.jar")
            import zipfile
            with zipfile.ZipFile(jar_path, "w") as zf:
                zf.writestr("fabric.mod.json", json.dumps(meta))
                zf.writestr("com/test/TestClass.java", "class TestClass {}")

            from main import detect_mod_info
            info = detect_mod_info(jar_path)
            assert info["loader"] == "fabric"
            assert info["mod_id"] == "testmod"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
