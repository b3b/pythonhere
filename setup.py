from setuptools import setup, convert_path

main_ns = {}
with open(convert_path("pythonhere/version_here.py")) as ver_file:
    exec(ver_file.read(), main_ns)
    version = main_ns["__version__"]

with open(convert_path("README.rst")) as readme_file:
    long_description = readme_file.read()


setup(
    name="pythonhere",
    version=main_ns["__version__"],
    packages=[
        "pythonhere",
        "pythonhere.magic_here",
        "pythonhere.ui_here",
    ],
    description="Here is the Kivy based app to run code from the Jupyter magic %there",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="b3b",
    author_email="ash.b3b@gmail.com",
    install_requires=[
        "kivy>=2.0.0",
        "herethere>=0.1.0,<0.2.0",
        "ifaddr",
        "ipython",
        "ipywidgets",
        "nest_asyncio",
        "Pillow",
    ],
    extras_require={
        "dev": [
            "black",
            "codecov",
            "docutils",
            "flake8",
            "jupytext",
            "pylint",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-mock",
        ],
        "docker": [
            "jupytext==1.7.1"
        ]
    },
    url="https://github.com/b3b/ipython-pythonhere",
    project_urls={
        'Changelog': 'https://github.com/b3b/pythonhere/blob/master/CHANGELOG.rst',
    },
    # https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="android ipython jupyter magic kivy",
    license="MIT",
)
