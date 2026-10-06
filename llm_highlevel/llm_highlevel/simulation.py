# Build Gazebo geometry and robot description from the installed Humble UR model.
from xml.etree import ElementTree as ET


def world_sdf(scene):
    def box(name, xyz, size, color, collision=True):
        pose = ' '.join(map(str, xyz)) + ' 0 0 0'
        dimensions = ' '.join(map(str, size))
        rgba = ' '.join(map(str, color))
        geometry = f'<geometry><box><size>{dimensions}</size></box></geometry>'
        solid = f'<collision name="collision">{geometry}</collision>' if collision else ''
        return f'''<model name="{name}"><static>true</static><pose>{pose}</pose>
          <link name="link">{solid}<visual name="visual">{geometry}
          <material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material>
          </visual></link></model>'''

    models = [box('floor', [0, 0, -0.07], [3, 3, 0.02], [0.35, 0.38, 0.4, 1]),
              box('work_table', scene['table']['center'], scene['table']['size'], [0.5, 0.36, 0.22, 1])]
    for name, data in scene['objects'].items():
        models.append(box(name, data['position'], [scene['cube_size']]*3, data['color']))
    plus = scene.get('plus_object')
    if plus:
        # Keep the optional plus object on the table at its parking point.
        # RobotSkills moves it into the selected A/B/C zone when a/b/c is pressed.
        models.append(box(plus['name'], plus['parking_position'],
                          [scene['cube_size']]*3, [0.95, 0.35, 0.05, 1.0]))
    top = scene['table']['center'][2] + scene['table']['size'][2]/2
    if plus:
        for temp_name, temp_xyz, color in (
                ('temporary_zone', plus['temporary_zone'], [0.95, 0.45, 0.05, 1]),
                ('temporary_zone2', plus.get('temporary_zone2'), [0.65, 0.30, 0.85, 1]),
                ('common_zone', plus.get('common_zone'), [0.45, 0.45, 0.45, 1])):
            if temp_xyz is None:
                continue
            models.append(box(temp_name,
                              [temp_xyz[0], temp_xyz[1], top + 0.0005],
                              [0.075, 0.075, 0.001], color, collision=False))
    for index, (name, xyz) in enumerate(scene['zones'].items()):
        models.append(box(name, [xyz[0], xyz[1], top + 0.0005], [0.075, 0.075, 0.001],
                          [0.2, 0.65, 0.35, 1], collision=False))
        patterns = [('01110', '10001', '11111', '10001', '10001'),
                    ('11110', '10001', '11110', '10001', '11110'),
                    ('01111', '10000', '10000', '10000', '01111')]
        for row, pixels in enumerate(patterns[index]):
            for col, bit in enumerate(pixels):
                if bit == '1':
                    models.append(box(f'{name}_label_{row}_{col}',
                                      [xyz[0]+0.025+(4-row)*0.003, xyz[1]+(2-col)*0.003, top+0.002],
                                      [0.003, 0.003, 0.001], [1, 1, 1, 1], collision=False))
    return '''<?xml version="1.0"?><sdf version="1.7"><world name="%s">
      <physics name="physics" type="ignored"><max_step_size>0.002</max_step_size>
        <real_time_factor>1</real_time_factor></physics>
      <plugin filename="ignition-gazebo-physics-system" name="ignition::gazebo::systems::Physics"/>
      <!-- Gazebo Sim sensor system publishes the wrist camera image. -->
      <plugin filename="ignition-gazebo-sensors-system" name="ignition::gazebo::systems::Sensors">
        <render_engine>ogre2</render_engine>
      </plugin>
      <plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
      <plugin filename="ignition-gazebo-scene-broadcaster-system" name="ignition::gazebo::systems::SceneBroadcaster"/>
      <light type="directional" name="sun"><pose>0 0 5 0 0 0</pose><diffuse>0.9 0.9 0.9 1</diffuse>
        <specular>0.1 0.1 0.1 1</specular><direction>-0.5 0.1 -1</direction></light>
      <scene><ambient>0.6 0.6 0.6 1</ambient><background>0.2 0.23 0.28 1</background></scene>
      %s
    </world></sdf>''' % (scene['world_name'], '\n'.join(models))


