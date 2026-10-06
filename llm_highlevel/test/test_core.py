import copy
import json
import os
import random
from pathlib import Path
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from xml.etree import ElementTree as ET

from llm_highlevel.configuration import (choose_temporary_zone, load_student,
                                         read_yaml, randomize_start_positions, student_assignment)
from llm_highlevel.llm_planner import LLMPlanner, PlannerError
from llm_highlevel.skill_executor import SkillExecutor
from llm_highlevel.task_validator import InvalidPlan, validate_plan
from llm_highlevel.simulation import add_parallel_gripper, world_sdf

ROOT = Path(__file__).resolve().parents[1]
PLAN = {'plan': [{'skill': 'pick', 'object': 'red_cube'},
                 {'skill': 'place', 'object': 'red_cube', 'zone': 'zone_b'}, {'skill': 'home'}]}


ADVANCED_PLAN = {'plan': [
    {'skill': 'pick', 'object': 'blue_cube'},
    {'skill': 'place', 'object': 'blue_cube', 'zone': 'zone_a'},
    {'skill': 'home'},
    {'skill': 'pick', 'object': 'red_cube'},
    {'skill': 'place', 'object': 'red_cube', 'zone': 'zone_b'},
    {'skill': 'home'},
    {'skill': 'pick', 'object': 'yellow_cube'},
    {'skill': 'place', 'object': 'yellow_cube', 'zone': 'zone_c'},
    {'skill': 'home'},
]}


class ValidatorTests(unittest.TestCase):
    def test_valid_plan(self):
        self.assertEqual(validate_plan(json.dumps(PLAN)), PLAN['plan'])

    def test_reject_all_invalid_before_execution(self):
        invalid = [None, [], {}, {'plan': []}, {'plan': PLAN['plan'] + [{'skill': 'home'}]},
                   {'plan': PLAN['plan'], 'joint_trajectory': []}, {'error': 'ambiguous'},
                   '```json\n' + json.dumps(PLAN) + '\n```', '{"plan":[],"plan":[]}',
                   '{bad json', {'plan': [True, None, 3]}]
        for index, key, value in [(0, 'skill', 'exec'),
                                   (0, 'object', []), (1, 'zone', 'zone_d'),
                                   (1, 'object', 'blue_cube'), (2, 'joints', [0.0]*6)]:
            candidate = copy.deepcopy(PLAN)
            candidate['plan'][index][key] = value
            invalid.append(candidate)
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(InvalidPlan):
                validate_plan(candidate)

    def test_personal_assignment(self):
        self.assertEqual(student_assignment('23020734'),
                         {'zone_a': 'blue_cube', 'zone_b': 'red_cube', 'zone_c': 'yellow_cube'})
        self.assertEqual(student_assignment('23020123')['zone_a'], 'blue_cube')
        student = load_student(ROOT / 'config/student_config.yaml')
        self.assertEqual(student['student_name'], 'Ngo Thien Dac')

    def test_advanced_plan_validates_three_transfers(self):
        self.assertEqual(validate_plan(ADVANCED_PLAN), ADVANCED_PLAN['plan'])

    def test_advanced_plan_rejects_duplicate_object(self):
        candidate = copy.deepcopy(ADVANCED_PLAN)
        candidate['plan'][3]['object'] = 'blue_cube'
        candidate['plan'][4]['object'] = 'blue_cube'
        with self.assertRaises(InvalidPlan):
            validate_plan(candidate)

    def test_wrong_student_zone_reports_invalid_object(self):
        wrong = {'plan': [
            {'skill': 'pick', 'object': 'red_cube'},
            {'skill': 'place', 'object': 'red_cube', 'zone': 'zone_a'},
            {'skill': 'home'},
        ]}
        with self.assertRaisesRegex(InvalidPlan, 'INVALID_OBJECT'):
            validate_plan(wrong)

    def test_world_matches_collision_config(self):
        scene = read_yaml(ROOT / 'config/scene.yaml')
        world = ET.fromstring(world_sdf(scene)).find('world')
        for name, data in scene['objects'].items():
            model = world.find(f"model[@name='{name}']")
            xyz = list(map(float, model.findtext('pose').split()[:3]))
            self.assertEqual(xyz, data['position'])
            self.assertIsNotNone(model.find('link/collision'))
        self.assertEqual(len(world.findall("model[@name='work_table']")), 1)
        self.assertIsNotNone(world.find("model[@name='orange_cube']"))
        self.assertIsNotNone(world.find("model[@name='temporary_zone']"))
        self.assertIsNotNone(world.find("model[@name='temporary_zone2']"))
        self.assertIsNotNone(world.find("model[@name='common_zone']"))

    def test_green_cube_is_a_valid_explicit_object(self):
        plan = {'plan': [{'skill': 'pick', 'object': 'green_cube'},
                         {'skill': 'place', 'object': 'green_cube', 'zone': 'zone_a'},
                         {'skill': 'home'}]}
        self.assertEqual(validate_plan(plan), plan['plan'])

    def test_random_start_has_green_and_one_wrong_assigned_cube(self):
        scene = read_yaml(ROOT / 'config/scene.yaml')
        base = {name: data['position'] for name, data in scene['objects'].items()}
        assignment = load_student(ROOT / 'config/student_config.yaml')['personal_assignment']
        correct = {obj: zone for zone, obj in assignment.items()}
        for seed in range(100):
            positions, green_zone, misplaced, wrong_zone = randomize_start_positions(
                base, scene['zones'], assignment, random.Random(seed))
            self.assertIn(green_zone, scene['zones'])
            self.assertIn(misplaced, correct)
            self.assertIn(wrong_zone, scene['zones'])
            self.assertNotEqual(wrong_zone, green_zone)
            self.assertNotEqual(wrong_zone, correct[misplaced])
            self.assertEqual(positions['green_cube'], scene['zones'][green_zone])
            self.assertEqual(positions[misplaced], scene['zones'][wrong_zone])


