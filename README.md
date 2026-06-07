# 🔄 Minecraft Mod Converter & Refactor Tool

将 Minecraft mod 在不同版本和不同加载器之间转换。

```
Forge ↔ Fabric | 1.12 ~ 1.21 | 版本升降 + 加载器互转
```

## ✨ 功能

### 两种模式

| 模式 | 原理 | 适用场景 | 速度 |
|------|------|----------|------|
| **convert** | 规则引擎 + 模式匹配 | 简单 mod、批量处理 | ⚡ 快 |
| **refactor** | AI 语义理解 + 代码重写 | 复杂 mod、高质量输出 | 🐢 慢但准 |

### 支持的版本范围

```
1.12 ←→ 1.16 ←→ 1.17 ←→ 1.18 ←→ 1.19 ←→ 1.20 ←→ 1.21
```

- ✅ 1.12.x（经典 Forge）
- ✅ 1.16.x（Forge + Fabric 起始）
- ✅ 1.17.x（Mappings 大变更）
- ✅ 1.18.x（世界生成重写）
- ✅ 1.19.x（聊天系统变更）
- ✅ 1.20.x（数据包增强）
- ✅ 1.21.x（Component 系统）

### 支持的转换方向

- ✅ Forge → Fabric
- ✅ Fabric → Forge
- ✅ NeoForge → Forge/Fabric
- ✅ 版本升级（如 1.16 → 1.21）
- ✅ 版本降级（如 1.21 → 1.12）
- ✅ 同时换版本 + 换加载器

### 自动处理的内容

- `@Mod` 注解 ↔ `ModInitializer` 接口
- `DeferredRegister` ↔ `Registry.register()`
- `@SubscribeEvent` 事件系统 ↔ Fabric Callbacks
- `SimpleChannel` 网络包 ↔ Fabric Networking
- Forge Capability → Fabric 替代方案
- 包路径和导入语句（Mojang/Intermediary mappings）
- 版本间 API 差异（NBT ↔ Component、DamageSource 等）
- 生成目标加载器的元数据文件（`fabric.mod.json` / `mods.toml`）

## 📦 安装

### 下载预编译版本

