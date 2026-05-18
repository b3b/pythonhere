# Workaround for `ImportError: dlopen failed: cannot locate symbol`
# https://github.com/kivy/python-for-android/issues/3329

from pythonforandroid.recipes.cryptography import (
    CryptographyRecipe as UpstreamCryptographyRecipe,
)


class CryptographyRecipe(UpstreamCryptographyRecipe):
    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)

        python_link_version = self.ctx.python_recipe.link_version
        link_arg = f"-Clink-arg=-lpython{python_link_version}"

        rustflags = env.get("RUSTFLAGS", "").split()

        if link_arg not in rustflags:
            rustflags.append(link_arg)

        env["RUSTFLAGS"] = " ".join(rustflags)

        return env


recipe = CryptographyRecipe()
