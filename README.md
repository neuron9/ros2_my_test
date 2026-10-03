AMR в Gazebo: автономная GPS-навигация (ROS 2 Humble)

Автономный мобильный робот в симуляторе Gazebo Classic, который стартует из
точки A, объезжает статические препятствия и доезжает до точки B,
следуя по GPS-waypoints. Используются лидар, камера глубины (аналог Orbbec
Astra), GPS и IMU; навигация построена на Nav2 + robot_localization.

VirtualBox Ubuntu 22.04. Весь код предназначен для исполнения на Ubuntu.

| Компонент   | Версия                         			|
|-------------|-------------------------------------------------|
| ОС          | Ubuntu 22.04 (VirtualBox)      			|
| ROS         | ROS 2 Humble               			|
| Симулятор   | Gazebo Classic 11          			|
| Навигация   | Nav2 (navigation2)           			|
| Локализация | robot_localization (dual EKF + navsat_transform)|
| Язык узлов  | Python                         			|

src/
  amr_description/   URDF/Xacro робота, сенсоры, gazebo-плагины
  amr_gazebo/        мир course.world + спавн робота
  amr_navigation/    dual EKF, navsat, Nav2 config, RViz, Python-узлы
  amr_bringup/       запуск всего одной командой
scripts/
  record_rosbag.sh          запись демонстрационного rosbag
quickstart/
  install_and_run.sh        apt + rosdep + colcon + bringup одной командой


Робот и сенсоры (amr_description)
Собственный дифференциальный робот (URDF/Xacro) с макросами инерции. Плагины
Gazebo Classic:

| Сенсор / привод | Плагин | Топик(и) | TF frame |
|---|---|---|---|
| Дифф. привод | libgazebo_ros_diff_drive.so | /cmd_vel, /odom | base_footprint |
| 2D лидар | libgazebo_ros_ray_sensor.so | /scan | lidar_link |
| Камера глубины | libgazebo_ros_camera.so (type="depth") | /camera/image_raw, /camera/depth/image_raw, /camera/points, /camera/camera_info | camera_depth_optical_frame |
| IMU | libgazebo_ros_imu_sensor.so | /imu | imu_link |
| GPS | libgazebo_ros_gps_sensor.so | /gps/fix (sensor_msgs/NavSatFix) | gps_link |

Диф-привод публикует только одометрию и TF колёс (publish_odom_tf=false);
цепочку map -> odom -> base_footprint строит robot_localization.

Мир (amr_gazebo/worlds/course.world)
Плоская поверхность, 4 статических препятствия (боксы и цилиндры), визуальные
зоны старта (зелёная) и финиша (красная). Блок <spherical_coordinates> задаёт
датум GPS; heading_deg=180 компенсирует известный баг ENU в Gazebo Classic,
чтобы GPS выдавал корректные East/North/Up.

Дерево TF
map --(ekf_filter_node_map / navsat_transform)--> odom
odom --(ekf_filter_node_odom)--> base_footprint
base_footprint --(URDF)--> base_link --> {wheels, lidar_link, camera_link, imu_link, gps_link}


Поток данных
Gazebo --/scan, /camera/points--> Nav2 (costmaps, planner, controller) --/cmd_vel--> Gazebo
Gazebo --/odom, /imu-----------> ekf_odom ----> TF odom->base_footprint
Gazebo --/gps/fix, /imu--------> navsat_transform --/odometry/gps--> ekf_map --> TF map->odom
navsat_transform --/fromLL service--> gps_waypoint_follower --followWaypoints()--> Nav2


Быстрый старт (Ubuntu 22.04)
Из корня репозитория — установка зависимостей, сборка и запуск симуляции:
bash
chmod +x quickstart/install_and_run.sh
./quickstart/install_and_run.sh


На слабой VM без RViz:
bash
./quickstart/install_and_run.sh use_rviz:=false


Повторный запуск без apt/rosdep и без пересборки:
bash
./quickstart/install_and_run.sh --skip-install --skip-build


Сборка
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash


Запуск
ros2 launch amr_bringup bringup.launch.py


Запустится Gazebo + RViz, поднимутся локализация и Nav2, а через ~30 секунд
автоматически стартует следование по всем GPS-waypoints из точки A в точку B
(короткий коридор через промежуточные точки, не прямой заезд на финиш).

не запускать waypoints автоматически (для ручной отправки целей из RViz)
ros2 launch amr_bringup bringup.launch.py autostart_waypoints:=false

свой файл waypoints
ros2 launch amr_bringup bringup.launch.py waypoints_file:=/path/to/waypoints.yaml

Ручной запуск следования по точкам (если autostart_waypoints:=false):
ros2 run amr_navigation gps_waypoint_follower


Waypoints
Маршрут задаётся в GPS-координатах в
[src/amr_navigation/config/waypoints.yaml](src/amr_navigation/config/waypoints.yaml).
Датум (lat 55.7558, lon 37.6173) совпадает со <spherical_coordinates> мира и
с параметром datum в
[dual_ekf_navsat.yaml](src/amr_navigation/config/dual_ekf_navsat.yaml), поэтому
начало карты совпадает с точкой A. Узел gps_waypoint_follower переводит каждую
точку в кадр map через сервис /fromLL и отправляет весь список в Nav2
(followWaypoints), чтобы пройти короткий маршрут: обход с севера → проход
между препятствиями → финиш B.