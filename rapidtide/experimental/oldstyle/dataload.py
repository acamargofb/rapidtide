#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 25 15:57:03 2018

@author: neuro
"""

import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from scipy import fftpack
from statsmodels.robust.scale import mad

try:
    import pyfftw

    pyfftwexists = True
    fftpack = pyfftw.interfaces.scipy_fftpack
    pyfftw.interfaces.cache.enable()
except ImportError:
    pyfftwexists = False


def filtscale(data, scalefac=1.0, reverse=False, hybrid=False, lognormalize=True, epsilon=1e-10, numorders=6):
    if not reverse:
        specvals = fftpack.fft(data)
        if lognormalize:
            themag = np.log(np.absolute(specvals) + epsilon)
            scalefac = np.max(themag)
            themag = (themag - scalefac + numorders) / numorders
            themag[np.where(themag < 0.0)] = 0.0
        else:
            scalefac = np.std(data)
            themag = np.absolute(specvals) / scalefac
        thephase = np.angle(specvals)
        thephase = thephase / (2.0 * np.pi) - 0.5
        if hybrid:
            return np.stack((thedata, themag), axis=1), scalefac
        else:
            return np.stack((themag, thephase), axis=1), scalefac
    else:
        if hybrid:
            return data[:, 0]
        else:
            thephase = (data[:, 1] + 0.5) * 2.0 * np.pi
            if lognormalize:
                themag = np.exp(data[:, 0] * numorders - numorders + scalefac)
            else:
                themag = data[:, 0] * scalefac
            specvals = themag * np.exp(1.0j * thephase)
            return  fftpack.ifft(specvals).real

def tobadpts(name):
    return name.replace('.txt', '_badpts.txt')


def tocardfmri(name):
    return name.replace('normpleth', 'cardfromfmri')


def prep(window_size,
        step=1,
        lag=0,
        excludethresh=4.0,
        usebadpts=False,
        startskip=200,
        endskip=0,
        thesuffix='sliceres',
        thedatadir='/data1/frederic/test/output',
        dofft=False,
        debug=False,
        readlim=None,
        countlim=None):

    print('entering dataload prep')
    print('searching for data with suffix', thesuffix, 'in', thedatadir)
    searchstring = os.path.join(thedatadir, '*normpleth_' + thesuffix + '.txt')
    print('searchstring:', searchstring)
    fromfile = sorted(glob.glob(searchstring))

    # make sure all files exist
    cleanfilelist = []
    print('checking datafiles')
    for physioname in fromfile:
        if os.path.isfile(tocardfmri(physioname)):
            if usebadpts:
                if os.path.isfile(tobadpts(physioname.replace('normpleth', 'pleth'))) \
                    and os.path.isfile(tobadpts(tocardfmri(physioname))):
                    cleanfilelist.append(physioname)
                    print(cleanfilelist[-1])
            else:
                cleanfilelist.append(physioname)
                print(cleanfilelist[-1])
    if usebadpts:
        print(len(cleanfilelist), 'runs pass all 4 files present check')
    else:
        print(len(cleanfilelist), 'runs pass both files present check')

    # find out how long the files are
    tempy = np.loadtxt(cleanfilelist[0])
    tempx = np.loadtxt(cleanfilelist[0].replace('normpleth', 'cardfromfmri'))
    tclen = np.min([tempx.shape[0], tempy.shape[0]])
    print('tclen set to', tclen)

    # allocate target arrays
    print('allocating arrays')
    if readlim is None:
        s = len(cleanfilelist)
    else:
        s = readlim
    x1 = np.zeros([tclen, s])
    y1 = np.zeros([tclen, s])
    names = []
    if usebadpts:
        bad1 = np.zeros([tclen, s])

    # now read the data in
    count = 0
    print('checking data')
    for i in range(s):
        print('processing ', cleanfilelist[i])
        tempy = np.loadtxt(cleanfilelist[i])
        tempx = np.loadtxt(cleanfilelist[i].replace('normpleth', 'cardfromfmri'))
        ntempx = tempx.shape[0]
        ntempy = tempy.shape[0]
        if (ntempx >= tclen) and (ntempy >= tclen):
            x1[:tclen, count] = tempx[:tclen]
            y1[:tclen, count] = tempy[:tclen]
            names.append(cleanfilelist[i])
            if usebadpts:
                tempbad1 = np.loadtxt(tobadpts(cleanfilelist[i].replace('normpleth', 'pleth')))
                tempbad2 = np.loadtxt(tobadpts(tocardfmri(cleanfilelist[i])))
                bad1[:tclen, count] = 1.0 - (1.0 - tempbad1[:tclen]) * (1.0 - tempbad2[:tclen])
            count += 1
    print(count, 'runs pass file length check')

    if countlim is not None:
        if count > countlim:
            count = countlim

    print('filtering', count, 'subjects worth of data')
    y = y1[startskip:, :count]
    x = x1[startskip:, :count]
    if usebadpts:
        bad = bad1[startskip:, :count]
    print('xshape, yshape:', x.shape, y.shape)

    # normalize input and output data
    print('normalizing data')
    print('y shape:', y.shape, 'count:', count)
    if debug:
        for thesubj in range(count):
            print('prenorm sub', thesubj, 'min, max, mean, std, MAD x, y:', thesubj,
                  np.min(x[:, thesubj]), np.max(x[:, thesubj]), np.mean(x[:, thesubj]), np.std(x[:, thesubj]), mad(x[:, thesubj]),
                  np.min(y[:, thesubj]), np.max(y[:, thesubj]), np.mean(y[:, thesubj]), np.std(x[:, thesubj]), mad(y[:, thesubj]))

    y -= np.mean(y, axis=0)
    thestd = np.std(y, axis=0)
    themad = mad(y, axis=0)
    for thesubj in range(themad.shape[0]):
        if themad[thesubj] > 0.0:
            y[:, thesubj] /= themad[thesubj]

    x -= np.mean(x, axis=0)
    themad = mad(x, axis=0)
    thestd = np.std(x, axis=0)
    for thesubj in range(themad.shape[0]):
        if themad[thesubj] > 0.0:
            x[:, thesubj] /= themad[thesubj]

    if debug:
        for thesubj in range(count):
            print('postnorm sub', thesubj, 'min, max, mean, std, MAD x, y:', thesubj,
                  np.min(x[:, thesubj]), np.max(x[:, thesubj]), np.mean(x[:, thesubj]), np.std(x[:, thesubj]), mad(x[:, thesubj]),
                  np.min(y[:, thesubj]), np.max(y[:, thesubj]), np.mean(y[:, thesubj]), np.std(x[:, thesubj]), mad(y[:, thesubj]))

    thefabs = np.fabs(x)
    themax = np.max(thefabs, axis=0)
    cleansubjs = np.where(themax < excludethresh)[0]
    x = x[:, cleansubjs]
    y = y[:, cleansubjs]
    cleannames = []
    print(cleansubjs)
    for theindex in cleansubjs:
        cleannames.append(names[theindex])
    if usebadpts:
        bad = bad[:, cleansubjs]

    print('after filtering, shape of x is', x.shape)

    N_pts = y.shape[0]
    N_subjs = y.shape[1]

    X = np.zeros((1, N_pts, N_subjs))
    Y = np.zeros((1, N_pts, N_subjs))
    if usebadpts:
        BAD = np.zeros((1, N_pts, N_subjs))

    X[0, :, :] = x
    Y[0, :, :] = y
    if usebadpts:
        BAD[0, :, :] = bad

    Xb = np.zeros((N_subjs * (N_pts - window_size - 1), window_size + lag, 1))
    print('dimensions of Xb:', Xb.shape)
    for j in range(N_subjs):
        print('sub', j, '(', cleannames[j], '), min, max X, Y:', j, np.min(X[0, :, j]), np.max(X[0, :, j]), np.min(Y[0, :, j]),
              np.max(Y[0, :, j]))
        for i in range((N_pts - window_size - 1)):
            Xb[j * ((N_pts - window_size - 1)) + i, :, 0] = X[0, step * i:(step * i + window_size + lag), j]

    Yb = np.zeros((N_subjs * (N_pts - window_size - 1), window_size + lag, 1))
    print('dimensions of Yb:', Yb.shape)
    for j in range(N_subjs):
        for i in range((N_pts - window_size - 1)):
            Yb[j * ((N_pts - window_size - 1)) + i, :, 0] = Y[0, step * i:(step * i + window_size + lag), j]

    if usebadpts:
        Xb_withbad = np.zeros((N_subjs * (N_pts - window_size - 1), window_size + lag, 2))
        print('dimensions of Xb_withbad:', Xb_withbad.shape)
        for j in range(N_subjs):
            print('packing data for subject',j)
            for i in range((N_pts - window_size - 1)):
                Xb_withbad[j * ((N_pts - window_size - 1)) + i, :, 0] = \
                    X[0, step * i:(step * i + window_size + lag), j]
                Xb_withbad[j * ((N_pts - window_size - 1)) + i, :, 1] = \
                    BAD[0, step * i:(step * i + window_size + lag), j]
        Xb = Xb_withbad
    
    perm = np.arange(Xb.shape[0])

    if dofft:
        Xb_fourier = np.zeros((N_subjs * (N_pts - window_size - 1), window_size + lag, 2))
        print('dimensions of Xb_fourier:', Xb_fourier.shape)
        Xscale_fourier = np.zeros((N_subjs, N_pts - window_size - 1))
        print('dimensions of Xscale_fourier:', Xscale_fourier.shape)
        Yb_fourier = np.zeros((N_subjs * (N_pts - window_size - 1), window_size + lag, 2))
        print('dimensions of Yb_fourier:', Yb_fourier.shape)
        Yscale_fourier = np.zeros((N_subjs, N_pts - window_size - 1))
        print('dimensions of Yscale_fourier:', Yscale_fourier.shape)
        for j in range(N_subjs):
            print('transforming subject',j)
            for i in range((N_pts - window_size - 1)):
                Xb_fourier[j * ((N_pts - window_size - 1)) + i, :, :], Xscale_fourier[j, i] = \
                    filtscale(X[0, step * i:(step * i + window_size + lag), j])
                Yb_fourier[j * ((N_pts - window_size - 1)) + i, :, :], Yscale_fourier[j, i] = \
                    filtscale(Y[0, step * i:(step * i + window_size + lag), j])
    
    perm = np.arange(Xb.shape[0])
    limit = int(0.8 * Xb.shape[0])

    batchsize = N_pts - window_size - 1

    if dofft:
        train_x = Xb_fourier[perm[:limit], :, :]
        train_y = Yb_fourier[perm[:limit], :, :]

        val_x = Xb_fourier[perm[limit:], :, :]
        val_y = Yb_fourier[perm[limit:], :, :]
        print('train, val dims:', train_x.shape, train_y.shape, val_x.shape, val_y.shape)
        return train_x, train_y, val_x, val_y, N_subjs, tclen - startskip, batchsize, Xscale_fourier, Yscale_fourier
    else:
        train_x = Xb[perm[:limit], :, :]
        train_y = Yb[perm[:limit], :, :]

        val_x = Xb[perm[limit:], :, :]
        val_y = Yb[perm[limit:], :, :]
        print('train, val dims:', train_x.shape, train_y.shape, val_x.shape, val_y.shape)
        return train_x, train_y, val_x, val_y, N_subjs, tclen - startskip, batchsize