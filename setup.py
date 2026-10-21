from setuptools import setup, find_packages
import os


def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

setup(
    name="CreMail",
    version="2.3.0",
    author="QiuMing",
    author_email="mocre_rx@foxmail.com",
    description="A powerful and easy-to-use Python email sending module with support for multiple configuration methods, async sending, and verification code generation.",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/MoCre-QiuMing/CreMail",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Communications :: Email",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    # 同步发信完全零依赖（smtplib 为标准库）；aiosmtplib/jinja2 为可选依赖，见 extras_require
    install_requires=[],
    extras_require={
        "async": ["aiosmtplib>=3.0.0"],
        "template": ["jinja2>=3.0.0"],
        "all": ["aiosmtplib>=3.0.0", "jinja2>=3.0.0"],
    },
)