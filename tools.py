import time
import base64
import json
import math
from PIL import Image
import api
from react_agent.tools import BaseTool, register_tool
from pymycobot.mycobot import MyCobot
from pymycobot.genre import Angle
import numpy as np
from pymycobot import PI_PORT, PI_BAUD  # 当使用树莓派版本的mycobot时，可以引用这两个变量进行MyCobot初始化
import init
import cv2
import eyeonhand

mc = MyCobot('/dev/ttyUSB0', 1000000)

init.BotInit(mc)
#init.GetImage()

def adjust_gamma(image, gamma=1.0):
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

def get_object_angle(image, box):
    x1, y1, x2, y2 = box
    h, w = image.shape[:2]
    # Clamp coordinates
    x1 = max(0, min(int(x1), w))
    y1 = max(0, min(int(y1), h))
    x2 = max(0, min(int(x2), w))
    y2 = max(0, min(int(y2), h))
    
    roi = image[y1:y2, x1:x2]
    if roi.size == 0:
        return 0
        
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # Use Otsu's thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0
        
    # Find largest contour
    c = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(c)
    angle = rect[-1]
    
    width, height = rect[1]
    if width < height:
        angle += 90
        
    # Normalize angle to [-90, 90]
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180
        
    return angle

@register_tool('move_to')
class MoveTo(BaseTool):
    description = 'This function arranges multiple objects into a specific pattern within a designated area after calling function grab_object. You should generate the target_coord parameter dynamically using Python code, and ensure the arrangement follows the given constraints.'
    parameters = [
        {
            'name': 'target_coord',
            'type': 'list',
            'example':'[int,int] ',
            'description':'The target coordinate of the object.The number of it should be the same as object_number. x coordinate should range from -70 to 140, y coordinate should range from 150 to 280. When using this function, you have to generate Python code to get the correct coordinate and I will execute the code for you.两点之间的距离不小于50',
            'get_from_code':True,
            'required':True
        },
        {
            'name': 'target_height',
            'type': 'int',
            'example': '110',
            'description': 'Defines the height at which the object is released. Typically must set all objects to 110. Only if the instruction specifies that objects should be stacked, the height must starts at 110 for the first object and increases by 20 for each subsequent object (e.g., 110 for the first one, 130 for the second, and so on).',
            'first_height':'must be 110',
            'get_from_code': False,
            'required': True
        }
    ]

    def call(self, target_coord, target_height,**kwargs):
        width, height = Image.open("captured_image.jpg").size

        # 将物体移动到目标位置
        target_robot_coord = target_coord
        print("*************")
        print(target_robot_coord)

        time.sleep(3)

        mc.send_coords([target_robot_coord[0], target_robot_coord[1], 180, -175, 0, -45], 40)
        time.sleep(3)

        mc.send_coords([target_robot_coord[0], target_robot_coord[1], target_height, -175, 0, -45], 40)
        time.sleep(3)
        init.open_gripper()
        time.sleep(1)

        mc.send_coords([target_robot_coord[0], target_robot_coord[1], 200, -175, 0, -45], 40)
        time.sleep(2)
        mc.send_angles([0, 0, 0, 0, 0, -45], 40)
        time.sleep(1)

        print("Objects arranged successfully")
        return "Objects arranged successfully."



