"""
Mappings module - Forge ↔ Fabric API mappings and version-specific changes.
Central knowledge base for all known transformations.
"""

# ============================================================
# FORGE → FABRIC API MAPPINGS
# ============================================================

FORGE_TO_FABRIC = {
    # --- Events ---
    "net.minecraftforge.event.entity.player.PlayerEvent": {
        "fabric": "net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents",
        "note": "Forge uses @SubscribeEvent on event bus; Fabric uses callback registration",
    },
    "net.minecraftforge.event.TickEvent": {
        "fabric": "net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents",
        "note": "Forge TickEvent.ServerTickEvent → Fabric ServerTickEvents.END_SERVER_TICK",
    },
    "net.minecraftforge.event.entity.living.LivingDeathEvent": {
        "fabric": "net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents",
        "note": "Forge uses @SubscribeEvent; Fabric uses ServerLivingEntityEvents.ALLOW_DEATH",
    },
    "net.minecraftforge.event.world.BlockEvent": {
        "fabric": "net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents",
        "note": "Forge BlockEvent.BreakEvent → Fabric PlayerBlockBreakEvents.BEFORE",
    },
    "net.minecraftforge.event.entity.player.AttackEntityEvent": {
        "fabric": "net.fabricmc.fabric.api.event.player.AttackEntityCallback",
        "note": "Forge AttackEntityEvent → Fabric AttackEntityCallback.EVENT",
    },
    "net.minecraftforge.event.server.ServerStartingEvent": {
        "fabric": "net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents",
        "note": "Use ServerLifecycleEvents.SERVER_STARTING",
    },
    "net.minecraftforge.event.server.ServerStoppingEvent": {
        "fabric": "net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents",
        "note": "Use ServerLifecycleEvents.SERVER_STOPPING",
    },

    # --- Registry ---
    "net.minecraftforge.registries.DeferredRegister": {
        "fabric": "net.minecraft.registry.Registry",
        "note": "Forge uses DeferredRegister + RegistryObject; Fabric uses direct Registry.register()",
        "transform": "deferred_register",
    },
    "net.minecraftforge.registries.ForgeRegistries": {
        "fabric": "net.minecraft.registry.Registries",
        "note": "ForgeRegistries.ITEMS → Registries.ITEM, ForgeRegistries.BLOCKS → Registries.BLOCK",
    },
    "net.minecraftforge.registries.RegistryObject": {
        "fabric": "net.minecraft.util.Identifier",
        "note": "RegistryObject.get() replaced by direct reference after registration",
    },
    "net.minecraftforge.event.RegistryEvent": {
        "fabric": "net.minecraft.registry.Registry",
        "note": "Direct registration in mod initializer instead of event",
    },

    # --- Networking ---
    "net.minecraftforge.network.simple.SimpleChannel": {
        "fabric": "net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking",
        "note": "Forge SimpleChannel → Fabric ServerPlayNetworking/ClientPlayNetworking",
    },
    "net.minecraftforge.network.NetworkRegistry": {
        "fabric": "net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking",
        "note": "Different networking model; use PayloadTypeRegistry for packet registration",
    },

    # --- Capabilities ---
    "net.minecraftforge.common.capabilities.ICapabilityProvider": {
        "fabric": "No direct equivalent",
        "note": "Forge Capabilities have no Fabric equivalent. Use API interfaces or component systems instead.",
        "transform": "capability_rewrite",
    },
    "net.minecraftforge.common.util.LazyOptional": {
        "fabric": "java.util.Optional or direct access",
        "note": "LazyOptional pattern not needed in Fabric",
    },

    # --- Config ---
    "net.minecraftforge.common.ModConfig": {
        "fabric": "net.fabricmc.loader.api.ModContainer.getConfig() or Cloth Config API",
        "note": "Forge has built-in config; Fabric uses external libraries (Cloth Config, ModMenu)",
    },
    "net.minecraftforge.fml.config.ModConfig": {
        "fabric": "Cloth Config API or manual JSON config",
        "note": "Forge built-in config system not available in Fabric",
    },

    # --- Mod Lifecycle ---
    "net.minecraftforge.fml.common.Mod": {
        "fabric": "net.fabricmc.api.ModInitializer",
        "note": "@Mod annotation → implements ModInitializer, use onInitialize() method",
        "transform": "mod_class",
    },
    "net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent": {
        "fabric": "net.fabricmc.api.ModInitializer.onInitialize()",
        "note": "Common setup code goes in onInitialize()",
    },
    "net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent": {
        "fabric": "net.fabricmc.api.ClientModInitializer.onInitializeClient()",
        "note": "Client setup code goes in onInitializeClient()",
    },
    "net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext": {
        "fabric": "Not needed",
        "note": "Fabric uses mod initializer pattern, no loading context needed",
    },

    # --- GUI / Menu ---
    "net.minecraft.inventory.container.Container": {
        "fabric": "net.minecraft.screen.ScreenHandler",
        "note": "Container → ScreenHandler (1.17+ mapping change)",
    },
    "net.minecraft.client.gui.screen.inventory.ContainerScreen": {
        "fabric": "net.minecraft.client.gui.screen.ingame.HandledScreen",
        "note": "ContainerScreen → HandledScreen",
    },
    "net.minecraftforge.network.IContainerFactory": {
        "fabric": "net.minecraft.screen.ScreenHandlerFactory",
        "note": "Different factory interface in Fabric",
    },

    # --- Block Entity ---
    "net.minecraft.tileentity.TileEntity": {
        "fabric": "net.minecraft.block.entity.BlockEntity",
        "note": "TileEntity → BlockEntity (1.17+ mapping change)",
    },
    "net.minecraftforge.common.extensions.IForgeBlockEntity": {
        "fabric": "net.minecraft.block.entity.BlockEntity",
        "note": "Forge extension interface not needed; use vanilla BlockEntity directly",
    },

    # --- Properties ---
    "net.minecraft.state.properties.BlockStateProperties": {
        "fabric": "net.minecraft.state.property.Properties",
        "note": "BlockStateProperties → Properties",
    },
}

