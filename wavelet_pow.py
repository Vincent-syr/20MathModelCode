import math
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
from copy import deepcopy
import pandas as pd
import pywt







def wavelet_pow(data):

    # 需要分析的四个频段
    iter_freqs = [
        {'name': 'Delta', 'fmin': 0, 'fmax': 4},
        {'name': 'Theta', 'fmin': 4, 'fmax': 8},
        {'name': 'Alpha', 'fmin': 8, 'fmax': 13},
        {'name': 'Beta', 'fmin': 13, 'fmax': 25},
    ]
    maxlevel = 6
    fs = 250
    wavelet='db4'

    
    # 小波包分解
    wp = pywt.WaveletPacket(data=data, wavelet=wavelet, mode='symmetric', maxlevel=maxlevel)
    # 频谱由低到高的对应关系，这里需要注意小波变换的频带排列默认并不是顺序排列，所以这里需要使用’freq‘排序。
    freqTree = [node.path for node in wp.get_level(maxlevel, 'freq')]
    # 计算maxlevel最小频段的带宽
    freqBand = fs / (2 ** maxlevel)
    # 定义能量数组
    energy = []
    # 循环遍历计算四个频段对应的能量
    for iter in range(len(iter_freqs)):
        iterEnergy = 0.0
        for i in range(len(freqTree)):
            # 第i个频段的最小频率
            bandMin = i * freqBand
            # 第i个频段的最大频率
            bandMax = bandMin + freqBand
            # 判断第i个频段是否在要分析的范围内
            if (iter_freqs[iter]['fmin'] <= bandMin and iter_freqs[iter]['fmax'] >= bandMax):
                # 计算对应频段的累加和
                iterEnergy += pow(np.linalg.norm(wp[freqTree[i]].data, ord=None), 2)
        # 保存四个频段对应的能量和
        energy.append(iterEnergy)
    return energy