'''
@register_tool('select_object')
class SelectObject(BaseTool):
    description = 'This function selects specified objects detected objects and moves them according to a predefined rule or strategy.'
    parameters = [
        {
            'name': 'object_name',
            'type': 'string',
            'description': 'The name of the object to be selected. This parameter specifies the target object that the function should identify and select for further processing. When using this parameter in this function select_object, the complete string shoule be "所有" + object name.',
            'required': True
        }
    ]

    def call(self, object_name, **kwargs):
        width, height = Image.open("image.jpg").size


        # 获取识别出的所有物体的坐标
        positions = api.QwenVLRequest(object_name, "image.jpg").get("coordinates", [])
        print(positions)
        if not positions:
            print("No objects detected.")
            return

        # 遍历所有识别出的物体
        for position in positions:
            # 计算每个物体的中心点坐标
            center_x = (position['x1'] + position['x2']) / 2
            center_y = (position['y1'] + position['y2']) / 2
            target_coord = (center_x / 1000 * width, center_y / 1000 * height)

            # 转换为机械臂坐标
            robot_coord = eyeonhand.pixel_to_arm(target_coord, eyeonhand.affine_matrix,eyeonhand.translation_vector)
            print("像素坐标 {} 对应的机械臂坐标为: {}".format(target_coord, robot_coord))

            mc.send_coords([robot_coord[0], robot_coord[1], 110 , -178.24, 1.68, -134.33], 20)
            time.sleep(3)  # 等待移动完成
            init.pump_on()
            time.sleep(1)
            mc.send_coords([robot_coord[0], robot_coord[1], 200 , -178.24, 1.68, -134.33], 20)
            time.sleep(3)
            mc.send_coords([robot_coord[0], 0 - robot_coord[1], 200, -178.24, 1.68, -134.33], 20)
            time.sleep(3)
            mc.send_coords([robot_coord[0] , 0-robot_coord[1], 120, -178.24, 1.68, -134.33], 20)
            time.sleep(3)  # 等待移动完成
            init.pump_off()
            mc.send_coords([robot_coord[0], 0 - robot_coord[1], 200, -178.24, 1.68, -134.33], 20)
            time.sleep(3)
            mc.send_coords([robot_coord[0], robot_coord[1], 200, -178.24, 1.68, -134.33], 20)
            time.sleep(3)

        return "Objects moved successfully"

'''
'''
@register_tool('move_to')
class MoveObject(BaseTool):
    description = 'This function specifies a special location for the object to be placed. '
    parameters = [
        #{
         #   'name': 'object_name',
         #   'type': 'string',
         #   'description': 'The name of the object to be detected and moved. ',
          #  'required': True
       # },
        {
            'name': 'target_coord',
            'type': 'list',
            'example':'[int,int]',
            'description': 'The coordinate where the object should be placed.The x coordinate should range from -140 to 100, y coordinate should range from 150 to 280. ',
            'required': True
        }
    ]

    def call(self, target_coord,**kwargs):

        print(target_coord)

        # 计算中心点坐标
        #center_x_object = (position_object['coordinates'][0]['x1'] + position_object['coordinates'][0]['x2']) / 2
        #center_y_object = (position_object['coordinates'][0]['y1'] + position_object['coordinates'][0]['y2']) / 2
        #center_x_target = (position_target['coordinates'][0]['x1'] + position_target['coordinates'][0]['x2']) / 2
        #center_y_target = (position_target['coordinates'][0]['y1'] + position_target['coordinates'][0]['y2']) / 2
        #target_coord_object=(center_x_object/1000*width,center_y_object/1000*height)
        #target_coord_target = (center_x_target / 1000 * width, center_y_target / 1000 * height)
       # robot_coord_object = eyeonhand.pixel_to_robot(target_coord_object[0], target_coord_object[1], eyeonhand.transform_matrix)
        #robot_coord_target = eyeonhand.pixel_to_arm(target_coord_target, eyeonhand.affine_matrix, eyeonhand.translation_vector)
       # print("像素坐标 {} 对应的机械臂坐标为: {}".format(target_coord_object, robot_coord_object))
        #print("像素坐标 {} 对应的机械臂坐标为: {}".format(target_coord_target, robot_coord_target))

       # mc.send_coords([robot_coord_object[0], robot_coord_object[1], 100, -178.24, 1.68, -134.33], 20)
        #time.sleep(5)
        mc.send_coords([target_coord[0], target_coord[1], 200, -178.24, 1.68, -134.33], 20)
        time.sleep(3)
        init.gripper_on()
        return "move success"
'''
@register_tool('grab_object')
class GrabObject(BaseTool):
    description = 'This function detects the position of a specified object and performs a grabbing action to retrieve the object. '
    parameters = [
        {
            'name': 'object_name',
            'type': 'string',
            'description': 'The name of the object to be detected and grabbed. ',
            'required': True
        }
    ]

    def call(self, object_name, **kwargs):
        init.BotInit(mc)

        init.GetImage()

        width, height = Image.open('captured_image.jpg').size
        positions=api.QwenVLRequest("一个"+object_name,"captured_image.jpg").get("coordinates", [])
        print(positions)

        with open("config.json", "r") as config_file:
            config_data = json.load(config_file)

        x_offset = config_data.get("x", 0)
        y_offset = config_data.get("y", 0)
        z_offset = config_data.get("z", 0)
        tool_x = config_data.get("tool_x", 0)
        tool_y = config_data.get("tool_y", 0)

        # 只处理positions中的第一个坐标
        if positions:
            position = positions[0]
            # 计算中心点坐标
            center_x = (position['x1'] + position['x2']) / 2
            center_y = (position['y1'] + position['y2']) / 2
            target_coord = (center_x / 1000 * width, center_y / 1000 * height)
            robot_coord = eyeonhand.pixel_to_arm(target_coord)
            print("像素坐标 {} 对应的机械臂坐标为: {}".format(target_coord, robot_coord))
            
            # Apply global offsets
            robot_coord[0]=robot_coord[0]+x_offset
            robot_coord[1]=robot_coord[1]+y_offset
            if robot_coord[0] >210:
                robot_coord[0]=robot_coord[0]-5
            z = 120 + z_offset

            # Calculate angle
            img = cv2.imread('captured_image.jpg')
            x1 = position['x1'] / 1000 * width
            y1 = position['y1'] / 1000 * height
            x2 = position['x2'] / 1000 * width
            y2 = position['y2'] / 1000 * height
            angle = get_object_angle(img, (x1, y1, x2, y2))
            print(f"Object Angle: {angle}")
            
            # Map to robot frame
            # Fixed value was -45 for horizontal objects (angle=0).
            # Image rotation is inverted relative to robot rotation.
            rz = -angle - 45
            print(f"Calculated rz: {rz}")

            # Compensate for tool offset due to rotation
            # Original calibration assumes rz = -45
            # New position = Calibrated - (R(rz) - R(-45)) * ToolOffset
            if tool_x != 0 or tool_y != 0:
                def rotate_point(x, y, angle_deg):
                    rad = math.radians(angle_deg)
                    rx = x * math.cos(rad) - y * math.sin(rad)
                    ry = x * math.sin(rad) + y * math.cos(rad)
                    return rx, ry

                dx_base, dy_base = rotate_point(tool_x, tool_y, -45)
                dx_new, dy_new = rotate_point(tool_x, tool_y, rz)
                
                robot_coord[0] -= (dx_new - dx_base)
                robot_coord[1] -= (dy_new - dy_base)
                print(f"Applied tool offset compensation. New coord: {robot_coord}")

            init.open_gripper()
            mc.send_coords([robot_coord[0], robot_coord[1], 200, -173, 0, rz], 40)
            time.sleep(3)
            mc.send_coords([robot_coord[0], robot_coord[1], z, -173, 0, rz], 40)
            time.sleep(4)
            init.close_gripper()

            mc.send_coords([robot_coord[0], robot_coord[1], 200, -173, 0, rz], 40)
            time.sleep(3)
            mc.send_angles([0, 0, 0, 0, 0, -45], 40)
        else:
            print("没有找到任何位置数据")

        return robot_coord

