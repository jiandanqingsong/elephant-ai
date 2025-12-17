import time
import sys
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
from unitree_sdk2py.go2.sport.sport_client import (
    SportClient,
    PathPoint,
    SPORT_PATH_POINT_SIZE,
)
import math
from dataclasses import dataclass

# --------------- 在下面添加你的动作---------------
def act(sport_client):
    """
    在这里编写你的动作编排代码。
    你可以调用 sport_client 提供的各种方法来控制机器人。
    """
    print("开始执行动作编排...")
    print("WARNING: 请确保机器狗周围没有障碍物。")
    #sport_client.Stretch()  # 示例动作：伸展
    #time.sleep(2)


if __name__ == "__main__":

    ChannelFactoryInitialize(0, 'eth0')
    sport_client = SportClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()

    act(sport_client)
# -------------------------------------------------