from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.readlines()

setup(
    name='pisslink',
    author='KaasToast',
    url='https://github.com/KaasToast/Pisslink.py',
    version='V1',
    packages=['pisslink'],
    license='MIT',
    description='Minimalistic lavalink wrapper based on wavelink. Made for Pycord.',
    include_package_data=True,
    install_requires=requirements
)