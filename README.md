可供调用的方法在根目录的tools.py内实现

机械臂文档：
JetCobot AI协作机械臂：https://www.yahboom.com/study/JETCOBOT                       
密码：omea

config.json:
1.手眼标定：像素坐标写在points_pixel中，机械臂坐标写在points_arm中
2.x、y是偏移量数据，若出现普遍性的偏差可以同一调整
3.voice:true使用语音输入，false使用键盘打字输入。语音输入需要将音频存到Recording.flac中

运行：
python agent.py