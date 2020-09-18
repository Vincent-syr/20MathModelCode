from scipy.signal import butter, lfilter
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import freqz
from scipy import signal
import pandas as pd


def butter_filter(raw_data, lowcut=30, fs=250):
    """[summary]

    Args:
        raw_data ([type]): np.array, shape[N, 1]
        lowcut (int, optional): [description]. low cut frequency, don't need to revise,Defaults to 25.
        fs (int, optional): [description]. Defaults to 250hz. sample frequency, don't need to revise'

    Returns:
        [type]: [description]
    """
    # fs = 250
    sos = signal.butter(N=6, Wn=lowcut, btype='lowpass', fs=fs, output='sos')
    filtered = signal.sosfilt(sos, raw_data)
    return filtered


if __name__ == "__main__":
    path = 'S1_train_data.xlsx'
    s1 = pd.read_excel(path, header=None, sheet_name='char01(B)')
    s1 = s1.values  # (3125, 20)
    # raw_data = 
    for i in range(20):
        raw_data = s1[:,i]
        x = np.linspace(0,len(raw_data), len(raw_data)) / 250
        filtered = butter_filter(raw_data)
        start = 250
        stop = start + 200
        # stop = len(x)
        # plt.figure()
        plt.plot(x[start:stop], raw_data[start:stop], label='raw signal')
        plt.plot(x[start:stop], filtered[start:stop], label='low passfilterd signal')
        plt.title('Butterworth filter')
        plt.xlabel('time (s)')
        plt.ylabel('microvolts (uV)')
        plt.legend()
        plt.show()







