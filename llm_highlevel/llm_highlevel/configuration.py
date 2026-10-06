from pathlib import Path
import random
import yaml

TARGET_OBJECTS = frozenset(('red_cube', 'yellow_cube', 'blue_cube'))
# Green is a fifth scene object and can be an obstacle or an explicit target.
# The student-ID assignment remains restricted to TARGET_OBJECTS.
OBJECTS = TARGET_OBJECTS | frozenset(('green_cube',))
ZONES = frozenset(('zone_a', 'zone_b', 'zone_c'))


def randomize_start_positions(base_positions, zones, assignment, rng=None):
    """Create a collision-free advanced start state.

    The green cube is placed in one random target zone. A second cube from
    the student-assigned set is then placed in one of its *wrong* zones. The
    wrong zone is kept different from the green zone so the two random
    occupants never start on top of each other. Returning this as a pure
    helper keeps the scene policy testable without starting ROS/Gazebo.
    """
    rng = rng or random
    positions = {name: list(xyz) for name, xyz in base_positions.items()}
    zone_names = sorted(zones)
    if not zone_names:
        return positions, None, None, None

    green_zone = None
    if 'green_cube' in positions:
        green_zone = rng.choice(zone_names)
        positions['green_cube'] = list(zones[green_zone])

    object_to_correct_zone = {
        obj: zone for zone, obj in assignment.items()
        if obj in positions
    }
    candidates = [
        (obj, zone)
        for obj in sorted(TARGET_OBJECTS)
        for zone in zone_names
        if zone != object_to_correct_zone.get(obj)
        and zone != green_zone
    ]
    if not candidates:
        return positions, green_zone, None, None

    misplaced_object, misplaced_zone = rng.choice(candidates)
    positions[misplaced_object] = list(zones[misplaced_zone])
    return positions, green_zone, misplaced_object, misplaced_zone


def choose_temporary_zone(obj, temporary_zones, positions, size, exclude=None):
    """Return the first free holding pad, including common_zone fallback.

    All objects share the same pad order. No color is tied to a specific
    temporary zone, so a full pad can be bypassed without special cases.
    """
    ordered = [name for name in ('temporary_zone', 'temporary_zone2', 'common_zone')
               if name in temporary_zones]
    for name in ordered:
        xyz = temporary_zones.get(name)
        if xyz is None:
            continue
        occupied = any(
            other != exclude and
            ((pos[0] - xyz[0]) ** 2 + (pos[1] - xyz[1]) ** 2 +
             (pos[2] - xyz[2]) ** 2) ** 0.5 < float(size) * 1.5
            for other, pos in positions.items())
        if not occupied:
            return name
    return None


def share_path():
    from ament_index_python.packages import get_package_share_directory
    return Path(get_package_share_directory('llm_highlevel'))


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
