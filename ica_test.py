import math
import numpy as np
from matplotlib import pyplot as plt
from sklearn.decomposition import FastICA, PCA
from scipy import signal
from copy import deepcopy
import pandas as pd


path = 'S1_train_data.xlsx'
s1 = pd.read_excel(path, header=None, sheet_name='char01(B)')
s1 = s1.values  # (3125, 20)
X = s1

t = np.linspace(0,len(X[:,0]), len(X[:,0])) / 250

for i, sig in enumerate(X.T, 1): 
    plt.figure(1)
    plt.subplot(20, 1, i)
    plt.plot(t, sig)


for i, sig in enumerate(X.T, 1): 
    plt.figure(1)
    plt.subplot(20, 1, i)
    plt.plot(t, sig)
plt.show()