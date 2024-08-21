from setuptools import setup, find_packages

setup(
    name='egov_law',
    version='1.0.3',
    packages=find_packages(),
    install_requires=[
        'requests',
        'lxml'
    ],
    url='https://github.com/lupin-oomura/egov_law.git',
    author='Shin Oomura',
    author_email='shin.oomura@gmail.com',
    description='',
)
