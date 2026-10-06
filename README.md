# UR3 LLM — `llm_advanced` và `llm_highlevel`

Hai package ROS 2 cho mô phỏng tay máy UR3 trong Gazebo Fortress, dùng 9Router để chuyển câu lệnh tự nhiên thành chuỗi skill `pick`, `place`, `home`.

## Hai chế độ trong repository

| Package | Kịch bản | Vùng tạm |
|---|---|---|
| `llm_advanced` | Green chiếm ngẫu nhiên một trong A/B/C; có thể xử lý hai vật cản bằng hai vùng tạm | `temporary_zone`, `temporary_zone2` |
| `llm_highlevel` | Green chiếm một đích và thêm một khối đỏ/vàng/xanh dương nằm sai đích; khi hai vùng tạm đầy thì dùng vùng chung | `temporary_zone`, `temporary_zone2`, `common_zone` |

Cả hai package đều kiểm tra trạng thái trước khi đặt vật, gripper hai ngón chạy chung trajectory và camera RGB gắn sát carrier của đầu công tác.

## Yêu cầu

- Ubuntu 22.04, ROS 2 Humble.
- Gazebo Fortress/Gazebo Sim, MoveIt 2, `ur_description`, `ur_moveit_config`, `ros_gz_sim`, `ros_gz_bridge`.
- 9Router đang chạy tại `http://localhost:20128`.

## Cài đặt và build

Đặt repository này trong workspace ROS 2:

```bash
cd ~/ros2_ws/src
git clone https://github.com/23020734-thiendac/llm_highAdvanced.git
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select llm_advanced llm_highlevel --symlink-install
source install/setup.bash
```

## Cấu hình 9Router

Không lưu API key vào GitHub. Trong mỗi terminal chạy planner, nhập key cục bộ:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export NINE_ROUTER_BASE_URL="http://localhost:20128/v1"
export NINE_ROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
read -rsp "NINE_ROUTER_API_KEY: " NINE_ROUTER_API_KEY; echo
export NINE_ROUTER_API_KEY
export ROS_DOMAIN_ID=68
```

Không dán API key vào README, mã nguồn hoặc commit. Khóa đã xuất hiện công khai trong lịch sử trao đổi nên nên thu hồi và tạo khóa mới trên 9Router.

## Mức 2 — hai đích có vật chiếm (`llm_advanced`)

Terminal launch:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export NINE_ROUTER_BASE_URL="http://localhost:20128/v1"
export NINE_ROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
read -rsp "NINE_ROUTER_API_KEY: " NINE_ROUTER_API_KEY; echo
export NINE_ROUTER_API_KEY
export ROS_DOMAIN_ID=68
ros2 launch llm_advanced llm_robot.launch.py
```

Khi terminal launch báo `READY`, mở terminal command và chạy:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
export NINE_ROUTER_BASE_URL="http://localhost:20128/v1"
export NINE_ROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
read -rsp "NINE_ROUTER_API_KEY: " NINE_ROUTER_API_KEY; echo
export NINE_ROUTER_API_KEY

ros2 run llm_advanced command --timeout 1800 \
  "Arrange all objects according to my student ID."
```

Planner sẽ kiểm tra đích trước khi đặt. Nếu đích đã có vật, robot gắp vật đang chiếm và đưa vào vùng tạm còn trống, về `home`, rồi mới đặt vật đúng màu.

## Mức 3 — ba đích có vật chiếm (`llm_highlevel`)

Terminal launch:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export NINE_ROUTER_BASE_URL="http://localhost:20128/v1"
export NINE_ROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
read -rsp "NINE_ROUTER_API_KEY: " NINE_ROUTER_API_KEY; echo
export NINE_ROUTER_API_KEY
export ROS_DOMAIN_ID=68
ros2 launch llm_highlevel llm_robot.launch.py
```

Terminal command:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
export NINE_ROUTER_BASE_URL="http://localhost:20128/v1"
export NINE_ROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
read -rsp "NINE_ROUTER_API_KEY: " NINE_ROUTER_API_KEY; echo
export NINE_ROUTER_API_KEY

ros2 run llm_highlevel command --timeout 1800 \
  "Arrange all objects according to my student ID."
```

Ở chế độ này green và một khối theo MSSV có thể cùng chiếm các đích. Nếu `temporary_zone` và `temporary_zone2` đã đầy, executor dùng `common_zone` màu xám rồi tiếp tục xử lý.

## Điều khiển PLUS bằng bàn phím

Mở terminal riêng sau khi launch:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
ros2 run llm_advanced command --teleop
```

Hoặc với chế độ ba đích:

```bash
ros2 run llm_highlevel command --teleop
```

Phím điều khiển:

- `a`: đưa khối cam vào zone A.
- `b`: đưa khối cam vào zone B.
- `c`: đưa khối cam vào zone C.
- `h`: reset cảnh và đưa robot về home.
- `q`: thoát teleop, không tắt Gazebo.

Nếu workspace đã cài package nền, lệnh tương đương là `ros2 run ur3_llm_control command --teleop`.

## Terminal camera và kiểm tra trạng thái

Camera monitor in vị trí từng khối, trạng thái `TRỐNG/CHIẾM` của A/B/C, vùng tạm và vật đang được giữ:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
ros2 run llm_advanced camera_monitor
```

Hoặc:

```bash
ros2 run llm_highlevel camera_monitor
```

Xem topic camera:

```bash
ros2 topic list | grep wrist_camera
ros2 topic hz /wrist_camera/image_raw
ros2 run rqt_image_view rqt_image_view
```

Trong `rqt_image_view`, chọn `/wrist_camera/image_raw`. Thông tin hiệu chuẩn nằm ở `/wrist_camera/camera_info`.

## Lệnh mức 1 — xử lý từng vật

```bash
ros2 run llm_advanced command "Đưa khối màu đỏ vào vùng B."
ros2 run llm_advanced command "Move the blue cube to zone A."
ros2 run llm_advanced command "Hãy lấy khối màu vàng và đặt nó vào ô C."
ros2 run llm_advanced command "Đưa khối cam vào vùng tạm thời."
```

Khi đang chạy `llm_highlevel`, thay `llm_advanced` trong các lệnh trên bằng `llm_highlevel`.

## Kiểm thử

```bash
cd ~/ros2_ws/src/llm_highAdvanced
PYTHONPATH=llm_advanced python3 -m unittest discover -s llm_advanced/test -v
PYTHONPATH=llm_highlevel python3 -m unittest discover -s llm_highlevel/test -v
```

## Cấu trúc chính

```text
llm_advanced/                 # Hai vùng tạm
llm_highlevel/                # Ba vùng tạm, có common_zone
├── config/                   # scene, controller, MSSV
├── launch/                   # llm_robot.launch.py
├── llm_<package>/            # planner, skill, camera monitor, simulation
├── prompts/                  # prompt cho LLM
└── test/                     # kiểm thử validator/executor
```
