from setuptools import setup

setup(
    name='py-api-client',
    version='0.3',
    description='Bear Robotics Servi API client',
    author='Sajjad Taheri',
    author_email='sajjad@bearrobotics.ai',
    packages=['client'],
    install_requires=[
        'pika>=1.3.0',
        'cryptography>=38.0.1',
    ],
    license='mit',
    scripts=[
        'py-api-client',
        'scripts/api_client.py',
    ],
    url='https://gitlab.com/bearrobotics-public/py-api-client',
)
