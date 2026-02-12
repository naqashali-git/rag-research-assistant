"""Setup configuration for RAG Research Assistant."""

from setuptools import setup, find_packages

setup(
    name='rag-research-assistant',
    version='1.0.0',
    description='Local-first, security-constrained RAG research assistant',
    author='Your Name',
    packages=find_packages(),
    python_requires='>=3.11',
    install_requires=[
        'python-dotenv==1.0.0',
        'PyYAML==6.0',
        'click==8.1.7',
        'colorama==0.4.6',
        'llama-cpp-python==0.2.27',
        'langchain==0.1.16',
        'sentence-transformers==2.2.2',
        'PyPDF2==3.0.1',
        'python-docx==0.8.11',
        'markdown==3.5.1',
        'chromadb==0.4.22',
        'requests==2.31.0',
        'cryptography==41.0.7',
    ],
)