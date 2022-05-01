from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.readlines()

setup(
    name='pisslink',
    author='KaasToast',
    url='https://github.com/KaasToast/Pisslink.py',
    version='1.1',
    packages=['pisslink'],
    license='MIT',
    description='Wavelink fork that works.',
    include_package_data=True,
    install_requires=requirements
)