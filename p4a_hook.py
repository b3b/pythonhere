from pathlib import Path

from pythonforandroid.toolchain import ToolchainCL


# LiteRT-LM GPU acceleration uses OpenCL. On Android, the required
# non-NDK native libraries must be declared in the application manifest.
#
# See:
# https://github.com/google-ai-edge/LiteRT-LM/blob/main/docs/api/kotlin/getting_started.md
#
# The libraries are optional so the APK can still be installed on devices
# that do not provide them; GPU availability is handled at runtime.
LITERT_NATIVE_LIBRARIES = """
        <uses-native-library
            android:name="libvndksupport.so"
            android:required="false" />

        <uses-native-library
            android:name="libOpenCL.so"
            android:required="false" />
"""


def after_apk_build(toolchain: ToolchainCL) -> None:
    """Add native-library declarations required for LiteRT-LM GPU support."""

    manifest = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"

    print(f"Patching manifest for LiteRT-LM GPU support: {manifest}")

    if not manifest.exists():
        raise RuntimeError(f"Generated manifest does not exist: {manifest}")

    text = manifest.read_text(encoding="utf-8")

    # libOpenCL.so is used as the marker because this hook always adds
    # both LiteRT-LM declarations together.
    if 'android:name="libOpenCL.so"' in text:
        print("LiteRT-LM native-library declarations already present")
        return

    marker = "</application>"

    if marker not in text:
        raise RuntimeError(f"Cannot find {marker!r} in {manifest}")

    updated = text.replace(
        marker,
        LITERT_NATIVE_LIBRARIES + "\n    " + marker,
        1,
    )

    manifest.write_text(updated, encoding="utf-8")
    print("Added LiteRT-LM GPU native-library declarations")
