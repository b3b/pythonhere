from pythonforandroid.recipes.freetype import FreetypeRecipe


class FreetypeSourceForgeRecipe(FreetypeRecipe):
    # FreeType officially publishes stable releases on both Savannah and
    # SourceForge:
    # https://freetype.org/download/
    #
    # python-for-android normally downloads FreeType from Savannah. We use
    # the official SourceForge release mirror instead because Savannah's
    # download service has caused intermittent HTTP 502 build failures.
    url = (
        "https://downloads.sourceforge.net/project/freetype/"
        "freetype2/{version}/freetype-{version}.tar.gz"
    )


recipe = FreetypeSourceForgeRecipe()
