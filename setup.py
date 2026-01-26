from setuptools import setup, find_packages

setup(
    name="code2map",
    version="0.1.0",
    description="Transform large source code into semantic maps for AI-driven analysis and review",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="code2map developers",
    url="https://github.com/example/code2map",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "javalang>=0.13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": ["code2map=code2map.cli:main"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
