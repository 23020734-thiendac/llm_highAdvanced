# Bài thực hành 3 — LLM nâng cao (`llm_highlevel`)

Package ROS 2 độc lập cho mô phỏng UR3 trong Gazebo Fortress. Package cũ `ur3_llm_control` được giữ nguyên; tuần 3 chạy bằng package mới này.

## Điểm mới

- Có 5 khối trên bàn: đỏ, vàng, xanh dương, cam và xanh lá.
- `green_cube` được chọn ngẫu nhiên vào một trong ba đích A/B/C khi planner khởi động. Vì vậy mỗi lần chạy có thể xuất hiện một kịch bản chiếm đích khác nhau.
- Đồng thời, một trong ba khối theo MSSV (`red_cube`, `yellow_cube`, `blue_cube`) được chọn ngẫu nhiên và đặt vào một trong hai zone sai của nó. Zone sai được chọn khác vị trí của green để không chồng vật; executor phải tự dọn vật này trước khi đặt đúng.
- Khối cam vẫn là vật PLUS điều khiển bằng teleop: `a` đưa cam vào A, `b` đưa cam vào B, `c` đưa cam vào C, `h` reset, `q` thoát teleop.
- Có ba vùng tạm: `temporary_zone` (cam), `temporary_zone2` (tím) và `common_zone` (xám, ở mép đối diện và thẳng hàng zone B). Mọi vật đều có thể dùng bất kỳ vùng tạm nào còn trống; khi hai vùng đầu đã đầy, executor dùng common_zone.
- Có node `camera_monitor` hiển thị liên tục vị trí các khối, green start, vật bị đặt sai zone và trạng thái trống/chiếm của A/B/C cùng hai vùng tạm trong một terminal riêng.
- Có camera RGB mô phỏng gắn sát mặt bên carrier của `grasp_link`, kèm bản gá bạc mỏng không tạo khe hở. Trục quang học song song hướng vươn của EF/jaws, được phát qua `/wrist_camera/image_raw` và `/wrist_camera/camera_info`.
- Lệnh `Arrange all objects according to my student ID.` vẫn xếp ba khối theo MSSV 23020734: xanh dương → A, đỏ → B, vàng → C. Khối xanh lá được xem là vật cản trong lệnh này.
- Các skill `pick`, `place`, `home` tiếp tục điều khiển MoveIt và gripper; hai ngón gripper dùng cùng một trajectory để mở/đóng đồng thời.

## Cài đặt và build

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select llm_highlevel --symlink-install
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
ros2 launch llm_highlevel llm_robot.launch.py
```

Chờ terminal launch báo `READY`, sau đó mở terminal khác và nạp lại các biến môi trường ở trên.

## Mức 1 — xử lý từng khối

```bash
ros2 run llm_highlevel command "Đưa khối màu đỏ vào vùng B."
ros2 run llm_highlevel command "Move the blue cube to zone A."
ros2 run llm_highlevel command "Hãy lấy khối màu vàng và đặt nó vào ô C."
ros2 run llm_highlevel command "Đưa khối cam vào vùng tạm thời."
```

## Camera Detect + check

Mở terminal riêng sau khi launch và chạy:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
ros2 run llm_highlevel camera_monitor
```

Terminal này sẽ in vị trí vật, `FREE/CHIẾM`, và cập nhật trong khi lệnh sắp xếp đang chạy.

Để xem hình ảnh thật từ camera gắn trên tay máy, mở terminal khác:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=68
ros2 topic list | grep wrist_camera
ros2 run rqt_image_view rqt_image_view
```

Trong cửa sổ `rqt_image_view`, chọn topic `/wrist_camera/image_raw` ở danh sách Image Topic. `camera_monitor` là node kiểm tra trạng thái hình học của scene.

## Mức 2 — nhiều khối trong một câu lệnh

```bash
ros2 run llm_highlevel command --timeout 1800 \
  "Arrange all objects according to my student ID."
```

LLM chỉ sinh danh sách skill; validator kiểm tra schema, vật, đích và thứ tự trước khi robot chuyển động.
Nếu temporary_zone và temporary_zone2 đã có vật, occupant tiếp theo được chuyển vào common_zone.

## Điều khiển khối Orange bằng teleop

Bật teleop trong terminal riêng:

```bash
ros2 run llm_highlevel command --teleop
```

Nhấn `a`, `b` hoặc `c` để đặt cam vào đích tương ứng, rồi chạy lệnh mức 2. Executor sẽ đưa cam sang vùng tạm trước khi xếp khối đúng. Nhấn `h` để reset cảnh, chọn lại vị trí ngẫu nhiên cho green cube và chọn lại một vật đỏ/vàng/xanh dương ở zone sai.

## Kiểm thử nhanh

```bash
cd ~/ros2_ws/src/TuongTacNguoi_Robot
PYTHONPATH=llm_highlevel python3 -m unittest discover -s llm_highlevel/test -v
```
