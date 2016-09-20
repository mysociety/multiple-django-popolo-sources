from setuptools import setup, find_packages
setup(
    name = "multiple-django-popolo-sources",
    version = "0.0.2",
    packages = find_packages(),
    author = "Mark Longair",
    author_email = "mark@mysociety.org",
    description = "Handle django-popolo data from multiple separate sources",
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
