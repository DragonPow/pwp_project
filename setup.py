from setuptools import setup, find_packages
import json

with open('config.json') as f:
    config = json.load(f)

setup(
    name=config.get('app_name', 'electronic_office'),
    version=config.get('app_version', '0.0.1'),
    description=config.get('app_description', ''),
    author=config.get('app_author', ''),
    author_email=config.get('app_email', ''),
    license=config.get('app_license', 'GPL-3.0'),
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'frappe',
        'minio==7.1.12',
        'requests==2.28.1',
        'cryptography==3.4.8',
        'PyPDF2==3.0.1',
        'reportlab==3.6.8',
        'pandas==1.5.0',
        'numpy==1.23.3',
    ],
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
)
