# Bài thực hành 3 — LLM nâng cao (`llm_advanced`)

Package ROS 2 độc lập cho mô phỏng UR3 trong Gazebo Fortress. Package cũ `ur3_llm_control` được giữ nguyên; tuần 3 chạy bằng package mới này.

## Điểm mới

- Có 5 khối trên bàn: đỏ, vàng, xanh dương, cam và xanh lá.
- `green_cube` được chọn ngẫu nhiên vào một trong ba đích A/B/C khi planner khởi động. Vì vậy mỗi lần chạy có thể xuất hiện một kịch bản chiếm đích khác nhau.
- Khối cam vẫn là vật PLUS điều khiển bằng teleop: `a` đưa cam vào A, `b` đưa cam vào B, `c` đưa cam vào C, `h` reset, `q` thoát teleop.
- Có hai vùng tạm `temporary_zone` (cam) và `temporary_zone2` (tím). Cam luôn ưu tiên vùng cam; green luôn ưu tiên vùng tím. Khi một đích đang bị chiếm, executor kiểm tra zone, gắp vật đang chiếm và đặt vào vùng tạm phù hợp trước khi đặt vật đúng vào đích.
- Có node `camera_monitor` hiển thị liên tục vị trí các khối và trạng thái trống/chiếm của A/B/C cùng hai vùng tạm trong một terminal riêng.
- Có camera RGB mô phỏng gắn sát mặt bên carrier của `grasp_link`, kèm bản gá bạc mỏng không tạo khe hở. Trục quang học song song hướng vươn của EF/jaws. Ảnh được bridge sang `/wrist_camera/image_raw`; thông tin camera ở `/wrist_camera/camera_info`.
- Lệnh `Arrange all objects according to my student ID.` vẫn xếp ba khối theo MSSV 23020734: xanh dương → A, đỏ → B, vàng → C. Khối xanh lá được xem là vật cản trong lệnh này.
- Các skill `pick`, `place`, `home` tiếp tục điều khiển MoveIt và gripper; hai ngón gripper dùng cùng một trajectory để mở/đóng đồng thời.

## Cài đặt và build

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select llm_advanced --symlink-install
source install/setup.bash
```

## Cấu hình 9Router

Không ghi API key vào mã nguồn. Mỗi terminal chạy planner cần các biến môi trường:

```bash
export NINE_ROUTER_BASE_URL="http://localhost:20128/v1"
export NINE_ROUTER_MODEL="oc/muse-spark-1.3-contributor-free"
export NINE_ROUTER_API_KEY="<API key của bạn>"
export ROS_DOMAIN_ID=68
```

## Chạy mô phỏng

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch llm_advanced llm_robot.launch.py
```

Chờ terminal launch báo `READY`, sau đó mở terminal khác và nạp lại các biến môi trường ở trên.

## Mức 1 — xử lý từng khối

```bash
ros2 run llm_advanced command "Đưa khối màu đỏ vào vùng B."
ros2 run llm_advanced command "Move the blue cube to zone A."
ros2 run llm_advanced command "Hãy lấy khối màu vàng và đặt nó vào ô C."
ros2 run llm_advanced command "Đưa khối cam vào vùng tạm thời."
```

## Camera Detect + check

Mở terminal riêng sau khi launch và chạy:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
ros2 run llm_advanced camera_monitor
```

Terminal này sẽ in vị trí vật, `FREE/CHIẾM`, và cập nhật trong khi lệnh sắp xếp đang chạy.

Xem hình ảnh RGB từ camera gắn trên tay máy:

```bash
ros2 topic list | grep wrist_camera
ros2 run rqt_image_view rqt_image_view
```

## Mức 2 — nhiều khối trong một câu lệnh

```bash
ros2 run llm_advanced command --timeout 1800 \
  "Arrange all objects according to my student ID."
```

LLM chỉ sinh danh sách skill; validator kiểm tra schema, vật, đích và thứ tự trước khi robot chuyển động.

## Điều khiển khối Orange bằng teleop

Bật teleop trong terminal riêng:

```bash
ros2 run llm_advanced command --teleop
```

Nhấn `a`, `b` hoặc `c` để đặt cam vào đích tương ứng, rồi chạy lệnh mức 2. Executor sẽ đưa cam sang vùng tạm trước khi xếp khối đúng. Nhấn `h` để reset cảnh và chọn lại vị trí ngẫu nhiên cho green cube.

## Kiểm thử nhanh

```bash
cd ~/ros2_ws/src/TuongTacNguoi_Robot
PYTHONPATH=llm_advanced python3 -m unittest discover -s llm_advanced/test -v
```
