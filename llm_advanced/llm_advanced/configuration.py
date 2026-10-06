from pathlib import Path
import yaml

TARGET_OBJECTS = frozenset(('red_cube', 'yellow_cube', 'blue_cube'))
# Green is a fifth scene object and can be an obstacle or an explicit target.
# The student-ID assignment remains restricted to TARGET_OBJECTS.
OBJECTS = TARGET_OBJECTS | frozenset(('green_cube',))
ZONES = frozenset(('zone_a', 'zone_b', 'zone_c'))



def share_path():
    from ament_index_python.packages import get_package_share_directory
    return Path(get_package_share_directory('llm_advanced'))


def read_yaml(path):
    with open(path, encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def student_assignment(student_id):
    sid = str(student_id)
    if not sid.isdigit() or len(sid) < 2:
        raise ValueError('student_id phải có ít nhất hai chữ số')
    permutations = [
        ('red_cube', 'yellow_cube', 'blue_cube'),
        ('red_cube', 'blue_cube', 'yellow_cube'),
        ('yellow_cube', 'red_cube', 'blue_cube'),
        ('yellow_cube', 'blue_cube', 'red_cube'),
        ('blue_cube', 'red_cube', 'yellow_cube'),
        ('blue_cube', 'yellow_cube', 'red_cube'),
    ]
    return dict(zip(('zone_a', 'zone_b', 'zone_c'), permutations[int(sid[-2:]) % 6]))


def load_student(path):
    student = read_yaml(path)
    mapping = student_assignment(student['student_id'])
    if student.get('personal_assignment', mapping) != mapping:
        raise ValueError('personal_assignment không khớp MSSV')
    student['personal_assignment'] = mapping
    return student
