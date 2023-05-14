from setuptools import setup
import subprocess

# Initialize and update the c-ltarchiver submodule
subprocess.call(['git', 'submodule', 'init'])
subprocess.call(['git', 'submodule', 'update'])

# Call makefile to compile the C extension before installation
subprocess.call(['make', '-C', 'c-ltarchiver'])

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='ltarchiver',
    version='0.1',
    author='Marcelo Lacerda',
    author_email='marceloslacerda@gmail.com',
    description='Long term archiving program',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/marceloslacerda/ltarchiver',
    packages=['ltarchiver'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX :: Linux',
    ],
    python_requires='>=3.7',
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            'ltarchiver-store=ltarchiver.store:run',
            'ltarchiver-restore=ltarchiver.check_and_restore:run',
        ],
    },
    data_files=[("c-ltarchiver/out/", ["c-ltarchiver/out/ltarchiver_restore", "c-ltarchiver/out/ltarchiver_store"])]
)