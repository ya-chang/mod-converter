"""
Rebuilder module - Packages converted source code back into a mod jar.
"""

import os
import json
import shutil
import zipfile
import subprocess
from pathlib import Path


class Rebuilder:
    """Rebuilds converted source into a mod jar."""

    def build(self, source_dir: str, output_jar: str, target_version: str = None, target_loader: str = None):
        """Build a mod jar from converted source directory."""
        print(f"📦 Building: {output_jar}")

        src_dir = os.path.join(source_dir, "src")
        res_dir = os.path.join(source_dir, "resources")

        if not os.path.isdir(src_dir):
            print("  ⚠️  No source directory found, packaging as-is")
            src_dir = source_dir

        # Try to compile if javac is available
        compiled = False
        class_dir = os.path.join(source_dir, "classes")

        if self._check_javac():
            compiled = self._compile(src_dir, class_dir)

        # Build jar
        with zipfile.ZipFile(output_jar, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add compiled classes or source files
            if compiled and os.path.isdir(class_dir):
                for root, dirs, files in os.walk(class_dir):
                    for f in files:
                        if f.endswith(".class"):
                            filepath = os.path.join(root, f)
                            arcname = os.path.relpath(filepath, class_dir)
                            zf.write(filepath, arcname)
                print(f"  ✅ Added compiled classes")
            else:
                # Add Java source files as fallback
                for root, dirs, files in os.walk(src_dir):
                    for f in files:
                        if f.endswith(".java"):
                            filepath = os.path.join(root, f)
                            arcname = os.path.relpath(filepath, src_dir)
                            zf.write(filepath, arcname)
                print(f"  📄 Added source files (no compilation)")

            # Add resources
            if os.path.isdir(res_dir):
                for root, dirs, files in os.walk(res_dir):
                    for f in files:
                        filepath = os.path.join(root, f)
                        arcname = os.path.relpath(filepath, res_dir)
                        zf.write(filepath, arcname)
                print(f"  📄 Added resources")

            # Add MANIFEST.MF
            manifest = "Manifest-Version: 1.0\n"
            if target_loader:
                manifest += f"Mod-Loader: {target_loader}\n"
            if target_version:
                manifest += f"Minecraft-Version: {target_version}\n"
            zf.writestr("META-INF/MANIFEST.MF", manifest)

        # Report
        size = os.path.getsize(output_jar)
        print(f"  📦 Output: {output_jar} ({size:,} bytes)")

        return output_jar

    def _check_javac(self) -> bool:
        """Check if javac is available."""
        try:
            result = subprocess.run(["javac", "-version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _compile(self, src_dir: str, class_dir: str) -> bool:
        """Attempt to compile Java source files."""
        os.makedirs(class_dir, exist_ok=True)

        java_files = list(Path(src_dir).rglob("*.java"))
        if not java_files:
            return False

        # Find Minecraft libraries (if available in lib/)
        lib_dir = os.path.join(os.path.dirname(__file__), "..", "..", "lib")
        classpath = []
        if os.path.isdir(lib_dir):
            for jar in Path(lib_dir).glob("*.jar"):
                if "cfr" not in str(jar) and "vineflower" not in str(jar):
                    classpath.append(str(jar))

        cmd = ["javac", "-d", class_dir, "-source", "17", "-target", "17"]
        if classpath:
            cmd.extend(["-cp", ":".join(classpath)])
        cmd.extend([str(f) for f in java_files])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                class_count = len(list(Path(class_dir).rglob("*.class")))
                print(f"  ✅ Compiled {class_count} classes")
                return True
            else:
                print(f"  ⚠️  Compilation failed (expected without MC libraries):")
                # Show first few errors only
                errors = result.stderr.strip().split("\n")[:5]
                for e in errors:
                    print(f"    {e}")
                return False
        except subprocess.TimeoutExpired:
            print("  ⚠️  Compilation timed out")
            return False
