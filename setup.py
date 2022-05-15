from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.readlines()

setup(
    name='Pisslink.py',
    author='KaasToast',
    url='https://github.com/KaasToast/Pisslink.py',
    version='1.2',
    packages=['pisslink'],
    license='MIT',
    description='An audio player for Discord with a builtin queue system, Spotify and playlist support.',
    include_package_data=True,
    install_requires=requirements,
)