# ============================================================
# VERSION-SPECIFIC CHANGES
# ============================================================

VERSION_CHANGES = {
    ("1.20.1", "1.21"): {
        "description": "Major changes: Component system, registry changes, data-driven features",
        "changes": [
            {
                "area": "items",
                "old": "NBT-based item data (CompoundTag)",
                "new": "Component system (DataComponentType)",
                "pattern_old": r"ItemStack\.getTag\(\)|CompoundTag|\.getOrCreateTag\(\)",
                "pattern_new": "DataComponentType",
                "note": "Item NBT replaced by typed Components in 1.21",
            },
            {
                "area": "registry",
                "old": "BuiltInRegistries",
                "new": "Registry with Holder",
                "note": "Registry access pattern changed",
            },
            {
                "area": "damage",
                "old": "DamageSource constructor",
                "new": "DamageSources registry",
                "pattern_old": r"new\s+DamageSource\(",
                "note": "DamageSource now created through DamageSources registry",
            },
        ],
    },
    ("1.21", "1.20.1"): {
        "description": "Reverse of above: Component system → NBT, new registry → old registry",
        "changes": [
            {
                "area": "items",
                "old": "Component system (DataComponentType)",
                "new": "NBT-based item data (CompoundTag)",
                "note": "Components back to NBT tags",
            },
            {
                "area": "damage",
                "old": "DamageSources registry",
                "new": "DamageSource constructor",
                "note": "Use old DamageSource pattern",
            },
        ],
    },
    ("1.20.1", "1.20.4"): {
        "description": "Minor changes: Some API refinements",
        "changes": [
            {
                "area": "registry",
                "note": "Mostly compatible, minor API adjustments",
            },
        ],
    },
    ("1.19.4", "1.20.1"): {
        "description": "Changes: Trim patterns, armor trims, new commands",
        "changes": [
            {
                "area": "general",
                "note": "Most APIs compatible; check for removed/renamed methods",
            },
        ],
    },
}

