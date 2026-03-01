from setuptools import setup, find_packages
import os


def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

setup(
    name="CreMail",
    version="1.2.1",
    author="Your Name",
    author_email="your.email@example.com",
    description="A powerful and easy-to-use Python email sending module with support for multiple configuration methods, async sending, and verification code generation.",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/cremail",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Communications :: Email",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6",
    install_requires=[
        "aiosmtplib>=3.0.0; python_version>='3.6'", 
        "jinja2>=3.0.0; python_version>='3.6'",     
    ],
    extras_require={
        "async": ["aiosmtplib>=3.0.0"],
        "template": ["jinja2>=3.0.0"],
        "all": ["aiosmtplib>=3.0.0", "jinja2>=3.0.0"],
    },
    keywords="email, smtp, send, async, verification, code",
)