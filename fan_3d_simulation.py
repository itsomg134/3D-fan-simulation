"""
3D Interactive Fan Simulation with Realistic Physics
Features: Multiple fan types, speed control, oscillation, lighting effects
Controls: 
  - Mouse: Rotate view
  - Arrow keys: Adjust fan speed
  - Space: Toggle oscillation
  - 1-5: Change fan type
  - O: Toggle on/off
  - L: Cycle lighting modes
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, Button
import warnings
warnings.filterwarnings('ignore')


class Fan3D:
    """Main 3D Fan class with physics and rendering"""
    
    def __init__(self, fan_type='ceiling'):
        self.fan_type = fan_type
        self.angle = 0
        self.speed = 2.0
        self.max_speed = 10.0
        self.is_on = True
        self.oscillate = False
        self.oscillate_angle = 0
        self.oscillate_direction = 1
        self.oscillate_range = 60
        self.blade_count = 3
        self.lighting_mode = 'realistic'
        
        # Fan configuration based on type
        self.configure_fan()
        
        # Physics parameters
        self.acceleration = 0.1
        self.deceleration = 0.05
        self.target_speed = self.speed
        self.current_speed = 0
        
        # Visual parameters
        self.blade_color = [0.2, 0.3, 0.5, 0.9]
        self.motor_color = [0.3, 0.3, 0.3, 1.0]
        self.stand_color = [0.4, 0.4, 0.4, 1.0]
        
    def configure_fan(self):
        """Configure fan parameters based on type"""
        configs = {
            'ceiling': {
                'blade_count': 3,
                'blade_length': 1.5,
                'blade_width': 0.3,
                'motor_radius': 0.2,
                'has_stand': False,
                'tilt_angle': 0
            },
            'table': {
                'blade_count': 4,
                'blade_length': 0.8,
                'blade_width': 0.2,
                'motor_radius': 0.15,
                'has_stand': True,
                'tilt_angle': 15
            },
            'tower': {
                'blade_count': 20,
                'blade_length': 0.3,
                'blade_width': 0.1,
                'motor_radius': 0.1,
                'has_stand': True,
                'tilt_angle': 0
            },
            'industrial': {
                'blade_count': 5,
                'blade_length': 2.0,
                'blade_width': 0.4,
                'motor_radius': 0.3,
                'has_stand': True,
                'tilt_angle': 0
            },
            'desk': {
                'blade_count': 3,
                'blade_length': 0.5,
                'blade_width': 0.15,
                'motor_radius': 0.1,
                'has_stand': True,
                'tilt_angle': 20
            }
        }
        
        config = configs.get(self.fan_type, configs['ceiling'])
        self.blade_count = config['blade_count']
        self.blade_length = config['blade_length']
        self.blade_width = config['blade_width']
        self.motor_radius = config['motor_radius']
        self.has_stand = config['has_stand']
        self.tilt_angle = config['tilt_angle']
    
    def generate_blade(self, angle_offset):
        """Generate a single fan blade mesh"""
        blade_angle = self.angle + angle_offset
        
        # Blade profile points
        num_segments = 20
        blade_profile = []
        
        for i in range(num_segments + 1):
            t = i / num_segments
            
            # Curved blade shape
            r = self.motor_radius + t * self.blade_length
            twist = np.sin(t * np.pi) * 15 * np.pi / 180
            width = self.blade_width * (1 - t * 0.5) * np.sin(t * np.pi)
            
            # Top surface
            x1 = r * np.cos(blade_angle + twist) - width * np.sin(blade_angle + twist)
            y1 = r * np.sin(blade_angle + twist) + width * np.cos(blade_angle + twist)
            z1 = np.sin(t * np.pi) * 0.1
            
            # Bottom surface
            x2 = r * np.cos(blade_angle + twist) + width * np.sin(blade_angle + twist)
            y2 = r * np.sin(blade_angle + twist) - width * np.cos(blade_angle + twist)
            z2 = -np.sin(t * np.pi) * 0.05
            
            blade_profile.append(([x1, y1, z1], [x2, y2, z2]))
        
        # Create blade mesh
        vertices = []
        faces = []
        
        for i in range(num_segments):
            v1_top, v1_bot = blade_profile[i]
            v2_top, v2_bot = blade_profile[i + 1]
            
            idx = len(vertices)
            vertices.extend([v1_top, v2_top, v2_bot, v1_bot])
            
            # Top face
            faces.append([idx, idx + 1, idx + 2, idx + 3])
        
        return np.array(vertices), faces
    
    def generate_motor_housing(self):
        """Generate cylindrical motor housing"""
        vertices = []
        faces = []
        
        theta = np.linspace(0, 2 * np.pi, 32)
        height_segments = 5
        
        for i in range(height_segments + 1):
            z = -0.2 + i * 0.08
            r = self.motor_radius * (1 + 0.1 * np.sin(i * np.pi / height_segments))
            
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                vertices.append([x, y, z])
        
        # Generate faces
        n_theta = len(theta)
        for i in range(height_segments):
            for j in range(n_theta - 1):
                idx = i * n_theta + j
                faces.append([
                    idx, idx + 1, idx + n_theta + 1, idx + n_theta
                ])
        
        return np.array(vertices), faces
    
    def generate_stand(self):
        """Generate fan stand/pole"""
        vertices = []
        faces = []
        
        if not self.has_stand:
            return np.array(vertices), faces
        
        # Pole
        theta = np.linspace(0, 2 * np.pi, 16)
        pole_height = 2.5 if self.fan_type == 'tower' else 1.5
        pole_radius = 0.05
        
        for i, z in enumerate(np.linspace(-pole_height, -0.2, 20)):
            r = pole_radius * (1 + 0.2 * (1 - abs(z + pole_height/2) / (pole_height/2)))
            
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                vertices.append([x, y, z])
        
        # Base
        base_radius = 0.3
        for t in theta:
            x = base_radius * np.cos(t)
            y = base_radius * np.sin(t)
            vertices.append([x, y, -pole_height])
            vertices.append([x * 0.9, y * 0.9, -pole_height + 0.05])
        
        # Generate pole faces
        n_theta = len(theta)
        for i in range(19):
            for j in range(n_theta - 1):
                idx = i * n_theta + j
                faces.append([
                    idx, idx + 1, idx + n_theta + 1, idx + n_theta
                ])
        
        return np.array(vertices), faces
    
    def generate_safety_cage(self):
        """Generate protective wire cage around blades"""
        vertices = []
        faces = []
        
        # Front cage
        n_rings = 8
        n_spokes = 16
        theta = np.linspace(0, 2 * np.pi, n_spokes)
        
        cage_radius = self.blade_length + 0.2
        
        for i in range(n_rings):
            r = cage_radius * (i + 1) / n_rings
            z = 0.05
            
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                vertices.append([x, y, z])
        
        # Rear cage
        for i in range(n_rings):
            r = cage_radius * (i + 1) / n_rings
            z = -0.15
            
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                vertices.append([x, y, z])
        
        # Connect front and back
        for i in range(n_spokes - 1):
            for j in range(n_rings - 1):
                idx_front = j * n_spokes + i
                idx_back = (n_rings + j) * n_spokes + i
                
                faces.append([
                    idx_front, idx_front + 1, idx_back + 1, idx_back
                ])
        
        return np.array(vertices), faces
    
    def apply_lighting(self, vertices, faces, color):
        """Apply realistic lighting to mesh"""
        if len(vertices) == 0 or len(faces) == 0:
            return []
        
        face_colors = []
        light_dir = np.array([0.5, 0.5, 1.0])
        light_dir = light_dir / np.linalg.norm(light_dir)
        
        for face in faces:
            if len(face) < 3:
                continue
                
            # Calculate face normal
            v0 = vertices[face[0]]
            v1 = vertices[face[1]]
            v2 = vertices[face[2]]
            
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            
            if np.linalg.norm(normal) > 0:
                normal = normal / np.linalg.norm(normal)
            else:
                normal = np.array([0, 0, 1])
            
            # Lighting calculation
            if self.lighting_mode == 'realistic':
                diffuse = max(0, np.dot(normal, light_dir))
                ambient = 0.3
                specular = max(0, np.dot(normal, light_dir)) ** 3 * 0.5
                intensity = ambient + diffuse * 0.7 + specular
            elif self.lighting_mode == 'flat':
                intensity = 1.0
            else:  # dramatic
                diffuse = max(0, np.dot(normal, light_dir))
                intensity = 0.2 + diffuse * 0.8
            
            intensity = np.clip(intensity, 0, 1)
            
            face_color = [
                color[0] * intensity,
                color[1] * intensity,
                color[2] * intensity,
                color[3]
            ]
            face_colors.append(face_color)
        
        return face_colors
    
    def update_physics(self, dt=0.016):
        """Update fan physics simulation"""
        # Update rotation speed with acceleration/deceleration
        if self.is_on:
            if self.current_speed < self.target_speed:
                self.current_speed = min(
                    self.target_speed,
                    self.current_speed + self.acceleration
                )
            elif self.current_speed > self.target_speed:
                self.current_speed = max(
                    self.target_speed,
                    self.current_speed - self.deceleration
                )
        else:
            self.current_speed = max(0, self.current_speed - self.deceleration)
        
        # Update blade rotation
        self.angle += self.current_speed * dt * np.pi
        self.angle %= (2 * np.pi)
        
        # Update oscillation
        if self.oscillate:
            self.oscillate_angle += self.oscillate_direction * 0.5
            
            if abs(self.oscillate_angle) >= self.oscillate_range / 2:
                self.oscillate_direction *= -1
                self.oscillate_angle = np.clip(
                    self.oscillate_angle,
                    -self.oscillate_range / 2,
                    self.oscillate_range / 2
                )
    
    def render(self, ax):
        """Render complete fan model"""
        ax.clear()
        
        # Apply oscillation rotation
        if self.oscillate:
            osc_rad = self.oscillate_angle * np.pi / 180
            rotation_matrix = np.array([
                [np.cos(osc_rad), -np.sin(osc_rad), 0],
                [np.sin(osc_rad), np.cos(osc_rad), 0],
                [0, 0, 1]
            ])
        else:
            rotation_matrix = np.eye(3)
        
        # Apply tilt
        if self.tilt_angle != 0:
            tilt_rad = self.tilt_angle * np.pi / 180
            tilt_matrix = np.array([
                [1, 0, 0],
                [0, np.cos(tilt_rad), -np.sin(tilt_rad)],
                [0, np.sin(tilt_rad), np.cos(tilt_rad)]
            ])
            rotation_matrix = rotation_matrix @ tilt_matrix
        
        all_collections = []
        
        # Render blades
        for i in range(self.blade_count):
            angle_offset = i * 2 * np.pi / self.blade_count
            vertices, faces = self.generate_blade(angle_offset)
            
            if len(vertices) > 0:
                # Apply rotation
                vertices = vertices @ rotation_matrix.T
                
                face_vertices = [[vertices[idx] for idx in face] for face in faces]
                face_colors = self.apply_lighting(vertices, faces, self.blade_color)
                
                collection = Poly3DCollection(
                    face_vertices,
                    facecolors=face_colors,
                    edgecolors='none',
                    linewidths=0
                )
                ax.add_collection3d(collection)
                all_collections.append(collection)
        
        # Render motor housing
        vertices, faces = self.generate_motor_housing()
        if len(vertices) > 0:
            vertices = vertices @ rotation_matrix.T
            face_vertices = [[vertices[idx] for idx in face] for face in faces]
            face_colors = self.apply_lighting(vertices, faces, self.motor_color)
            
            collection = Poly3DCollection(
                face_vertices,
                facecolors=face_colors,
                edgecolors='k',
                linewidths=0.5,
                alpha=0.9
            )
            ax.add_collection3d(collection)
            all_collections.append(collection)
        
        # Render stand
        vertices, faces = self.generate_stand()
        if len(vertices) > 0:
            face_vertices = [[vertices[idx] for idx in face] for face in faces]
            face_colors = self.apply_lighting(vertices, faces, self.stand_color)
            
            collection = Poly3DCollection(
                face_vertices,
                facecolors=face_colors,
                edgecolors='k',
                linewidths=0.5
            )
            ax.add_collection3d(collection)
            all_collections.append(collection)
        
        # Render safety cage (optional, for table/desk fans)
        if self.fan_type in ['table', 'desk']:
            vertices, faces = self.generate_safety_cage()
            if len(vertices) > 0:
                vertices = vertices @ rotation_matrix.T
                face_vertices = [[vertices[idx] for idx in face] for face in faces]
                
                collection = Poly3DCollection(
                    face_vertices,
                    facecolors=(0.5, 0.5, 0.5, 0.3),
                    edgecolors=(0.3, 0.3, 0.3, 0.8),
                    linewidths=1.5
                )
                ax.add_collection3d(collection)
                all_collections.append(collection)
        
        # Set axis properties
        max_dim = max(self.blade_length * 1.5, 2.5 if self.has_stand else 1)
        ax.set_xlim([-max_dim, max_dim])
        ax.set_ylim([-max_dim, max_dim])
        ax.set_zlim([-max_dim if self.has_stand else -1, 1])
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(f'{self.fan_type.capitalize()} Fan - Speed: {self.current_speed:.1f} RPM', 
                     fontsize=12, fontweight='bold')
        
        # Set viewing angle
        ax.view_init(elev=20, azim=45)
        ax.set_box_aspect([1, 1, 1])
        
        return all_collections


class FanSimulator:
    """Main simulator class with UI and controls"""
    
    def __init__(self):
        self.fig = plt.figure(figsize=(14, 10))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.patch.set_facecolor('#1a1a1a')
        self.ax.set_facecolor('#2a2a2a')
        
        self.fan = Fan3D('ceiling')
        self.frame_count = 0
        
        # Setup UI
        self.setup_ui()
        self.setup_controls()
        
        # Animation
        self.anim = FuncAnimation(
            self.fig,
            self.update,
            frames=None,
            interval=16,
            blit=False,
            cache_frame_data=False
        )
    
    def setup_ui(self):
        """Setup user interface elements"""
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.25)
        
        # Info text
        info_text = (
            "Controls:\n"
            "↑↓: Speed | Space: Oscillate | O: On/Off\n"
            "1-5: Fan Type | L: Lighting | Mouse: Rotate View"
        )
        
        self.fig.text(
            0.5, 0.02, info_text,
            ha='center',
            fontsize=10,
            color='white',
            bbox=dict(boxstyle='round', facecolor='#333333', alpha=0.8)
        )
    
    def setup_controls(self):
        """Setup interactive controls"""
        
        def on_key(event):
            if event.key == 'up':
                self.fan.target_speed = min(
                    self.fan.max_speed,
                    self.fan.target_speed + 0.5
                )
            elif event.key == 'down':
                self.fan.target_speed = max(0, self.fan.target_speed - 0.5)
            elif event.key == ' ':
                self.fan.oscillate = not self.fan.oscillate
            elif event.key == 'o':
                self.fan.is_on = not self.fan.is_on
                if not self.fan.is_on:
                    self.fan.target_speed = 0
                else:
                    self.fan.target_speed = 2.0
            elif event.key == 'l':
                modes = ['realistic', 'flat', 'dramatic']
                idx = (modes.index(self.fan.lighting_mode) + 1) % len(modes)
                self.fan.lighting_mode = modes[idx]
            elif event.key in ['1', '2', '3', '4', '5']:
                types = ['ceiling', 'table', 'tower', 'industrial', 'desk']
                self.fan.fan_type = types[int(event.key) - 1]
                self.fan.configure_fan()
        
        self.fig.canvas.mpl_connect('key_press_event', on_key)
    
    def update(self, frame):
        """Animation update function"""
        self.fan.update_physics()
        collections = self.fan.render(self.ax)
        self.frame_count += 1
        
        return collections
    
    def run(self):
        """Start the simulation"""
        plt.show()


# Main execution
if __name__ == "__main__":
    print("Starting 3D Fan Simulator...")
    print("Loading graphics engine...")
    
    simulator = FanSimulator()
    
    print("\n" + "="*60)
    print("3D FAN SIMULATOR - READY")
    print("="*60)
    print("\nControls:")
    print("  ↑/↓ Arrow Keys  : Increase/Decrease Speed")
    print("  Space Bar       : Toggle Oscillation")
    print("  O               : Turn Fan On/Off")
    print("  L               : Cycle Lighting Modes")
    print("  1-5             : Switch Fan Types")
    print("                    1: Ceiling Fan")
    print("                    2: Table Fan")
    print("                    3: Tower Fan")
    print("                    4: Industrial Fan")
    print("                    5: Desk Fan")
    print("  Mouse Drag      : Rotate View")
    print("\nFeatures:")
    print("  ✓ Realistic blade physics with twist")
    print("  ✓ Smooth acceleration/deceleration")
    print("  ✓ Multiple fan types")
    print("  ✓ Dynamic lighting system")
    print("  ✓ Oscillation animation")
    print("  ✓ Safety cage rendering")
    print("="*60 + "\n")
    
    simulator.run()