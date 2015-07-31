#!/usr/bin/env python

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.mlab as mlab
from scipy import signal

def load_data(path, filename, source):
    
    raw_data = []
    
    if source == 'muse':
        skiprows = 0
        with open(path + filename, 'rb') as csvfile:
            for row in csvfile:
                cols = row.split(',')
                if(cols[1].strip() == "/muse/eeg"):
                    raw_data.append(cols[2:6])

        dt = np.dtype('Float64')            
        raw_data = np.array(raw_data, dtype=dt) 
        
    if source == 'openbci': 
        skiprows = 5
        raw_data = np.loadtxt(path + filename,
                      delimiter=',',
                      skiprows=skiprows,
                      usecols=(0,1,2,3,4,5,6,7,8)
                      )   
                      
            
    if source == 'openbci-openvibe': 
        skiprows = 2
        raw_data = np.loadtxt(path + filename,
                      delimiter=',',
                      skiprows=skiprows,
                      usecols=(0,1,2,3,4,5,6,7,8)
                      )                   
                      
                      
                         
    return raw_data

class EEGrunt:
    def __init__(self, data, path, filename, source):
        self.raw_data = data
        self.path = path
        self.filename = filename
        self.source = source
        
        if self.source == 'openbci' or self.source == 'openbci-openvibe':
            self.fs_Hz = 250.0
            self.NFFT = 256*2
            self.nchannels = 8
            self.channels = [1,2,3,4,5,6,7,8]
            self.col_offset = -1
            if(filename[(len(filename) - 3):] == "csv"):
                self.col_offset = 0

        
        if self.source == 'muse':
            self.fs_Hz = 220.0
            self.NFFT = 220*2
            self.nchannels = 4
            self.channels = [1,2,3,4]
            self.col_offset = -1
            
            
        self.sample_block = 11
        
        self.plot = 'show'
        
        self.overlap  = self.NFFT - int(0.25 * self.fs_Hz)
        self.t_sec = np.arange(len(self.raw_data[:, 0])) /self.fs_Hz

    
    def load_channel(self,channel):
        channel_data = self.raw_data[:,(channel+self.col_offset)]
        self.channel = channel
        self.data = channel_data
        
        
    def packet_check(self):
        data_indices = self.data[:, 0]
        d_indices = data_indices[2:]-data_indices[1:-1]
        n_jump = np.count_nonzero((d_indices != 1) & (d_indices != -255))
        print("Packet counter discontinuities: " + str(n_jump))
        self.n_jump  = n_jump

    def remove_dc_offset(self):
        hp_cutoff_Hz = 1.0
        
        print("Highpass filtering at: " + str(hp_cutoff_Hz) + " Hz")
        
        b, a = signal.butter(2, hp_cutoff_Hz/(self.fs_Hz / 2.0), 'highpass') 
        self.data = signal.lfilter(b, a, self.data, 0)

        
    def notch_mains_interference(self):
        notch_freq_Hz = np.array([60.0])  # main + harmonic frequencies
        for freq_Hz in np.nditer(notch_freq_Hz):  # loop over each target freq
            bp_stop_Hz = freq_Hz + 3.0*np.array([-1, 1])  # set the stop band       
            b, a = signal.butter(3, bp_stop_Hz/(self.fs_Hz / 2.0), 'bandstop') 
            self.data = signal.lfilter(b, a, self.data, 0)
            print("Notch filter removing: " + str(bp_stop_Hz[0]) + "-" + str(bp_stop_Hz[1]) + " Hz")
            
    def bandpass(self,start,stop):
        bp_Hz = np.zeros(0)
        bp_Hz = np.array([start,stop])
        b, a = signal.butter(3, bp_Hz/(self.fs_Hz / 2.0),'bandpass')
        print("Bandpass filtering to: " + str(bp_Hz[0]) + "-" + str(bp_Hz[1]) + " Hz")
        return signal.lfilter(b, a, self.data, 0)
         
        
    def smooth(x,window_len=11,window='hanning'):
        if x.ndim != 1:
            raise ValueError, "smooth only accepts 1 dimension arrays."
        if x.size < window_len:
            raise ValueError, "Input vector needs to be bigger than window size."
        if window_len<3:
            return x
        if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
            raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
        s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
        if window == 'flat': #moving average
            w=np.ones(window_len,'d')
        else:
            w=eval('np.'+window+'(window_len)')
        y=np.convolve(w/w.sum(),s,mode='valid')
        return y

    def plotit(self,plt, plotname=""):
        if self.plot == 'show':
            plt.show()
        if self.plot == 'save':
            plt.savefig('plots/EEGrunt_'+plotname+'.png')

    def signalplot(self,x_values,x_label,y_label,title):
        plt.figure(figsize=(10,5))
        plt.subplot(1,1,1)
        plt.plot(x_values,data)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title("Plot of "+title)
        self.plotit(plt)
        
    def get_spectrum_data(self):
        self.spec_PSDperHz, self.spec_freqs, self.spec_t = mlab.specgram(np.squeeze(self.data),
                                       NFFT=self.NFFT,
                                       window=mlab.window_hanning,
                                       Fs=self.fs_Hz,
                                       noverlap=self.overlap
                                       ) # returns PSD power per Hz
        # convert the units of the spectral data
        self.spec_PSDperBin = self.spec_PSDperHz * self.fs_Hz / float(self.NFFT) 
    

    def spectrogram(self):
        f_lim_Hz = [0, 50]   # frequency limits for plotting
        plt.figure(figsize=(10,5))
        # data = data - np.mean(data,0)
        ax = plt.subplot(1,1,1)    
        plt.pcolor(self.spec_t, self.spec_freqs, 10*np.log10(self.spec_PSDperBin))  # dB re: 1 uV
        plt.clim([-25,26])
        plt.xlim(self.spec_t[0], self.spec_t[-1]+1)
        plt.ylim(f_lim_Hz)
        plt.xlabel('Time (sec)')
        plt.ylabel('Frequency (Hz)')
        plt.title("Spectrogram of "+self.default_plot_title)
        # add annotation for FFT Parameters
        ax.text(0.025, 0.95,
            "NFFT = " + str(self.NFFT) + "\nfs = " + str(int(self.fs_Hz)) + " Hz",
            transform=ax.transAxes,
            verticalalignment='top',
            horizontalalignment='left',
            backgroundcolor='w')
        self.plotit(plt, 'Channel '+str(self.channel)+' spectrogram')

    def plot_spectrum_avg_fft(self):        
        spectrum_PSDperHz = np.mean(self.spec_PSDperHz,1)
        plt.figure(figsize=(10,5))
        plt.plot(self.spec_freqs, 10*np.log10(spectrum_PSDperHz))  # dB re: 1 uV
        plt.xlim((0,60))
        plt.ylim((-30,50))
        plotname = 'Channel '+str(self.channel)+' Spectrum Average FFT Plot'
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('PSD per Hz (dB re: 1uV^2/Hz)')
        plt.title("Channel "+str(self.filename)+" Spectrum Average FFT Plot\n"+self.filename)
        self.plotit(plt, plotname)
        
        
    def plot_band_power(self,start_freq,end_freq,band_name):    
        print("Plotting band power over time. Frequency range: "+str(start_freq)+" - "+str(end_freq))
        title = 'Trend Graph of '+band_name+' EEG Amplitude over Time '+self.default_plot_title
        bool_inds = (self.spec_freqs > start_freq) & (self.spec_freqs < end_freq)
        band_power = np.sqrt(np.amax(self.spec_PSDperBin[bool_inds, :], 0))
        plt.figure(figsize=(10,5))    
        plt.plot(self.spec_t,band_power)
        plt.ylim([np.amin(band_power), np.amax(band_power)+1])
        # plt.xlim(len(x)/config['sample_block'])
        plt.xlabel('Time (sec)')
        plt.ylabel('EEG Amplitude (uVrms)')
        plt.title(title)
        self.plotit(plt, 'Channel '+str(self.channel)+' trend graph')


    def plot_coherence_fft(self, s1, s2, chan_a, chan_b):
        plt.figure()
        plt.ylabel("Coherence")
        plt.xlabel("Frequency (Hz)")
        plt.title("Coherence between channels "+chan_a+" and " +chan_b +" in the "+str(config['band'][0])+"-"+str(config['band'][1])+" Hz band.")
        plt.grid(True)
        plt.xlim(config['band'][0],config['band'][1])
        cxy, f = plt.cohere(s1, s2, NFFT, fs_Hz)
        self.plotit(plt)
