import pyaudio
import numpy as np
import soundfile as sf
import api
import sys
import requests



def record_auto():

    command=api.AudioRecognize('Recording.flac')
    print(f"<USER>:{command}")
    return command

if __name__ == '__main__':
    record_auto(MIC_INDEX=4)
