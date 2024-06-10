
'''The Record class is defined in such a way that it doesn't take any user data and
still does it's job by detecting input to sound card, it checks whether the
channels are proper and monitors which one works better for the device

The main Plotting functions file has extended functions to monitor the
data continuously.

Not all the routines are mine some have been adapted from the recorder software
and some from equalizer, some are written by my friend'''

import threading
import time
import scipy.io.wavfile
import pyaudio
import scipy.io.wavfile
import numpy as np

def FFT(data,rate): #This is the main function for filtering adapted from
    # https://github.com/swharden/FftSharp#-fftsharp
    # FftSharp is a collection of Fast Fourier Transform (FFT) tools for .NET.
    # FftSharp is provided under the permissive MIT license so it is
    # suitable for use in commercial applications.
    data=data*np.hamming(len(data))
    fft=np.fft.fft(data)
    fft=10*np.log10(np.abs(fft))
    freq=np.fft.fftfreq(len(fft),1/rate)
    return freq[:int(len(freq)/2)],fft[:int(len(fft)/2)] #given some data points
                                         # and a rate, returns [freq,power]

class Record(object):
    def __init__(self,device=None,rate=None,chunk=4096,maxMemorySec=5):
        #breaks the signal into smaller chunks of 5 sec duration and 4096 bits

        """For this function to work stream_start function should be called.
        - if there's no device, it will take input from whatever the first valid
        input is present
        - Lowest rate will be used when the rate is not given. For e.g 8000 """

        # config
        self.chunk = chunk   # This means there is no need of multiple power
        self.maxMemorySec = maxMemorySec  # Deletes if more than memory
                                          # and re-updates
        self.device=device
        self.rate=rate

        # internal variables
        self.chunks_Recorded=0
        self.p=pyaudio.PyAudio() #This keeps the signal incoming as long
                                 # as user wants
        self.t=False             #After a period of time it should become threads

    ### TESTING AND INITIALIZING SOUND CARD

    def set_low_rate(self,device): #This sets the incoming audio signal
                                     # to one of the lowest supported rate.

        for test_rate in [8000, 9600, 11025, 12000, 16000, 22050, 24000,
                         32000, 44100, 48000, 88200, 96000, 192000]:
            if self.validation_check(device,test_rate):
                return test_rate
        print("OOPS! I'm Sorry, can't figure the Device",device)
        return None

    def validation_check(self,device,rate=44100): #Checks whether a rate and
                                  # device ID is valid and returns True/False
        try:
            self.info=self.p.get_device_info_by_index(device)
            if not self.info["maxInputChannels"]>0:
                return False
            stream=self.p.open(format=pyaudio.paInt16,channels=1,
               input_device_index=device,frames_per_buffer=self.chunk,
               rate=int(self.info["defaultSampleRate"]),input=True)
            stream.close()
            return True
        except:
            return False

    def check_inputdevices(self):

        #Checks for the devices that is open for mic signal
        #It is called when object PyAudio is present

        microphone=[]
        for device in range(self.p.get_device_count()):
            if self.validation_check(device):
                microphone.append(device)
        if len(microphone)==0:
            print("Ohho! no microphone devices found!")
        else:
            print("Yay! found %d microphone devices: %s"%(len(microphone),microphone))
        return microphone

    ### STARTUP AND SHUTDOWN

    def startup(self):

        ##This sub routine is for checking the settings are ok and startup
        #after changing any particular setting like rate before it starts to record


        if self.device is None:
            self.device=self.check_inputdevices()[0]  #It picks the first device
        if self.rate is None:
            self.rate=self.set_low_rate(self.device)
        if not self.validation_check(self.device,self.rate):
            print("figuring out an optimum mic device/rate...")
            self.device=self.check_inputdevices()[0]  #It picks the first device
            self.rate=self.set_low_rate(self.device)
        self.msg='recording from "%s" '%self.info["name"]
        self.msg+='(device %d) '%self.device
        self.msg+='at %d Hz'%self.rate
        self.data=np.array([])
        print(self.msg)


    def shut(self):  #It shuts down slowly
        print(" -- Terminating the stream...")
        self.keepRecording=False  #The threads automatically shuts
        if self.t:
            while(self.t.isPresent()):
                time.sleep(.1)    #Delays till all the threads shuts
            self.stream.stop_stream()
        self.p.terminate()

    ### HANDLING THE STREAM REAL TIME
    # https://github.com/gethiox/GXAudioVisualisation

    def stream_read_chunk(self):   #This sub-routine reads the audio in
                                   # chunks and reinitiate itself
        try:
            data = np.fromstring(self.stream.read(self.chunk),dtype=np.int16)
            self.data=np.concatenate((self.data,data))
            self.chunks_Recorded+=1
            self.dataFirstI=self.chunks_Recorded*self.chunk-len(self.data)
            if len(self.data)>self.maxMemorySec*self.rate:
                pDump=len(self.data)-self.maxMemorySec*self.rate
                self.data=self.data[pDump:]
                self.dataFirstI+=pDump
        except Exception as Exp:
            print(" -- Exception! shutting off...")
            print(Exp,"\n"*5)
            self.keepRecording=False
        if self.keepRecording==True:
            self.stream_thread_new()
        else:
            self.stream.close()
            self.p.terminate()
            self.keepRecording=None
            print(" -- stream has STOPPED")

    def stream_thread_new(self):
        self.t=threading.Thread(target=self.stream_read_chunk)
        self.t.start()

    def stream_starting(self):
        #This routine adds the data to self.data until signal terminates

        self.startup()
        print(" -- starting up the stream")
        self.keepRecording=True   # It sets to false to end the stream
        self.dataFiltered=None
        self.stream=self.p.open(format=pyaudio.paInt16,channels=1,
                      rate=self.rate,input=True,frames_per_buffer=self.chunk)
        self.stream_thread_new()

    def stream_stopping(self,DelayItaBit=True):
        """send the termination command and (optionally) hang till its done"""
        self.keepRecording=False
        if DelayItaBit==False:
            return
        while self.keepRecording is False:
            time.sleep(.1)

    ### AUDIO WAV

    def loadWAV(self,fname):
    #Load audio signal from a WAV File in a buffer in form of chunks (self.data)
        self.rate,self.data=scipy.io.wavfile.read(fname)
        print("loaded %.02f sec of data (rate=%dHz)"%(len(self.data)/self.rate,
                                                     self.rate))
        self.startup()
        return

    ### GETTING THE DATA
    def getPCMandFFT(self):
        # returns the parameters fft,data,hz,sec from a current buffer memory.
        if not len(self.data):
            return
        data=np.array(self.data) # make a copy in case processing is slow
        sec=np.arange(len(data))/self.rate
        hz,fft=FFT(data,self.rate)
        return data,fft,sec,hz

    def soft_Edges(self,data,fracEdge=.05):
        """multiple edges by a ramp of a certain percentage."""
        rampSize=int(len(data)*fracEdge)
        mult = np.ones(len(data))
        window=np.hanning(rampSize*2)
        mult[:rampSize]=window[:rampSize]
        mult[-rampSize:]=window[-rampSize:]
        return data*mult

    def Filtering_out(self,freqHighCutoff=40): #Filtering the 40 Hz Frequency
        if freqHighCutoff<=0:
            return self.data
        fft=np.fft.fft(self.soft_Edges(self.data))
        trim=len(fft)/self.rate*freqHighCutoff
        fft[int(trim):-int(trim)]=0
        return np.real(np.fft.ifft(fft))


if __name__=="__main__":
    print("It is written for the purpose of importing.")
