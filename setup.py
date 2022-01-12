from setuptools import setup, find_packages
from os import path
import versioneer

cur_dir = path.abspath(path.dirname(__file__))

# parse requirements
with open(path.join(cur_dir, "requirements.txt"), "r") as f:
    requirements = f.read().split()

# set up additional dev requirements
dev_requirements = []
with open(path.join(cur_dir, "dev-requirements.txt"), "r") as f:
    dev_requirements = f.read().split()

setup(
    name="lume-epics",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(),
    author='SLAC National Accelerator Laboratory',
    author_email="jgarra@slac.stanford.edu",
    license="SLAC Open",
    install_requires=requirements,
    # set up development requirements
    extras_require={"dev": dev_requirements},
    url="https://github.com/slaclab/lume-epics",
    include_package_data=True,
    python_requires=">=3.7,<3.9",
    entry_points={
        "console_scripts": [
        "render-from-template=lume_epics.commands.render_from_template:render_from_template",
        "serve-from-template=lume_epics.commands.serve_from_template:serve_from_template"]
    },
)