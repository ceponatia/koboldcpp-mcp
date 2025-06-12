#!/usr/bin/env python3
"""
Setup script for KoboldCpp MCP Server

A Model Context Protocol (MCP) server that enables Claude Code to interact
with local KoboldCpp instances for AI capabilities while maintaining complete
data privacy and control.
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# Get the directory containing this setup.py file
here = Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = ""
readme_path = here / "README.md"
if readme_path.exists():
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

# Read requirements from requirements.txt
requirements = []
requirements_path = here / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Version information
version = "1.0.0"
version_file = here / "src" / "__version__.py"
if version_file.exists():
    exec(open(version_file).read())

setup(
    name="koboldcpp-mcp",
    version=version,
    description="MCP server for KoboldCpp integration with Claude Code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Brian",
    author_email="",
    url="https://github.com/ceponatia/koboldcpp-mcp",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "Intended Audience :: System Administrators",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Framework :: AsyncIO",
    ],
    keywords="mcp model-context-protocol koboldcpp ai llm claude-code websocket",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "myst-parser>=1.0.0",
        ],
        "testing": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "aioresponses>=0.7.4",
        ]
    },
    entry_points={
        "console_scripts": [
            "koboldcpp-mcp=koboldcpp_mcp_server.cli:main",
        ],
    },
    package_data={
        "koboldcpp_mcp_server": [
            "config/*.json",
            "examples/*.py",
            "docs/*.md",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    platforms=["any"],
    license="MIT",
    
    # Additional metadata for PyPI
    project_urls={
        "Homepage": "https://github.com/ceponatia/koboldcpp-mcp",
        "Documentation": "https://github.com/ceponatia/koboldcpp-mcp/blob/main/docs/",
        "Repository": "https://github.com/ceponatia/koboldcpp-mcp.git",
        "Bug Tracker": "https://github.com/ceponatia/koboldcpp-mcp/issues",
        "Changelog": "https://github.com/ceponatia/koboldcpp-mcp/blob/main/CHANGELOG.md",
    },
    
    # Package discovery configuration
    # Exclude test directories from the package
    exclude=["tests*", "docs*", "examples*"],
    
    # Minimum requirements check
    setup_requires=[
        "setuptools>=45",
        "wheel",
    ],
)

# Post-install message
if __name__ == "__main__":
    print("\n" + "="*60)
    print("KoboldCpp MCP Server installation completed successfully!")
    print("="*60)
    print("\nQuick Start:")
    print("1. Start your KoboldCpp instance:")
    print("   koboldcpp --model your_model.gguf --port 5001")
    print("\n2. Run the MCP server:")
    print("   koboldcpp-mcp server")
    print("\n3. Configure Claude Code to use this MCP server")
    print("\nFor detailed setup instructions, see:")
    print("https://github.com/ceponatia/koboldcpp-mcp/blob/main/docs/setup.md")
    print("\nFor usage examples, see:")
    print("https://github.com/ceponatia/koboldcpp-mcp/blob/main/docs/usage.md")
    print("="*60)