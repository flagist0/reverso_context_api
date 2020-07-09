from setuptools import setup

setup(
    name='reverso_context_api',
    version='0.5',
    packages=['reverso_context_api'],
    url='https://github.com/flagist0/reverso_context_api',
    download_url="https://github.com/flagist0/reverso_context_api/archive/0.5.zip",
    license='MIT License',
    author='Alexander Presnyakov',
    author_email='flagist0@gmail.com',
    description='Simple Python wrapper for Reverso Context API',
    keywords=["reverso context", "api"],
    install_requires=["requests", "beautifulsoup4"]
)