@register_tool('show_object')
class ShowObject(BaseTool):
    description = 'This function shows the object to user after grabbing it, etc. '
    parameters = [
        {
            'name': 'object_name',
            'type': 'string',
            'description': 'show object name ',
            'required': True
        }
    ]


    def call(self,object_name, **kwargs):

        mc.send_angles([0, 0, 0, 0, 0, -45], 40)
        time.sleep(3)
        mc.send_angles([0, 0, 0, -90, 0, -45], 40)
        time.sleep(3)
        return "success"
'''
@register_tool('pump_on')
class Init(BaseTool):
    description = 'This functions start the pump. Pump is used to grab the objects '
    parameters = [
        {
            'name': 'duration',
            'type': 'float',
            'description': 'The amount of time to wait, in seconds.',
            'required': True
        }
    ]

    def call(self, duration, **kwargs):
        mc.send_angles([0, 0, 0, 0, 0, 0], 40)
        time.sleep(3)
        return f"move to init"
'''


'''
@register_tool('camera')
class Camera(BaseTool):
    description = 'This function takes the photo of the scene which is used to analyze the positions of the objects. This function has to be called firstly to init the bot arm. It has also to be called before the grabbing action when the bot arm is asked to move more than one object.'
    parameters = [
        {
            'name': 'duration',
            'type': 'float',
            'required': True
        }
    ]

    def call(self, duration, **kwargs):
        mc.send_coords([-8, -130, 250, 177.06, -0.46, 138.57], 10)
        # mc.send_coords([-8, -130, 280, 177.06, -0.46, 138.57], 10)
        time.sleep(3)

        mc.send_angles([-65.39, 14.76, -65.83, -42.36, 2.72, 70.3], 10)
        # mc.send_angles([-64.86, -3.6, -19.33, -69.25, 2.98, 70], 10)
        time.sleep(3)

        cap = cv2.VideoCapture(0)  # 使用第一个摄像头设备
        while True:
            ret, frame = cap.read()
            time.sleep(2)

            if not ret:
                print("Failed to capture image")
                break

            gamma_corrected_frame = adjust_gamma(frame, gamma=2.1)

            image_path = "image.jpg"
            cv2.imwrite(image_path, frame)
            print(f"Image saved as {image_path}")
            break
        cap.release()
        cv2.destroyAllWindows()
        return f"move to init"

@register_tool('set_color')
class SetColor(BaseTool):
    description = 'This function can set led\'s color (must RGB triple)'
    parameters = [
        {
            'name': 'R',
            'type': 'int',
            'description': 'the red component of the color, range [0, 255]',
            'required': True
        },
        {
            'name': 'G',
            'type': 'int',
            'description': 'the green component of the color, range [0, 255]',
            'required': True
        },
        {
            'name': 'B',
            'type': 'int',
            'description': 'the blue component of the color, range [0, 255]',
            'required': True
        }
    ]

    def call(self, R, G, B, **kwargs):
        try:
            mc.set_color(R, G, B)
            print(R,G,B)
            time.sleep(3)
            return f"success set_color!"
        except Exception as e:
            return f"error: {e}"
'''