def add_parallel_gripper(urdf):
    # Add a controllable two-finger parallel gripper to the UR3 tool frame.
    root = ET.fromstring(urdf)
    for child in list(root):
        if child.attrib.get('name') in ('ground_plane', 'ground_plane_joint'):
            root.remove(child)
    control = root.find('ros2_control')
    if control is None:
        raise ValueError('URDF không có ros2_control để thêm gripper')
    for name in ('gripper_left_joint', 'gripper_right_joint'):
        joint = ET.SubElement(control, 'joint', name=name)
        ET.SubElement(joint, 'command_interface', name='position')
        position_state = ET.SubElement(joint, 'state_interface', name='position')
        ET.SubElement(position_state, 'param', name='initial_value').text = '0.0'
        ET.SubElement(joint, 'state_interface', name='velocity')
    extra = ET.fromstring('''<robot>
      <!-- Elongated jaw carrier covers both finger travel endpoints. -->
      <link name="gripper_base"><inertial><origin xyz="0 0 0.015"/><mass value="0.08"/>
        <inertia ixx="0.0001" iyy="0.0001" izz="0.0001" ixy="0" ixz="0" iyz="0"/></inertial>
        <visual><origin xyz="0 0 0.015"/><geometry><box size="0.035 0.095 0.03"/></geometry>
          <material name="gripper_base_material"><color rgba="0.12 0.12 0.14 1"/></material></visual>
        <!-- No Gazebo collision on the carrier: the gripper is synchronized
             by the joint trajectory and grasp collision is managed by MoveIt. --></link>
      <joint name="gripper_mount" type="fixed"><parent link="tool0"/><child link="gripper_base"/><origin xyz="0 0 0"/></joint>
      <link name="gripper_left_finger"><inertial><origin xyz="0 0.07 0.02"/><mass value="0.025"/>
        <inertia ixx="0.00002" iyy="0.00002" izz="0.00002" ixy="0" ixz="0" iyz="0"/></inertial>
        <visual><origin xyz="0 0.07 0.02"/><geometry><box size="0.012 0.010 0.04"/></geometry>
          <material name="finger_material"><color rgba="0.2 0.22 0.25 1"/></material></visual>
        <collision><origin xyz="0 0.07 0.02"/><geometry><box size="0.012 0.010 0.04"/></geometry></collision></link>
      <joint name="gripper_left_joint" type="prismatic"><parent link="gripper_base"/><child link="gripper_left_finger"/>
        <origin xyz="0 -0.035 0.03"/><axis xyz="0 -1 0"/><limit lower="0.0" upper="0.012" effort="50" velocity="0.2"/>
        <dynamics damping="0.05" friction="0.0"/></joint>
      <gazebo reference="gripper_left_finger"><gravity>false</gravity><self_collide>false</self_collide></gazebo>
      <link name="gripper_right_finger"><inertial><origin xyz="0 0 0.02"/><mass value="0.025"/>
        <inertia ixx="0.00002" iyy="0.00002" izz="0.00002" ixy="0" ixz="0" iyz="0"/></inertial>
        <visual><origin xyz="0 0 0.02"/><geometry><box size="0.012 0.010 0.04"/></geometry>
          <material name="finger_material"><color rgba="0.2 0.22 0.25 1"/></material></visual>
        <collision><origin xyz="0 0 0.02"/><geometry><box size="0.012 0.010 0.04"/></geometry></collision></link>
      <gazebo reference="gripper_right_finger"><gravity>false</gravity><self_collide>false</self_collide></gazebo>
      <joint name="gripper_right_joint" type="prismatic"><parent link="gripper_base"/><child link="gripper_right_finger"/>
        <origin xyz="0 -0.035 0.03"/><axis xyz="0 1 0"/><limit lower="0.0" upper="0.012" effort="50" velocity="0.2"/>
        <dynamics damping="0.05" friction="0.0"/></joint>
      <link name="grasp_link"/><joint name="grasp_tip" type="fixed"><parent link="gripper_base"/><child link="grasp_link"/>
        <origin xyz="0 0 0.03"/></joint>
      <!-- RGB camera fixed flush to the side of the end-effector carrier.
           Its optical axis is parallel to the EF/jaw direction, not pointed
           down at the table. The housing and bracket are visual-only so they
           never block the gripper in MoveIt's collision model. -->
      <link name="wrist_camera_bracket"><inertial><origin xyz="0 0 0"/><mass value="0.005"/>
        <inertia ixx="0.000001" iyy="0.000001" izz="0.000001" ixy="0" ixz="0" iyz="0"/></inertial>
        <!-- 6 mm plate bridges the carrier side and the camera housing. -->
        <visual><origin xyz="0 0 0"/><geometry><box size="0.006 0.036 0.028"/></geometry>
          <material name="camera_bracket_material"><color rgba="0.62 0.64 0.68 1"/></material></visual>
      </link>
      <joint name="wrist_camera_bracket_mount" type="fixed"><parent link="grasp_link"/><child link="wrist_camera_bracket"/>
        <!-- Carrier x edge is +17.5 mm; the bracket starts exactly there. -->
        <origin xyz="0.0205 0 -0.015"/></joint>
      <link name="wrist_camera_link"><inertial><origin xyz="0 0 0"/><mass value="0.015"/>
        <inertia ixx="0.00001" iyy="0.00001" izz="0.00001" ixy="0" ixz="0" iyz="0"/></inertial>
        <!-- With the mount rotation, this box's local z thickness is the
             outward side direction. Its inner face touches the carrier. -->
        <visual><origin xyz="0 0 0"/><geometry><box size="0.024 0.03 0.024"/></geometry>
          <material name="camera_material"><color rgba="0.04 0.04 0.05 1"/></material></visual>
        <!-- Deliberately visual-only: the camera housing must never block the
             gripper or make an object pick fail in MoveIt. --></link>
      <joint name="wrist_camera_mount" type="fixed"><parent link="grasp_link"/><child link="wrist_camera_link"/>
        <!-- Carrier x edge is +17.5 mm and the camera half-thickness is
             12 mm, so x=29.5 mm makes the two faces exactly touch. The
             z=-15 mm offset centers both bodies at the same height. -->
        <origin xyz="0.0295 0 -0.015" rpy="0 -1.5708 0"/></joint>
      <link name="wrist_camera_optical_frame"/>
      <joint name="wrist_camera_optical_joint" type="fixed"><parent link="wrist_camera_link"/>
        <child link="wrist_camera_optical_frame"/><origin xyz="0 0 0" rpy="-1.5708 0 -1.5708"/></joint>
      <gazebo reference="wrist_camera_link">
        <sensor name="wrist_camera" type="camera">
          <always_on>true</always_on><update_rate>15</update_rate><visualize>true</visualize>
          <topic>/wrist_camera/image_raw</topic>
          <camera>
            <horizontal_fov>1.047</horizontal_fov>
            <image><width>640</width><height>480</height><format>R8G8B8</format></image>
            <clip><near>0.02</near><far>3.0</far></clip>
            <optical_frame_id>wrist_camera_optical_frame</optical_frame_id>
          </camera>
        </sensor>
      </gazebo>
    </robot>''')
    root.extend(list(extra))
    return ET.tostring(root, encoding='unicode')


