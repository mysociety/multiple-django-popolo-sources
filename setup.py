from setuptools import setup, find_packages
from os.path import join, dirname

with open(join(dirname(__file__), 'README.rst')) as f:
    readme_text = f.read()

setup(
    name = "multiple-django-popolo-sources",
    version = "0.0.3",
    packages = find_packages(),
    author = "Mark Longair",
    author_email = "mark@mysociety.org",
    description = "Handle django-popolo data from multiple separate sources",
    long_description = readme_text,
    license = "AGPL",
    keywords = "django popolo civic-tech",
    install_requires = [
        'Django>=1.7',
        'mysociety-django-popolo>=0.0.6',
        'requests',
    ],
    extras_require={
        'test': [
            'coverage',
            'mock',
        ],
    }
)
