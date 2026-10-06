"""Terminal monitor for the simulated camera/state detector.

The monitor subscribes to /llm/scene_state and displays object locations plus
occupied/free target and temporary zones while a task is running.
"""
import argparse
import json
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CameraMonitor(Node):
    def __init__(self, clear_screen=True):
        super().__init__('llm_advanced_camera_monitor')
        self.clear_screen = clear_screen
        self.received = False
        self.subscription = self.create_subscription(
            String, '/llm/scene_state', self.on_state, 10)

    @staticmethod
    def _zone_label(name):
        return name.replace('zone_', 'Zone ').replace('_', ' ').upper()

    def on_state(self, message):
        try:
            state = json.loads(message.data)
        except (TypeError, ValueError):
            return
        if not isinstance(state, dict):
            return
        self.received = True
        if self.clear_screen and sys.stdout.isatty():
            print('\033[2J\033[H', end='')
        print('=' * 64)
        print('CAMERA MONITOR — PHÁT HIỆN VẬT VÀ TRẠNG THÁI ZONE')
        print('=' * 64)
        print('Nguồn: trạng thái mô phỏng đồng bộ với MoveIt/Gazebo')
        print('Green start: ' + str(state.get('green_start_zone') or 'chưa chọn'))
        print('\nCÁC KHỐI:')
        objects = state.get('objects', {})
        for name in ('red_cube', 'yellow_cube', 'blue_cube', 'green_cube', 'orange_cube'):
            item = objects.get(name)
            if not item:
                continue
            position = item.get('position', '?')
            location = item.get('location', 'unknown')
            print(f'  {name:14s} -> {location:18s} xyz={position}')
        print('\nĐÍCH A/B/C:')
        for name in ('zone_a', 'zone_b', 'zone_c'):
            item = state.get('zones', {}).get(name, {})
            occupant = item.get('object') or 'TRỐNG'
            status = 'CHIẾM' if item.get('occupied') else 'TRỐNG'
            print(f'  {self._zone_label(name):8s} : {status:6s} {occupant}')
        print('\nVÙNG TẠM:')
        for name, item in state.get('temporary_zones', {}).items():
            occupant = item.get('object') or 'TRỐNG'
            status = 'CHIẾM' if item.get('occupied') else 'TRỐNG'
            print(f'  {name:18s}: {status:6s} {occupant}')
        print('\nĐang giữ: ' + str(state.get('held') or 'không'))
        print('CHECK được cập nhật liên tục; nhấn Ctrl+C để thoát.', flush=True)


def main(args=None):
    parser = argparse.ArgumentParser(description='Hiển thị trạng thái camera/zone của llm_advanced')
    parser.add_argument('--once', action='store_true', help='In một mẫu trạng thái rồi thoát')
    parser.add_argument('--no-clear', action='store_true', help='Không xóa màn hình giữa các mẫu')
    parsed = parser.parse_args(args)
    rclpy.init(args=args)
    node = CameraMonitor(clear_screen=not parsed.no_clear)
    try:
        if parsed.once:
            print('Đang chờ /llm/scene_state ...', flush=True)
        while rclpy.ok() and (not parsed.once or not node.received):
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