class TemporaryZoneTests(unittest.TestCase):
    def test_common_zone_is_used_when_two_preferred_pads_are_full(self):
        temporary_zones = {
            'temporary_zone': [0.32, 0.24, 0.1175],
            'temporary_zone2': [0.22, 0.24, 0.1175],
            'common_zone': [0.40, 0.0, 0.1175],
        }
        positions = {
            'orange_cube': list(temporary_zones['temporary_zone']),
            'green_cube': list(temporary_zones['temporary_zone2']),
            'red_cube': [0.22, -0.12, 0.1175],
        }
        self.assertEqual(
            choose_temporary_zone('red_cube', temporary_zones, positions, 0.035,
                                  exclude='red_cube'),
            'common_zone')
        # A green cube uses the first free pad too; no color-to-pad rule remains.
        positions.pop('orange_cube')
        positions.pop('green_cube')
        self.assertEqual(
            choose_temporary_zone('green_cube', temporary_zones, positions, 0.035),
            'temporary_zone')


class CameraTests(unittest.TestCase):
    def test_wrist_camera_is_attached_to_grasp_link(self):
        source = '''<robot name="test"><link name="tool0"/><ros2_control name="test" type="system"/></robot>'''
        root = ET.fromstring(add_parallel_gripper(source))
        camera = root.find("link[@name='wrist_camera_link']")
        bracket = root.find("link[@name='wrist_camera_bracket']")
        bracket_mount = root.find("joint[@name='wrist_camera_bracket_mount']")
        mount = root.find("joint[@name='wrist_camera_mount']")
        sensor = root.find("gazebo[@reference='wrist_camera_link']/sensor[@name='wrist_camera']")
        self.assertIsNotNone(camera)
        self.assertIsNotNone(bracket)
        self.assertEqual(bracket_mount.find('parent').attrib['link'], 'grasp_link')
        self.assertEqual(bracket_mount.find('origin').attrib['xyz'], '0.0205 0 -0.015')
        self.assertEqual(mount.find('parent').attrib['link'], 'grasp_link')
        self.assertEqual(mount.find('child').attrib['link'], 'wrist_camera_link')
        self.assertEqual(mount.find('origin').attrib['xyz'], '0.0295 0 -0.015')
        self.assertEqual(mount.find('origin').attrib['rpy'], '0 -1.5708 0')
        self.assertIsNone(camera.find('collision'))
        self.assertIsNone(bracket.find('collision'))
        self.assertEqual(sensor.attrib['type'], 'camera')
        self.assertEqual(sensor.findtext('topic'), '/wrist_camera/image_raw')
        self.assertEqual(sensor.find('camera/optical_frame_id').text, 'wrist_camera_optical_frame')

    def test_world_enables_gazebo_sensor_system(self):
        scene = read_yaml(ROOT / 'config/scene.yaml')
        world = ET.fromstring(world_sdf(scene)).find('world')
        sensors = world.find("plugin[@name='ignition::gazebo::systems::Sensors']")
        self.assertIsNotNone(sensors)
        self.assertEqual(sensors.findtext('render_engine'), 'ogre2')


