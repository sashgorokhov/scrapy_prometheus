from distutils.core import setup

with open('README.rst') as readme:
    long_description = readme.read()

VERSION = '2.0.1'

setup(
    install_requires=['prometheus_client'],
    name='scrapy_prometheus',
    version=VERSION,
    py_modules=['scrapy_prometheus'],
    # TODO: Add url and download_url when github repo will be created
    keywords=['scrapy', 'prometheus', 'pushgateway', 'monitoring'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Environment :: Plugins',
        'Framework :: Scrapy',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Monitoring',
        'Programming Language :: Python :: 3.5',  # TODO: Add more when tests added
    ],
    long_description=long_description,
    license='MIT License',
    author='sashgorokhov',
    author_email='sashgorokhov@gmail.com',
    description='Exporting scrapy stats as prometheus metrics through pushgateway service',
)