from glob import glob
from pathlib import Path
from setuptools import find_packages, setup

setup(
    name='llm_highlevel', version='0.1.0', packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/llm_highlevel']),
        ('share/llm_highlevel', ['package.xml', 'README.md']),
        *[('share/llm_highlevel/' + folder, [p for p in glob(folder + '/*') if Path(p).is_file()])
          for folder in ['launch', 'config', 'prompts', 'docs']],
    ],
    install_requires=['setuptools', 'PyYAML'], zip_safe=True,
    maintainer='Ngo Thien Dac', maintainer_email='student@example.com',
    description='High-level LLM scene handling -> validated skills -> MoveIt 2 -> UR3 in Gazebo Fortress',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'llm_planner_node = llm_highlevel.planner_node:main',
        'command = llm_highlevel.command:main',
        'camera_monitor = llm_highlevel.camera_monitor:main',
    ]},
)