def add_parallel_gripper_semantic(srdf):
    root = ET.fromstring(srdf)
    root.find("group[@name='ur_manipulator']/chain").set('tip_link', 'grasp_link')
    for link in ('gripper_base', 'gripper_left_finger', 'gripper_right_finger'):
        for other in ('tool0', 'flange', 'wrist_3_link', 'grasp_link'):
            ET.SubElement(root, 'disable_collisions', link1=link, link2=other, reason='Adjacent')
    for camera_link in ('wrist_camera_bracket', 'wrist_camera_link'):
        for other in ('tool0', 'flange', 'wrist_3_link', 'grasp_link',
                      'gripper_base', 'gripper_left_finger', 'gripper_right_finger'):
            ET.SubElement(root, 'disable_collisions', link1=camera_link,
                          link2=other, reason='Adjacent')
    ET.SubElement(root, 'disable_collisions', link1='gripper_base', link2='gripper_left_finger', reason='Adjacent')
    ET.SubElement(root, 'disable_collisions', link1='gripper_base', link2='gripper_right_finger', reason='Adjacent')
    # Keep the UR3 shoulder/base adjacent pair disabled explicitly. Some
    # Humble ur_moveit_config revisions omit this entry after xacro expansion.
    ET.SubElement(root, 'disable_collisions', link1='base_link_inertia',
                  link2='shoulder_link', reason='Adjacent')
    return ET.tostring(root, encoding='unicode')
