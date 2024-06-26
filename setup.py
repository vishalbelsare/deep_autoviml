############################################################################################
#Copyright 2021 Google LLC

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
############################################################################################
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="deep_autoviml",
    version="0.0.85",
    author="Ram Seshadri",
    # author_email="author@example.com",
    description="Automatically Build Deep Learning Models and Pipelines fast!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='Apache License 2.0',
    url="https://github.com/AutoViML/deep_autoviml",
    packages = [
        "deep_autoviml",
        "deep_autoviml.data_load",
        "deep_autoviml.modeling",
        "deep_autoviml.models",
        "deep_autoviml.preprocessing",
        "deep_autoviml.utilities",
    ],
    include_package_data=True,
    install_requires=[
        "ipython",
        "jupyter",
        "tensorflow>=2.8.0,<=2.12.1",
        "matplotlib>3.7.4",
        "numpy>=1.24",
        "pandas>=1.1.3, <2.0",
        "scikit-learn>=0.24,<=1.2.2",
        "regex",
        "emoji",
        "storm-tuner>=0.0.8",
        "optuna",
        "tensorflow_hub~=0.12.0",
        "tensorflow-text>=2.8.0,<=2.12.1",
        "tensorboard>=2.8.0,<=2.12.3",
        "xlrd"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
