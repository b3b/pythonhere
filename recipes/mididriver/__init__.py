from os.path import exists, join, isdir

import sh
from pythonforandroid.logger import shprint, info
from pythonforandroid.recipe import NDKRecipe
from pythonforandroid.util import current_directory


class MididriverRecipe(NDKRecipe):
    """Download and exract Midi Driver compiled libraries."""
    name = "mididriver"
    generated_libraries = ["libmidi.so"]
    url = "https://github.com/b3b/mididriver/releases/download/v{version}/MidiDriver-v{version}.aar"
    version = "1.19py31"
    sha256sum = "152003f72a8cc6adb77219b1edc4e5a6c7c32bfe853b31ef4d734e847f1f2e73"

    def unpack(self, arch):
        build_dir = self.get_build_container_dir(arch)
        filename = self.versioned_url.split("/")[-1]

        with current_directory(build_dir):
            directory_name = self.get_build_dir(arch)

            if not exists(directory_name) or not isdir(directory_name):
                extraction_filename = join(
                    self.ctx.packages_path, self.name, filename)
                try:
                    sh.unzip(extraction_filename)
                except (sh.ErrorReturnCode_1, sh.ErrorReturnCode_2):
                    # return code 1 means unzipping had
                    # warnings but did complete,
                    # apparently happens sometimes with
                    # github zips
                    pass
                shprint(sh.mv, "jni", directory_name)
            else:
                info("{} is already unpacked, skipping".format(self.name))

    def build_arch(self, arch, *extra_args):
        with current_directory(self.get_build_dir(arch.arch)):
            self.install_libs(
                arch,
                join(arch.arch, "libmidi.so"),
            )


recipe = MididriverRecipe()
