#!/usr/bin/env python3
"""Simple test runner (no pytest dependency)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passed = 0
failed = 0
errors = []

def run_test(name, func):
    global passed, failed
    try:
        func()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1
        errors.append((name, str(e)))


# === MAPPINGS TESTS ===
print("\n🔌 Mapping Tests:")
from src.utils.mappings import (
    FORGE_TO_FABRIC, FABRIC_TO_FORGE, get_mappings,
    get_version_changes, get_text_transforms,
)

run_test("FORGE_TO_FABRIC not empty", lambda: None if len(FORGE_TO_FABRIC) > 0 else (_ for _ in ()).throw(AssertionError()))
run_test("FABRIC_TO_FORGE not empty", lambda: None if len(FABRIC_TO_FORGE) > 0 else (_ for _ in ()).throw(AssertionError()))

def test_get_mappings():
    m = get_mappings("forge", "fabric")
    assert len(m) > 0
    assert all("fabric" in v for v in m.values())
run_test("get_mappings forge→fabric", test_get_mappings)

def test_version_changes():
    c = get_version_changes("1.20.1", "1.21")
    assert "changes" in c
    assert len(c["changes"]) > 0
run_test("version changes 1.20.1→1.21", test_version_changes)

def test_text_transforms():
    t = get_text_transforms("forge", "fabric", "1.20.1", "1.21")
    assert "package" in t
    assert "import" in t
run_test("text transforms", test_text_transforms)

def test_mod_mapping():
    assert "net.minecraftforge.fml.common.Mod" in FORGE_TO_FABRIC
    m = FORGE_TO_FABRIC["net.minecraftforge.fml.common.Mod"]
    assert "ModInitializer" in m["fabric"]
run_test("mod class mapping", test_mod_mapping)


# === ANALYZER TESTS ===
print("\n📊 Analyzer Tests:")
from src.core.analyzer import Analyzer, FORGE_PATTERNS, FABRIC_PATTERNS
import re

def test_forge_detection():
    sample = '@Mod("testmod")\npublic class TestMod {\n    @SubscribeEvent\n    public void onTick() {}\n}'
    found = False
    for cat, patterns in FORGE_PATTERNS.items():
        for p in patterns:
            if re.search(p, sample):
                found = True
                break
    assert found, "No Forge patterns detected"
run_test("Forge pattern detection", test_forge_detection)

def test_fabric_detection():
    sample = 'public class TestMod implements ModInitializer {\n    Registry.register(Registries.ITEM, ...);\n}'
    found = False
    for cat, patterns in FABRIC_PATTERNS.items():
        for p in patterns:
            if re.search(p, sample):
                found = True
                break
    assert found, "No Fabric patterns detected"
run_test("Fabric pattern detection", test_fabric_detection)

def test_class_analysis():
    a = Analyzer()
    result = a._analyze_class('@Mod("testmod")\npublic class TestMod {}', "TestMod.java")
    assert result is not None
    assert result["name"] == "TestMod"
run_test("class analysis", test_class_analysis)


# === CONVERT MODE TESTS ===
print("\n🔄 Convert Mode Tests:")
from src.modes.convert import ConvertMode

def test_mod_class_transform():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '@Mod("mymod")\npublic class MyMod {\n    public MyMod() {}\n}'
    r = c._transform_mod_class(src, "MyMod.java")
    assert "ModInitializer" in r
    assert "@Mod" not in r
    # Verify class declaration is preserved (not corrupted)
    assert "public class MyMod implements ModInitializer" in r
    assert r.startswith("import net.fabricmc.api.ModInitializer;")
run_test("@Mod → ModInitializer", test_mod_class_transform)

def test_mod_class_preserves_existing_implements():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '@Mod("mymod")\npublic class MyMod extends SomeBase implements Runnable {\n}'
    r = c._transform_mod_class(src, "MyMod.java")
    assert "implements Runnable, ModInitializer" in r
    assert "public class MyMod extends SomeBase" in r
run_test("@Mod preserves existing implements", test_mod_class_preserves_existing_implements)

def test_registry_transform():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = 'DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, "mymod");'
    r = c._transform_registry(src, "ModItems.java")
    assert "DeferredRegister" not in r
run_test("DeferredRegister → Registry.register", test_registry_transform)

def test_add_import():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = 'package com.test;\n\nimport java.util.List;\n\nclass Foo {}'
    r = c._add_import(src, "net.minecraft.util.Identifier")
    assert "import net.minecraft.util.Identifier;" in r
run_test("import insertion", test_add_import)

def test_forge_to_fabric_pipeline():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '''package com.test;

import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;

@Mod("mymod")
public class MyMod {
    DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, "mymod");
    
    public MyMod() {
        MinecraftForge.EVENT_BUS.register(this);
    }
    
    @SubscribeEvent
    public void onTick(TickEvent.ServerTickEvent event) {}
}
'''
    r = c._convert_file(src, "MyMod.java")
    # Check key transformations happened
    assert "fabricmc" in r or "ModInitializer" in r or "Registry" in r
    # Check forge references removed
    assert "ForgeRegistries" not in r
    # Verify class declaration is correct (not corrupted)
    assert "public class MyMod implements ModInitializer" in r
    # Verify event transform worked
    assert "onServerTick" in r
    # Verify invalid forge imports are removed
    assert "net.minecraftforge" not in r
run_test("full forge→fabric pipeline", test_forge_to_fabric_pipeline)

def test_fabric_to_forge_pipeline():
    c = ConvertMode("1.20.1", "fabric", "1.20.1", "forge")
    src = '''package com.test;

import net.fabricmc.api.ModInitializer;
import net.minecraft.registry.Registry;
import net.minecraft.registry.Registries;
import net.minecraft.util.Identifier;

public class MyMod implements ModInitializer {
    @Override
    public void onInitialize() {
        Registry.register(Registries.ITEM, new Identifier("mymod", "diamond_sword"), new SwordItem());
    }
}
'''
    r = c._convert_file(src, "MyMod.java")
    # Verify class declaration is preserved
    assert "public class MyMod" in r
    # Verify @Mod annotation added
    assert '@Mod("modid")' in r
    # Verify DeferredRegister created
    assert "DeferredRegister<ITEM>" in r
    assert "ForgeRegistries.ITEMS" in r
    # Verify registration converted
    assert 'ITEMS.register("diamond_sword"' in r
    # Verify onInitialize converted
    assert "onCommonSetup" in r
    # Verify Fabric imports removed
    assert "net.fabricmc" not in r
run_test("full fabric→forge pipeline", test_fabric_to_forge_pipeline)

# === EDGE CASE TESTS ===
print("\n🧪 Edge Case Tests:")

def test_abstract_mod_class():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '@Mod("mymod")\npublic abstract class BaseMod implements Runnable {\n}'
    r = c._transform_mod_class(src, "BaseMod.java")
    assert "public abstract class BaseMod implements Runnable, ModInitializer" in r
run_test("abstract class with @Mod", test_abstract_mod_class)

def test_mod_with_variable_id():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '@Mod(TestMod.MODID)\npublic class TestMod {\n    public static final String MODID = "test";\n}'
    r = c._transform_mod_class(src, "TestMod.java")
    assert "implements ModInitializer" in r
    assert "@Mod" not in r
run_test("@Mod with variable reference", test_mod_with_variable_id)

def test_multiple_subscribe_events():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '''public class MyMod {
    @SubscribeEvent
    public void onTick(TickEvent.ServerTickEvent event) {}

    @SubscribeEvent
    public void onJoin(PlayerLoggedInEvent event) {}
}'''
    r = c._convert_file(src, "MyMod.java")
    assert "onServerTick" in r
    assert "onPlayerJoin" in r
    assert "@SubscribeEvent" not in r
run_test("multiple @SubscribeEvent handlers", test_multiple_subscribe_events)

def test_utility_class_noop():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = 'public class Utils {\n    public static int add(int a, int b) { return a + b; }\n}'
    r = c._convert_file(src, "Utils.java")
    assert "public class Utils" in r
    assert "add(int a, int b)" in r
run_test("utility class without @Mod (no-op)", test_utility_class_noop)

def test_fabric_multi_registry_types():
    c = ConvertMode("1.20.1", "fabric", "1.20.1", "forge")
    src = '''public class MyMod implements ModInitializer {
    @Override
    public void onInitialize() {
        Registry.register(Registries.ITEM, new Identifier("mymod", "sword"), new SwordItem());
        Registry.register(Registries.BLOCK, new Identifier("mymod", "ore"), new OreBlock());
    }
}'''
    r = c._convert_file(src, "MyMod.java")
    assert "DeferredRegister<ITEM>" in r
    assert "DeferredRegister<BLOCK>" in r
    assert 'ITEMS.register("sword"' in r
    assert 'BLOCKS.register("ore"' in r
run_test("Fabric→Forge multiple registry types", test_fabric_multi_registry_types)

def test_forge_config_to_fabric():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '''import net.minecraftforge.common.ForgeConfigSpec;
public class ModConfig {
    public static final ForgeConfigSpec.Builder BUILDER = new ForgeConfigSpec.Builder();
}'''
    r = c._convert_file(src, "ModConfig.java")
    assert "ForgeConfigSpec" not in r
    assert "TODO" in r
run_test("Forge config → Fabric TODO", test_forge_config_to_fabric)

def test_forge_networking_to_fabric():
    c = ConvertMode("1.20.1", "forge", "1.20.1", "fabric")
    src = '''import net.minecraftforge.network.simple.SimpleChannel;
public class Net {
    private static final SimpleChannel CH = NetworkRegistry.newSimpleChannel(
        new ResourceLocation("mymod", "main"), () -> "1.0", s -> true, s -> true
    );
}'''
    r = c._convert_file(src, "Net.java")
    assert "SimpleChannel" not in r
    assert "ServerPlayNetworking" in r
run_test("Forge networking → Fabric", test_forge_networking_to_fabric)

def test_version_change_adds_todo():
    c = ConvertMode("1.20.1", "forge", "1.21", "forge")
    src = '''public class ItemData {
    public void save(CompoundTag tag) {
        tag.putInt("count", 5);
    }
}'''
    r = c._convert_file(src, "ItemData.java")
    assert "TODO" in r or "Version change" in r
run_test("version change 1.20→1.21 adds TODO", test_version_change_adds_todo)


# === REFACTOR MODE TESTS ===
print("\n🧠 Refactor Mode Tests:")
from src.modes.refactor import RefactorMode

def test_prompt_building():
    r = RefactorMode("1.20.1", "forge", "1.20.1", "fabric", api_key="test")
    p = r._build_prompt("class Test {}", "Test.java", "=== PROJECT ===")
    assert "forge" in p.lower()
    assert "fabric" in p.lower()
run_test("prompt building", test_prompt_building)

def test_fallback():
    r = RefactorMode("1.20.1", "forge", "1.20.1", "fabric", api_key="test")
    result = r._fallback_convert('@Mod("test")\npublic class Test {}')
    assert result is not None
run_test("fallback conversion", test_fallback)


# === JAR DETECTION TESTS ===
print("\n📦 Jar Detection Tests:")
import tempfile, json, zipfile

def test_detect_fabric():
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = {"schemaVersion": 1, "id": "testmod", "version": "1.0.0", "name": "Test", "depends": {"minecraft": ">=1.20.1"}}
        jar = os.path.join(tmpdir, "test.jar")
        with zipfile.ZipFile(jar, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(meta))
            zf.writestr("com/test/Foo.java", "class Foo {}")
        from main import detect_mod_info
        info = detect_mod_info(jar)
        assert info["loader"] == "fabric"
        assert info["mod_id"] == "testmod"
run_test("detect Fabric mod", test_detect_fabric)

def test_detect_forge_with_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        jar = os.path.join(tmpdir, "test.jar")
        toml = 'modLoader = "javafml"\nloaderVersion = "[47,)"\n\n[[mods]]\nmodId = "testmod"\ndisplayName = "Test"\n\n[[dependencies.testmod]]\nmodId = "forge"\nmandatory = true\nversionRange = "[47,)"\n\n[[dependencies.testmod]]\nmodId = "minecraft"\nmandatory = true\nversionRange = "[1.20.1,)"\n'
        with zipfile.ZipFile(jar, "w") as zf:
            zf.writestr("META-INF/mods.toml", toml)
        from main import detect_mod_info
        info = detect_mod_info(jar)
        assert info["loader"] == "forge"
        assert info["version"] == "1.20.1"
        assert info["mod_id"] == "testmod"
run_test("detect Forge mod with version", test_detect_forge_with_version)

def test_detect_neoforge():
    with tempfile.TemporaryDirectory() as tmpdir:
        jar = os.path.join(tmpdir, "test.jar")
        with zipfile.ZipFile(jar, "w") as zf:
            zf.writestr("META-INF/neoforge.mods.toml", '[[mods]]\nmodId = "neomod"\ndisplayName = "Neo"\n')
        from main import detect_mod_info
        info = detect_mod_info(jar)
        assert info["loader"] == "neoforge"
        assert info["mod_id"] == "neomod"
run_test("detect NeoForge mod", test_detect_neoforge)

def test_detect_fallback_classpath():
    with tempfile.TemporaryDirectory() as tmpdir:
        jar = os.path.join(tmpdir, "test.jar")
        with zipfile.ZipFile(jar, "w") as zf:
            zf.writestr("net/minecraftforge/common/MinecraftForge.java", "class Foo {}")
        from main import detect_mod_info
        info = detect_mod_info(jar)
        assert info["loader"] == "forge"
run_test("fallback detection from classpath", test_detect_fallback_classpath)


# === SUMMARY ===
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if errors:
    print(f"\nFailed tests:")
    for name, err in errors:
        print(f"  - {name}: {err}")
print()
sys.exit(1 if failed else 0)
