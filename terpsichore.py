#!/usr/bin/env python2

import argparse
import numpy as np
import numpy.fft as fft
import operator
import signals as sig
import sys
import wave

def fourier(wave, fr):
    return zip([x * fr for x in fft.fftfreq(len(wave)) if x > 0], np.absolute(fft.rfft(wave).real[1:]))

NOTES = ['a', 'a#', 'b', 'c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#']

def freq2note(f):
    l = np.log(f / 440.) / np.log(np.power(2, 1/12.))
    n = np.int(np.round(l))
    note = NOTES[np.mod(n, 12)]
    octave = np.int(n / 12.) + 4
    cents = np.round(100 * (l - n))
    return (note, octave, n)

SAMPLESIZE = 4400

def handle_note(n, start, dur):
    (note, octave, off) = n
    print('{} ({}) from {} for {}s'.format(note, octave, start, dur))

class Transcriber:
    def __init__(self, framerate, add_note):
        self.framerate = framerate
        self.add_note = add_note
        self.buffer = np.array([], dtype=np.int16)
        self.samplestart = 0
        self.current = {}

    def process(self, data):
        np.concatenate((self.buffer, data))
        while self.samplestart + SAMPLESIZE < len(data):
            sample = data[self.samplestart:self.samplestart+SAMPLESIZE]

            freqs = np.array([x * self.framerate
                              for x in fft.fftfreq(len(sample)) if x > 0])
            spectrum = np.absolute(fft.rfft(sample).real[1:])

            maxes = sig.argrelmax(spectrum, order=4, axis=0)[0]
            maxes = sorted(maxes, key=lambda i:spectrum[i], reverse=True)
            maxes = [m for m in maxes if spectrum[m] > spectrum[maxes][0]/2.]

            notes = [freq2note(freqs[m]) for m in maxes]

            # Send and kill ended notes
            kill = []
            for note in self.current:
                if not note in notes:
                    dur = self.current[note] / self.framerate
                    if dur > 0.0002:
                        self.add_note(note, self.samplestart / float(self.framerate) - dur, dur)
                    kill.append(note)
            for k in kill:
                del(self.current[k])

            # Register new notes
            for note in set(notes):
                if note in self.current:
                    self.current[note] += SAMPLESIZE/2.
                else:
                    self.current[note] = 0.

            # Advance
            self.samplestart += SAMPLESIZE/2

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('wav', type=str, help='audio file')
    args = parser.parse_args()

    # Read the WAV file
    wav = wave.open(args.wav)
    if wav.getnchannels() != 1:
        print("Too many channels!")
        sys.exit(1)
    if wav.getsampwidth() != 2:
        print("Bad sample width!")
        sys.exit(1)
    framerate = wav.getframerate()
    data = np.fromstring(wav.readframes(wav.getnframes()), dtype=np.int16)
    wav.close()

    transcriber = Transcriber(framerate, handle_note)
    transcriber.process(data)
