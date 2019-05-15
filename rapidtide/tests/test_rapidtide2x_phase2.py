#!/usr/bin/env python
# -*- coding: latin-1 -*-
from __future__ import print_function

import numpy as np
import matplotlib.pyplot as plt 
from scipy import arange
import os

import rapidtide.io as tide_io
import rapidtide.fit as tide_fit
import rapidtide.util as tide_util
import rapidtide.workflows.rapidtide2x as rapidtide2x_workflow
from rapidtide.tests.utils import get_test_data_path, get_test_target_path, get_test_temp_path, get_examples_path, get_rapidtide_root, get_scripts_path


def test_rapidtide2x(debug=False):
    recalculate = True
    if recalculate:
        # create outputdir if it doesn't exist
        try:
            if debug:
                os.makedirs(get_test_temp_path())
            print(get_test_temp_path(), 'created')
        except OSError:
            if debug:
                print(get_test_temp_path(), 'exists')
            else:
                pass
    
        # and launch the processing
        theargs = ['rapidtide2x']
        theargs += [os.path.join(get_examples_path(), 'fmri.nii.gz')]
        theargs += [os.path.join(get_test_temp_path(), 'rapidtide2x_phase2output')]
        theargs += ['--regressor=' + os.path.join(get_test_data_path(), 'rapidtide2x_phase1target_reference_fmrires.txt')]
        theargs += ['--regressortstep=1.5']
        theargs += ['--limitoutput']
        theargs += ['-s', '25.0']
        theargs += ['-L']
        theargs += ['-r', '-20,20']
        theargs += ['-f', '2']
        theargs += ['--passes=3']
        theargs += ['--refineoffset']
        theargs += ['--despecklepasses=4']
        theargs += ['--accheck']
        theargs += ['--nprocs=2']
        theargs += ['--saveoptionsasjson']
        theargs += ['--detrendorder=3']
        theargs += ['--pickleft']
        theargs += ['--corrmask=' + os.path.join(get_examples_path(), 'quartermask.nii.gz')]
        theargs += ['--noglm']
        rapidtide2x_workflow.rapidtide_main(theargs)
    
    diffmaps = tide_util.comparerapidtideruns(os.path.join(get_test_temp_path(), 'rapidtide2x_phase2output'), os.path.join(get_test_target_path(), 'rapidtide2x_phase2target'))

    for mapname, maps in diffmaps.items():
        print('checking', mapname)
        print('\trelmindiff', maps['relmindiff'])
        print('\trelmaxdiff', maps['relmaxdiff'])
        print('\trelmeandiff', maps['relmeandiff'])
        print('\trelmse', maps['relmse'])
        assert maps['relmindiff'] < 1e2
        assert maps['relmaxdiff'] < 1e2
        assert maps['relmeandiff'] < 1e-2
        assert maps['relmse'] < 1e2

def main():
    test_rapidtide2x(debug=True)


if __name__ == '__main__':
    main()
