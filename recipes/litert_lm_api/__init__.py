from pythonforandroid.recipe import PyProjectRecipe


class LiteRTLMAPIRecipe(PyProjectRecipe):
    """python-for-android recipe for Google's LiteRT-LM Python API."""

    version = "0.16.0"

    # Distribution name is "litert-lm-api", but the installed Python package
    # is imported as "litert_lm".
    site_packages_name = "litert_lm"

    # LiteRT-LM Android wheels are built for Android API 23+.
    min_ndk_api_support = 23

    @staticmethod
    def get_wheel_platform_tags(arch, ctx):
        """Return the wheel platform tag published by LiteRT-LM for this ABI."""

        # LiteRT-LM currently publishes Android wheels for these two ABIs.
        if arch == "arm64-v8a":
            return ["android_23_arm64_v8a"]

        if arch == "x86_64":
            return ["android_23_x86_64"]

        raise RuntimeError(
            f"litert-lm-api does not provide an Android wheel for {arch}"
        )


recipe = LiteRTLMAPIRecipe()
