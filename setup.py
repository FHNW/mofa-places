from setuptools import setup, find_packages


install_requires = open('requirements.txt').readlines()

setup(name='mofa-places',
    version='0.1',
    packages=find_packages(),
    description='',
    author='FHNW',
    author_email='webmaster@fhnw.ch',
    url='https://github.com/FHNW/mofa-places',
    include_package_data=True,
    setup_requires=["setuptools"],
    install_requires=install_requires,
    test_suite="mofa_places.tests",
)