class FakeSkills:
    def __init__(self, fail=None, preflight='SUCCESS'):
        self.calls, self.fail, self.preflight_status = [], fail, preflight
        self.plus_active = False
        self.plus_zone = None

    def clear_plus_zone(self):
        self.calls.append('clear_plus')
        self.plus_active = False
        self.plus_zone = None
        return 'SUCCESS'

    def preflight(self, obj, zone):
        return self.preflight_status

    def pick(self, obj):
        self.calls.append('pick')
        return 'PLANNING_FAILED' if self.fail == 'pick' else 'SUCCESS'

    def place(self, obj, zone):
        self.calls.append('place')
        return 'FAILED' if self.fail == 'place' else 'SUCCESS'

    def home(self):
        self.calls.append('home')
        return 'FAILED' if self.fail == 'home' else 'SUCCESS'


class ExecutorTests(unittest.TestCase):
    def test_success_requires_all_three(self):
        skills = FakeSkills()
        logs = []
        self.assertTrue(SkillExecutor(skills).execute(PLAN['plan'], logs.append))
        self.assertEqual(skills.calls, ['pick', 'place', 'home'])
        self.assertEqual(logs[-1], 'TASK SUCCESS')

    def test_stop_on_failure_and_latch(self):
        for fail, expected in [('pick', ['pick']), ('place', ['pick', 'place']),
                               ('home', ['pick', 'place', 'home'])]:
            skills = FakeSkills(fail)
            runner = SkillExecutor(skills)
            logs = []
            self.assertFalse(runner.execute(PLAN['plan'], logs.append))
            self.assertFalse(runner.execute(PLAN['plan'], logs.append))
            self.assertEqual(skills.calls, expected)
            self.assertNotIn('TASK SUCCESS', logs)

    def test_occupied_zone_stops_before_pick(self):
        skills = FakeSkills(preflight='ZONE_OCCUPIED')
        self.assertFalse(SkillExecutor(skills).execute(PLAN['plan'], lambda _: None))
        self.assertEqual(skills.calls, [])

    def test_advanced_executor_runs_each_transfer_in_order(self):
        skills = FakeSkills()
        logs = []
        self.assertTrue(SkillExecutor(skills).execute(ADVANCED_PLAN['plan'], logs.append))
        self.assertEqual(skills.calls, ['pick', 'place', 'home'] * 3)

    def test_plus_executor_clears_occupied_destination_before_transfer(self):
        skills = FakeSkills()
        skills.plus_active = True
        skills.plus_zone = 'zone_b'
        logs = []
        self.assertTrue(SkillExecutor(skills).execute(ADVANCED_PLAN['plan'], logs.append))
        self.assertEqual(skills.calls, ['pick', 'place', 'home', 'clear_plus',
                                        'pick', 'place', 'home',
                                        'pick', 'place', 'home'])
        self.assertTrue(any('PLUS: orange_cube' in line for line in logs))

    def test_invalid_last_step_never_moves(self):
        skills = FakeSkills()
        with self.assertRaises(InvalidPlan):
            SkillExecutor(skills).execute(PLAN['plan'][:2] + [{'skill': 'shell'}])
        self.assertEqual(skills.calls, [])


class PlannerTests(unittest.TestCase):
    def test_missing_model_explicit_error(self):
        with patch.dict(os.environ, {'NINE_ROUTER_MODEL': ''}):
            with self.assertRaises(PlannerError):
                LLMPlanner('test', {}).plan('Đưa vật màu đỏ sang vùng B.')

    def test_http_contract_with_local_mock_not_a_real_llm(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, body, self.headers.get('Authorization')))
                data = json.dumps({'choices': [{'finish_reason': 'stop',
                    'message': {'content': json.dumps(PLAN)}}]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with patch.dict(os.environ, {
                'NINE_ROUTER_BASE_URL': f'http://127.0.0.1:{server.server_port}/v1',
                'NINE_ROUTER_MODEL': 'test-model', 'NINE_ROUTER_API_KEY': 'test-only-key',
            }):
                planner = LLMPlanner('prompt', {'student_id': '23020734'})
                for command in ['Đưa vật màu đỏ sang vùng B.', 'Put the red cube in zone B.']:
                    self.assertEqual(planner.plan(command), PLAN['plan'])
                    self.assertEqual(requests[-1][1]['messages'][1]['content'], command)
                self.assertEqual(requests[0][0], '/v1/chat/completions')
                self.assertEqual(requests[0][2], 'Bearer test-only-key')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
