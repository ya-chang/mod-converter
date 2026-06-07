"""
Decompiler module - Extracts and decompiles mod jar files.
Supports CFR and Vineflower decompilers.
"""

import os
import subprocess
import zipfile
import shutil
import tempfile
from pathlib import Path


# Decompiler download URLs (fallback: bundled or auto-download)
CFR_URL = "https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar"
VINEFLOWER_URL = "https://github.com/Vineflower/vineflower/releases/download/1.11.0/vineflower-1.11.0.jar"


class Decompiler:
    """Handles jar extraction and Java source decompilation."""

    def __init__(self, decompiler: str = "cfr", lib_dir: str = None):
        self.decompiler = decompiler
        self.lib_dir = lib_dir or os.path.join(os.path.dirname(__file__), "..", "..", "lib")
        os.makedirs(self.lib_dir, exist_ok=True)

    def _get_decompiler_jar(self) -> str:
        """Get path to decompiler jar, download if needed."""
        if self.decompiler == "cfr":
            jar_name = "cfr-0.152.jar"
        elif self.decompiler == "vineflower":
            jar_name = "vineflower-1.11.0.jar"
        else:
            raise ValueError(f"Unknown decompiler: {self.decompiler}")

        jar_path = os.path.join(self.lib_dir, jar_name)
        if os.path.exists(jar_path):
            return jar_path

        print(f"📥 Downloading {self.decompiler}...")
        url = CFR_URL if self.decompiler == "cfr" else VINEFLOWER_URL
        try:
            import urllib.request
            urllib.request.urlretrieve(url, jar_path)
            print(f"  ✅ Downloaded to {jar_path}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to download {self.decompiler}: {e}\n"
                f"Please manually download {url} and place it in {self.lib_dir}/"
            )
        return jar_path

    def _check_java(self):
        """Verify Java is available."""
        try:
            result = subprocess.run(
                ["java", "-version"], capture_output=True, text=True, timeout=10
            )
            version_line = result.stderr.split("\n")[0] if result.stderr else "unknown"
            print(f"  ☕ Java: {version_line}")
            return True
        except FileNotFoundError:
            raise RuntimeError(
                "Java not found. Please install Java 17+ to use the decompiler.\n"
                "  Ubuntu/Debian: sudo apt install openjdk-17-jre\n"
                "  macOS: brew install openjdk@17\n"
                "  Windows: https://adoptium.net/"
            )

    def extract_jar(self, jar_path: str, output_dir: str = None) -> str:
        """Extract jar contents to a directory."""
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="mod-extract-")

        print(f"📦 Extracting: {os.path.basename(jar_path)}")
        with zipfile.ZipFile(jar_path, "r") as zf:
            zf.extractall(output_dir)

        # Count files
        file_count = sum(1 for _ in Path(output_dir).rglob("*") if _.is_file())
        print(f"  📁 Extracted {file_count} files to {output_dir}")
        return output_dir

    def decompile(self, jar_path: str, output_dir: str = None) -> str:
        """Full pipeline: extract jar → decompile classes → return source dir."""
        self._check_java()

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="mod-decompile-")

        # Step 1: Extract
        extract_dir = os.path.join(output_dir, "_extracted")
        self.extract_jar(jar_path, extract_dir)

        # Step 2: Find all class files
        class_files = list(Path(extract_dir).rglob("*.class"))
        if not class_files:
            print("  ⚠️  No .class files found in jar")
            # Maybe it's already source? Copy as-is
            shutil.copytree(extract_dir, os.path.join(output_dir, "src"), dirs_exist_ok=True)
            return output_dir

        print(f"  🔧 Found {len(class_files)} class files to decompile")

        # Step 3: Decompile
        decompiler_jar = self._get_decompiler_jar()
        src_dir = os.path.join(output_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        if self.decompiler == "cfr":
            cmd = [
                "java", "-jar", decompiler_jar,
                extract_dir,
                "--outputdir", src_dir,
                "--silent", "true",
                "--caseinsensitivefs", "false",
            ]
        else:  # vineflower
            cmd = [
                "java", "-jar", decompiler_jar,
                extract_dir,
                "-o", src_dir,
                "--loglevel", "WARN",
            ]

        print(f"  ⚙️  Running {self.decompiler}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print(f"  ⚠️  Decompiler warnings:\n{result.stderr[:500]}")

        # Count decompiled files
        java_files = list(Path(src_dir).rglob("*.java"))
        print(f"  ✅ Decompiled {len(java_files)} Java files")

        # Copy non-class resources (configs, assets, etc.)
        resources_dir = os.path.join(output_dir, "resources")
        os.makedirs(resources_dir, exist_ok=True)
        for item in Path(extract_dir).rglob("*"):
            if item.is_file() and item.suffix != ".class":
                rel = item.relative_to(extract_dir)
                dest = resources_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

        print(f"  📄 Copied resources to {resources_dir}")
        return output_dir

    def list_classes(self, jar_path: str) -> list:
        """List all class files in a jar without decompiling."""
        classes = []
        with zipfile.ZipFile(jar_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".class"):
                    classes.append(name.replace("/", ".").replace(".class", ""))
        return sorted(classes)

    def read_manifest(self, jar_path: str) -> dict:
        """Read jar manifest and metadata files."""
        metadata = {}
        with zipfile.ZipFile(jar_path, "r") as zf:
            # MANIFEST.MF
            if "META-INF/MANIFEST.MF" in zf.namelist():
                with zf.open("META-INF/MANIFEST.MF") as f:
                    metadata["manifest"] = f.read().decode("utf-8")

            # List all META-INF files
            metadata["meta_files"] = [
                n for n in zf.namelist() if n.startswith("META-INF/")
            ]

            # Top-level structure
            metadata["top_level"] = list(set(
                n.split("/")[0] for n in zf.namelist() if "/" in n
            ))

        return metadata
