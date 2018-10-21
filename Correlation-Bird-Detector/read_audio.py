#!/usr/bin/python

import pyaudio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.io.common import EmptyDataError
from scipy import signal
from scipy.io import wavfile
import time
import datetime
from glob import glob
from os import path
import os

import detect_historical_cusum as detect_cusum

# Index 2 is the microphone!
audio = pyaudio.PyAudio()
for i in range(audio.get_device_count()):
    dev = audio.get_device_info_by_index(i)
    print(i, dev["name"], dev["maxInputChannels"])


def get_audio_from_file(filename):
    print("Using existing data...")
    fs, amplitude = wavfile.read("Input Signals/" + filename)
    return amplitude


def get_mic_data():
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        frames_per_buffer=CHUNK,
        input_device_index=MIC_INDEX,
        input=True)

    print("recording...")
    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        # data = stream.read(CHUNK)

        frames.append(data)
    byteAudio = b''.join(frames)
    print("finished recording")

    # stop Recording
    stream.stop_stream()
    stream.close()
    audio.terminate()
    amplitude = np.frombuffer(byteAudio, np.int16)
    return amplitude


def detect_correlation_peaks(inputSignal, fileNameToDetect, start_dt, thresholds=[3], use_mic=False, days=0):
    if DEBUG_MODE:
        print("Correlating signal...")
    intermediate_time = time.time()
    # Correlate the data with a plover call
    fs, call_to_detect = wavfile.read(fileNameToDetect)
    call_to_detect = call_to_detect[:, 0]
    call_to_detect = call_to_detect[::-1]

    corr = signal.fftconvolve(inputSignal, call_to_detect, mode="same")
    if DEBUG_MODE:
        print("--- Took %s seconds ---" % (time.time() - intermediate_time))
        intermediate_time = time.time()

    if DEBUG_MODE:
        print("Finding envelope of correlation...")
    # Find the envelope of the cross correlation by squaring and filtering
    N = 10000
    envelope = corr * corr
    envelope = signal.fftconvolve(envelope, np.ones((N,)) / N, mode="valid")
    if DEBUG_MODE:
        print("--- Took %s seconds ---" % (time.time() - intermediate_time))
        intermediate_time = time.time()

    bird_name = fileNameToDetect.split(".wav")[0]
    bird_name = bird_name.split("/")[-1]

    print("Finding signal peaks of " + bird_name)
    min_threshold = 1 * 10**16
    df = pd.DataFrame()

    for threshold in thresholds:
        if DEBUG_MODE:
            print("Using threshold of " + str(threshold) + " standard deviations")
            smooth_std = threshold * envelope.std()
        else:
            smooth_std = envelope.mean() + threshold * envelope.std()

        # This minimum threshold is a way to avoid the system detecting calls when there's nothing similar at all
        if smooth_std < min_threshold and use_mic:
            smooth_std = min_threshold

        # The calls must at least be separated by 5s
        peaks, properties = signal.find_peaks(envelope, height=smooth_std, distance=fs)

        # plot_correlation_envelope(plt, envelope, peaks, smooth_std)

        detected_peaks_sec = peaks / float(RATE)
        delta = []
        for time_s in detected_peaks_sec:
            if DEBUG_MODE:
                timestamp = datetime.datetime(year=2000, month=1, day=1) + datetime.timedelta(seconds=time_s)
            else:
                timestamp = start_dt + datetime.timedelta(seconds=time_s)
            timestamp = timestamp + datetime.timedelta(days=days)
            delta.append(timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f"))

        df[threshold] = pd.Series(delta)

    if DEBUG_MODE:
        print("--- Took %s seconds ---" % (time.time() - intermediate_time))

    return df


def write_recording():
    print("ERROR: Method not written yet")
    # Write the recording
    # waveFile = wave.open(WAVE_OUTPUT_FILENAME, "wb")
    # waveFile.setnchannels(CHANNELS)
    # waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    # waveFile.setframerate(RATE)
    # waveFile.writeframes(b''.join(frames))
    # waveFile.close()


def save_peak_data(peaks, filename, directory=None, use_mic=False):
    # Extract the name of the bird from filename of known signal
    bird_name = filename.split(".")[0]
    bird_name = bird_name.split("/")[-1]

    if OUTPUT_DIRECTORY not in os.listdir(os.getcwd()):
        os.makedirs("Detected Peaks")

    if use_mic:
        try:
            historical_peaks = pd.read_csv(OUTPUT_DIRECTORY + "/" + bird_name + ".csv", header=None)
            peaks.columns = historical_peaks.columns
        except (EmptyDataError, IOError):
            historical_peaks = pd.DataFrame()

        historical_peaks = historical_peaks.append(peaks, ignore_index=True)
        historical_peaks.to_csv(OUTPUT_DIRECTORY + "/" + bird_name + ".csv", index=False, header=None)
    else:
        subdirectory = directory
        if directory is None:
            subdirectory = "Correlation " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if subdirectory not in os.listdir(os.getcwd() + "/" + OUTPUT_DIRECTORY):
            os.makedirs(OUTPUT_DIRECTORY + "/" + subdirectory)

        if bird_name not in os.listdir(os.getcwd() + "/" + OUTPUT_DIRECTORY + "/" + subdirectory):
            os.makedirs(OUTPUT_DIRECTORY + "/" + subdirectory + "/" + bird_name)

        for threshold in peaks.columns:
            peaks_dropped_nan = peaks[threshold].dropna(how="any")
            peaks_dropped_nan.to_csv(OUTPUT_DIRECTORY + "/" + subdirectory + "/" + bird_name + "/" + str(threshold) + ".csv", index=False)


def plot_correlation_envelope(plt, envelope, peaks, smooth_std):
    # Plot the correlation envelope with the detected peak values
    fig = plt.figure()
    s = fig.add_subplot(111)
    s.plot(envelope, label="Cross-correlation Envelope")
    s.plot(peaks, envelope[peaks], "x", label="Detected Peaks", markersize=10, linewidth=2)
    s.axhline(y=smooth_std, color="r", linestyle="dashed", label=r'$2\sigma + \mu$')
    s.legend(fontsize=10, numpoints=1, bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.xlabel("Sample")
    plt.ylabel("Cross-correlation Envelope")
    plt.ylim(bottom=0)
    # fig.savefig("Graphs/" + filename + "/envelope.pdf", format="pdf", dpi=300, bbox_inches="tight")


def plot_amplitude(plt, amplitude, filename):
    fig = plt.figure()
    s = fig.add_subplot(111)
    s.plot(amplitude, label="Audio Input")
    plt.xlabel("Sample")
    plt.ylabel("Amplitude")
    fig.savefig("Graphs/" + filename + "/amplitude.png", format="png", dpi=300, bbox_inches="tight")


def plot_spectrogram(plt, amplitude, filename):
    # Spectrogram plot
    fig = plt.figure()
    s = fig.add_subplot(111)
    s.specgram(amplitude, Fs=RATE)
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    fig.savefig("Graphs/" + filename + "/spectrogram.png", format="png", dpi=300, bbox_inches="tight")


# The main method
plt.rcParams['agg.path.chunksize'] = 20000

USE_MIC = False
DEBUG_MODE = True

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
MIC_INDEX = 2
RECORD_SECONDS = 20
WAVE_OUTPUT_FILENAME = "file.wav"
OUTPUT_DIRECTORY = "Detected Peaks"

# TODO: get this list from /"Actual Data" instead
# TODO: get calls from glob

callsToDetect = glob("Test Bird Calls/*")
check_change = datetime.timedelta(seconds=30)

if USE_MIC:
    print("Using microphone as input...")
    startup_time = datetime.datetime.now()
    days = 0

    while True:
        if DEBUG_MODE:
            fs, inputSignal = wavfile.read("Input Signals/trimmed_no_overlap.wav")
        else:
            days = days + 1
            print("Day " + str(days))
            inputSignal = get_mic_data()

        start_dt = datetime.datetime.now()
        start_time = intermediate_time = time.time()

        for fileNameToDetect in callsToDetect:
            detected_peaks = detect_correlation_peaks(inputSignal=inputSignal, fileNameToDetect=fileNameToDetect,
                                                      start_dt=start_dt, use_mic=True, days=days)
            save_peak_data(detected_peaks, fileNameToDetect, use_mic=True)

        print("--- Batch took %s seconds to process ---" % (time.time() - start_time))

        if days % 5 == 0:
            print("Checking for change detection...")

            for fileNameToDetect in callsToDetect:
                bird_name = fileNameToDetect.split(".wav")[0]
                bird_name = bird_name.split("/")[-1]

                # Get the csv data for the bird removed
                try:
                    date_range = pd.date_range(start_dt, periods=days).tolist()
                    daily_counts = pd.Series(date_range)
                    daily_counts = daily_counts.dt.normalize().value_counts() - 1

                    historical_peaks = pd.read_csv(OUTPUT_DIRECTORY + "/" + bird_name + ".csv", header=None)
                    historical_peaks = pd.to_datetime(historical_peaks[historical_peaks.columns[0]], format="%Y-%m-%dT%H:%M:%S.%f")

                    historical_counts = historical_peaks.dt.normalize().value_counts()
                    daily_counts = daily_counts.add(historical_counts, fill_value=0)
                    change, message = detect_cusum.detect_historical_cusum(daily_counts, threshold=2, look_back=5)
                    print(message + "for " + bird_name)
                except (EmptyDataError, IOError):
                    print("There was no data to examine for " + bird_name)

else:
    print("Using existing data as input...")

    pattern = "Input Signals/*.wav"
    files = [path.basename(x) for x in glob(pattern)]

    start_dt = datetime.datetime.now()

    for filename in files:
        print("Testing input signal: " + filename)
        fs, inputSignal = wavfile.read("Input Signals/" + filename)

        SNR = filename.split(".wav")[0]
        directory = "Correlation " + SNR + "dB " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for fileNameToDetect in callsToDetect:
            # if fileNameToDetect != "Test Bird Calls/Common Koel (eudynamys-scolopacea).wav":
            #     continue

            detected_peaks = detect_correlation_peaks(inputSignal=inputSignal, fileNameToDetect=fileNameToDetect,
                                                      start_dt=start_dt, thresholds=np.arange(0, 0.005, 0.0001))
            save_peak_data(detected_peaks, fileNameToDetect, directory=directory)

print("finished it!")
