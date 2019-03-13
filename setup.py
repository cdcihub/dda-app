from distutils.core import setup

setup(
        name='dda-worker',
        version='1.0',
        packages=["ddaworker"],
        package_data     = {
            "": [
                "*.txt",
                "*.md",
                "*.rst",
                "*.py"
                ]
            },
        install_requires= ["flask", "raven", "logzio-python-handler", "pathlib", "mattersend"],
        license='Creative Commons Attribution-Noncommercial-Share Alike license',
        long_description=open('README.md').read(),
        )