# ============================================================
# FABRIC → FORGE MAPPINGS (reverse)
# ============================================================

FABRIC_TO_FORGE = {}
for forge_api, info in FORGE_TO_FABRIC.items():
    fabric_api = info["fabric"]
    if fabric_api and fabric_api != "No direct equivalent":
        FABRIC_TO_FORGE[fabric_api] = {
            "forge": forge_api,
            "note": f"Reverse: {info['note']}",
        }


# ============================================================
# COMMON TRANSFORM RULES (text-based)
# ============================================================

TEXT_TRANSFORMS = {
    # Package renames (Mojang mappings)
    "package": {
        "net.minecraft.world.level.block": "net.minecraft.block",
        "net.minecraft.world.item": "net.minecraft.item",
        "net.minecraft.world.entity": "net.minecraft.entity",
        "net.minecraft.world.inventory": "net.minecraft.screen",
        "net.minecraft.world.level.block.entity": "net.minecraft.block.entity",
        "net.minecraft.client.gui.screens.inventory": "net.minecraft.client.gui.screen.ingame",
        "net.minecraft.core.BlockPos": "net.minecraft.util.math.BlockPos",
        "net.minecraft.resources.ResourceLocation": "net.minecraft.util.Identifier",
    },
    # Import renames
    "import": {
        "net.minecraftforge.fml.common.Mod": "net.fabricmc.api.ModInitializer",
        "net.minecraftforge.event": "net.fabricmc.fabric.api.event",
        "net.minecraftforge.registries": "net.minecraft.registry",
        "net.minecraftforge.network": "net.fabricmc.fabric.api.networking",
    },
    # Class name renames
    "class": {
        "Container": "ScreenHandler",
        "ContainerScreen": "HandledScreen",
        "TileEntity": "BlockEntity",
        "BlockStateProperties": "Properties",
    },
    # Method renames
    "method": {
        "getTag()": "getComponents()",
        "getOrCreateTag()": "getOrCreateComponent()",
        "setTag(": "setComponent(",
    },
}

# Version-specific text transforms
VERSION_TEXT_TRANSFORMS = {
    "1.20.1_to_1.21": {
        "import_changes": {
            "net.minecraft.nbt.CompoundTag": "net.minecraft.component.ComponentMap",
            "net.minecraft.nbt.Tag": "net.minecraft.component.ComponentType",
        },
        "method_changes": {
            "stack.getTag()": "stack.getComponents()",
            "stack.getOrCreateTag()": "stack.copyComponents()",
            "tag.putInt(": "components.put(",
            "tag.getInt(": "components.get(",
            "tag.putString(": "components.put(",
            "tag.getString(": "components.get(",
        },
    },
    "1.21_to_1.20.1": {
        "import_changes": {
            "net.minecraft.component.ComponentMap": "net.minecraft.nbt.CompoundTag",
            "net.minecraft.component.ComponentType": "net.minecraft.nbt.Tag",
        },
        "method_changes": {
            "stack.getComponents()": "stack.getTag()",
            "stack.copyComponents()": "stack.getOrCreateTag()",
        },
    },
}


def get_mappings(source_loader: str, target_loader: str) -> dict:
    """Get the appropriate mapping set for conversion direction."""
    if source_loader == "forge" and target_loader == "fabric":
        return FORGE_TO_FABRIC
    elif source_loader == "fabric" and target_loader == "forge":
        return FABRIC_TO_FORGE
    return {}


def get_version_changes(source_version: str, target_version: str) -> dict:
    """Get version-specific changes."""
    key = (source_version, target_version)
    return VERSION_CHANGES.get(key, {"description": "No specific changes documented", "changes": []})


def get_text_transforms(source_loader: str, target_loader: str, source_version: str, target_version: str) -> dict:
    """Get text-based transforms for the given conversion."""
    transforms = TEXT_TRANSFORMS.copy()

    # Add version-specific transforms
    vkey = f"{source_version}_to_{target_version}"
    if vkey in VERSION_TEXT_TRANSFORMS:
        transforms["version"] = VERSION_TEXT_TRANSFORMS[vkey]

    return transforms
