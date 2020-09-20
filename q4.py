import numpy as np
import pandas as pd
import os
from six.moves import cPickle as pickle
from scipy import signal
import matplotlib.pyplot as plt



from torch import nn
 
class SimpleNet(nn.Module):
    """
    定义了一个简单的三层全连接神经网络，每一层都是线性的
    """
    def __init__(self, in_dim, n_hidden_1, out_dim):
        super(simpleNet, self).__init__()
        self.layer = nn.Sequential(
            nn.Linear(in_dim, n_hidden_1),
            nn.ReLU(), 
            nn.Linear(n_hidden_1, out_dim), 
            nn.Sigmoid()
        )
        # self.layer1 = nn.Linear(in_dim, n_hidden_1)
        # self.layer2 = nn.Linear(n_hidden_1, out_dim)
 
    def forward(self, x):
        # x = self.layer1(x)
        # x = self.layer2(x)
        # out = self.layer3(x)
        out = self.layer(x)
        return out





def read():
    CHAR = ['清醒期（6）', '快速眼动期（5）', '睡眠I期（4）', '睡眠II期（3）', '深睡眠期（2）']
    feat_all = np.zeros((1,4))
    label_all = np.zeros((1))
    path='附件2-睡眠脑电数据.xlsx'
    for sheet_name in CHAR:
        s1 = pd.read_excel(path, header=None, sheet_name='清醒期（6）')
        feat = s1.values[1:,1:5].astype('float')
        label = s1.values[1:,0].astype('int')

        feat_all = np.concatenate((feat_all,feat), axis=0)
        label_all = np.concatenate((label_all,label), axis=0)

        # label_all.append(label)
    # print('ddddd')
    return feat_all, label_all
    # return np.array(feat_all), np.array(label_all)


