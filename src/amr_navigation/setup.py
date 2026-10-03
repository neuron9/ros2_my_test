import os
from glob import glob

from setuptools import find_packages, setup

package_name = "amr_navigation"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "rviz"), glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ParamonovSY",
    maintainer_email="paramonov@example.com",
    description="Localization, Nav2 config and GPS waypoint following nodes for the AMR robot.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "gps_waypoint_follower = amr_navigation.gps_waypoint_follower:main",
            "sensor_monitor = amr_navigation.sensor_monitor:main",
        ],
    },
)
