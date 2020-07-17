from setuptools import setup


setup(
    name='powertools',
    version='0.0.1',
    description=(
        "Enables the user to organize transformations of data with PySpark as a regular Python"
        "package."
    ),
    packages=['powertools'],
    install_requires=[
        'pandas==0.23.4',
        'pyarrow==0.15.1',
        'pyspark==2.4.4',
    ]
)
