# 🔄 Minecraft Mod Converter & Refactor Tool

将 Minecraft mod 在不同版本和不同加载器之间转换。

```
Forge ↔ Fabric | 1.16 ~ 1.21+ | 版本升降 + 加载器互转
```

## ✨ 功能

### 两种模式

| 模式 | 原理 | 适用场景 | 速度 |
|------|------|----------|------|
| **convert** | 规则引擎 + 模式匹配 | 简单 mod、批量处理 | ⚡ 快 |
| **refactor** | AI 语义理解 + 代码重写 | 复制 mod、高质量输出 | 🐢 慢但准 |

### 支持的转换

- ✅ Forge → Fabric
- ✅ Fabric → Forge
- ✅ NeoForge → Forge/Fabric
- ✅ 版本升级（1.20.1 → 1.21）
- ✅ 版本降级（1.21 → 1.20.1）
- ✅ 同时换版本 + 换加载器

### 自动处理的内容

- `@Mod` 注解 ↔ `ModInitializer` 接口
- `DeferredRegister` ↔ `Registry.register()`
- `@SubscribeEvent` 事件系统 ↔ Fabric Callbacks
- `SimpleChannel` 网络包 ↔ Fabric Networking
- 包路径和导入语句
- 生成目标加载器的元数据文件（`fabric.mod.json` / `mods.toml`）

## 📦 安装

### 方式一：直接运行（需要 Python 3.10+）

```bash
git clone https://github.com/YOUR_USERNAME/mod-converter.git
cd mod-converter
pip install toml  # 可选，Python 3.11+ 自带 tomllib
python3 main.py --help
```

### 方式二：构建可执行文件

```bash
pip install pyinstaller
chmod +x build.sh
./build.sh
# 输出: dist/mod-converter (Linux) 或 dist/mod-converter.exe (Windows)
```

### 前置要求

- **Python 3.10+**（推荐 3.12）
- **Java 17+**（反编译 jar 需要）
  ```bash
  # Ubuntu/Debian
  sudo apt install openjdk-17-jre
  
  # macOS
  brew install openjdk@17
  
  # Windows
  # https://adoptium.net/
  ```

## 🚀 使用方法

### 分析 mod

```bash
python3 main.py analyze input.jar
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
python3 main.py convert input.jar -t 1.20.1 -l fabric -o output.jar

# Fabric 1.20.1 → Forge 1.21
python3 main.py convert input.jar -t 1.21 -l forge -o output.jar

# 降版本
python3 main.py convert input.jar -t 1.20.1 -l forge -o output.jar
```

### 重构模式（AI 驱动）

```bash
# 需要 OpenAI API Key（或兼容的 API）
python3 main.py refactor input.jar -t 1.20.1 -l fabric \
  --api-key sk-xxx \
  --model gpt-4o \
  -o output/

# 使用其他兼容 API（如 DeepSeek、Ollama 等）
python3 main.py refactor input.jar -t 1.20.1 -l fabric \
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
├── lib/                    # 反编译器 jar（自动下载）
├── build.sh                # 构建脚本
└── README.md
```

## 🔧 API 映射表

工具内置了完整的 Forge ↔ Fabric API 映射：

| Forge | Fabric | 类型 |
|-------|--------|------|
| `@Mod` | `ModInitializer` | 模组入口 |
| `@SubscribeEvent` | Fabric Callbacks | 事件系统 |
| `DeferredRegister` | `Registry.register()` | 注册 |
| `ForgeRegistries` | `Registries` | 注册表 |
| `SimpleChannel` | `ServerPlayNetworking` | 网络 |
| `ForgeConfigSpec` | Cloth Config | 配置 |
| `LazyOptional` | `Optional` | 能力系统 |

## ⚠️ 已知限制

1. **反编译不完美**：变量名可能丢失，lambda 可能被拆散
2. **Forge Capability**：没有 Fabric 等价物，需要手动重设计
3. **Mixin 代码**：目标平台的注入点可能不同
4. **第三方库**：需要手动替换（如 GeckoLib → Fabric 版本）
5. **AI 模式需要 API Key**：重构模式依赖外部 LLM 服务

## 🧪 测试

```bash
python3 tests/run_tests.py
```

```
🔌 Mapping Tests:      ✅ 6/6
📊 Analyzer Tests:      ✅ 3/3
🔄 Convert Mode Tests:  ✅ 4/4
🧠 Refactor Mode Tests: ✅ 2/2
📦 Jar Detection Tests: ✅ 1/1

Results: 16 passed, 0 failed
```

## 📄 License

MIT

## 🤝 Contributing

欢迎提交 PR！特别是：
- 新的 API 映射规则
- 更多版本的转换支持
- 测试用例
- Bug 修复