从 [Releases](https://github.com/ya-chang/mod-converter/releases) 页面下载：

| 平台 | 文件 |
|------|------|
| Windows x64 | `mod-converter-windows-x64.exe` |
| Linux x64 | `mod-converter-linux-x64` |

### 从源码运行

```bash
git clone https://github.com/ya-chang/mod-converter.git
cd mod-converter
python3 main.py --help
```

### 自行构建

```bash
pip install pyinstaller
pyinstaller --onefile --name mod-converter --console main.py
# 输出: dist/mod-converter (Linux) 或 dist/mod-converter.exe (Windows)
```

### 前置要求

- **Python 3.10+**（推荐 3.12，源码运行时需要）
- **Java 17+**（反编译 jar 需要）
  ```bash
  # Ubuntu/Debian
  sudo apt install openjdk-17-jre
  # macOS
  brew install openjdk@17
  # Windows: https://adoptium.net/
  ```

## 🚀 使用方法

### 分析 mod

```bash
mod-converter analyze input.jar
```

输出示例：
```
📊 MOD ANALYSIS REPORT
==================================================
📁 Structure:
  Total Java files: 42
🔌 API Usage:
  forge:events: 8 usages in 3 files
  forge:registry: 5 usages in 2 files
⚡ Complexity:
  Detected loader: forge
  Difficulty: medium
```

### 转换模式（规则引擎）

```bash
# Forge 1.20.1 → Fabric 1.20.1
mod-converter convert input.jar -t 1.20.1 -l fabric -o output.jar

# Fabric 1.20.1 → Forge 1.16.5
mod-converter convert input.jar -t 1.16.5 -l forge -o output.jar

# Forge 1.12 → Fabric 1.20.1
mod-converter convert input.jar -t 1.20.1 -l fabric -o output.jar

# 降版本
mod-converter convert input.jar -t 1.12.2 -l forge -o output.jar
```

### 重构模式（AI 驱动）

```bash
# 需要 OpenAI API Key（或兼容的 API）
mod-converter refactor input.jar -t 1.20.1 -l fabric \
  --api-key sk-xxx \
  --model gpt-4o \
  -o output/

# 使用其他兼容 API（DeepSeek、Ollama 等）
mod-converter refactor input.jar -t 1.20.1 -l fabric \
  --api-key your-key \
  --api-base https://api.deepseek.com/v1 \
  --model deepseek-coder \
  -o output/
```

## 📁 项目结构

```
mod-converter/
├── main.py                 # CLI 入口
├── src/
│   ├── core/
│   │   ├── decompiler.py   # jar 反编译（CFR/Vineflower）
│   │   ├── analyzer.py     # 代码分析 & 报告
│   │   └── rebuilder.py    # 重新打包 jar
│   ├── modes/
│   │   ├── convert.py      # 转换模式（规则引擎）
│   │   └── refactor.py     # 重构模式（AI 驱动）
│   └── utils/
│       └── mappings.py     # API 映射表 & 版本差异
├── tests/
│   └── run_tests.py        # 测试套件
├── .github/workflows/
│   ├── build.yml           # 自动构建（每次推送）
│   └── release.yml         # 自动发布（打 tag 时）
├── build.sh                # 构建脚本
└── README.md
```

## 🔧 版本间的主要差异

| 变更 | 版本 | 说明 |
|------|------|------|
| 包名重构 | 1.16+ | MCP → Mojang mappings |
| 世界生成 | 1.18 | 完全重写，Y=0 以下新增 |
| 聊天系统 | 1.19 | 签名消息系统 |
| 数据包 | 1.20 | 增强数据包功能 |
| Component 系统 | 1.21 | NBT → 类型化 Component |
| Registry 重构 | 1.17+ | 新注册表系统 |
| Block Entity | 1.17 | TileEntity → BlockEntity |
| Container | 1.17 | Container → ScreenHandler |

## 🔌 API 映射表

| Forge | Fabric | 版本 |
|-------|--------|------|
| `@Mod` | `ModInitializer` | 1.16+ |
| `@SubscribeEvent` | Fabric Callbacks | 1.16+ |
| `DeferredRegister` | `Registry.register()` | 1.16+ |
| `ForgeRegistries` | `Registries` | 1.16+ |
| `SimpleChannel` | `ServerPlayNetworking` | 1.16+ |
| `ForgeConfigSpec` | Cloth Config | 1.16+ |
| `LazyOptional` | `Optional` | 1.16+ |
| `TileEntity` | `BlockEntity` | 1.17+ |
| `Container` | `ScreenHandler` | 1.17+ |
| `DamageSource(构造)` | `DamageSources` | 1.21+ |
| `CompoundTag` | `DataComponent` | 1.21+ |

## ⚠️ 已知限制

1. **反编译不完美**：变量名可能丢失，lambda 可能被拆散
2. **Forge Capability**：没有 Fabric 等价物，需要手动重设计
3. **Mixin 代码**：目标平台的注入点可能不同
4. **第三方库**：需要手动替换（如 GeckoLib → Fabric 版本）
5. **1.12 转换**：1.12 使用旧版 MCP mappings，差异较大，建议用 refactor 模式
6. **AI 模式需要 API Key**：重构模式依赖外部 LLM 服务

## 🧪 测试

```bash
python3 tests/run_tests.py
```

```bash
python3 tests/run_tests.py
```

```
🔌 Mapping Tests:      ✅ 6/6
📊 Analyzer Tests:      ✅ 3/3
🔄 Convert Mode Tests:  ✅ 6/6
🧪 Edge Case Tests:     ✅ 8/8
🧠 Refactor Mode Tests: ✅ 2/2
📦 Jar Detection Tests: ✅ 4/4

Results: 29 passed, 0 failed
```

测试覆盖：
- 基础映射、分析器、重构模式
- Forge ↔ Fabric 双向完整 pipeline
- 边缘情况：抽象类、变量引用的 modId、多事件处理器、多注册类型
- 无效 import 清理、配置/网络模块转换、版本变更 TODO
- Mod 检测：Fabric/Forge/NeoForge jar 元数据解析、classpath 回退检测

## 📦 发布

```bash
# 创建 tag 自动触发构建 + 发布 Release
git tag v1.0.0
git push --tags
# GitHub Actions 会自动构建 Windows/Linux 版本并发布到 Release 页面
```

## 📄 License

MIT

## 🤝 Contributing

欢迎提交 PR！特别是：
- 新的 API 映射规则
- 更多版本的转换支持
- 测试用例
- Bug 修复

## 📝 Changelog

### v1.0.1 (Bug Fixes)

**修复：**
- 修复 Forge→Fabric 转换中类声明被破坏的严重 bug（正则反向引用错误）
- 修复 Fabric→Forge 转换中类声明丢失的问题
- 修复 `@SubscribeEvent` 事件处理器转换全部失效的问题
- 修复 Fabric→Forge 注册转换中 DeferredRegister 插入位置错误
- 修复多注册类型（ITEM + BLOCK）全部使用同一变量名的 bug
- 修复正则无法匹配含括号构造函数（如 `new SwordItem()`）的问题
- 修复 import 转换生成不存在的 Fabric API import 的问题
- 修复已有 `implements` 子句的类添加 ModInitializer 时产生多余空格
- 修复分析器中 `Registries\.` 模式误匹配 `ForgeRegistries.` 的问题

**改进：**
- 新增 13 个测试用例（含边缘情况、Mod 检测、分析器），测试总数从 16 增至 29
- Forge→Fabric 转换现在正确清除所有无效的 Forge import
- Fabric→Forge 多注册类型自动分组，生成独立的 DeferredRegister 声明
