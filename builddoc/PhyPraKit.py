#!/usr/bin/python
# module PhyPraKit.py, pyhton3 version
from __future__ import print_function  # for python2.7 compatibility
''' 
.. module PhyPraKit   
   :synopsis: a collection of tools for data analysis
     recommended for "Physikalisches Praktikum am KIT"

.. moduleauthor:: Guenter Quast <g.quast@kit.edu>

**PhyPraKit**  for Data Handling, Visualisation and Analysis

  contains the following functions:

      1. Data input:

        - readColumnData() read data and meta-data from text file
        - readCSV()        read data in csv-format from file with header
        - readtxt()        read data in "txt"-format from file with header
        - readPicoScope()  read data from PicoScope
        - readCassy()      read CASSY output file in .txt format   
        - labxParser()     read CASSY output file, .labx format   
        - writeCSV()       write data in csv-format (opt. with header)

      2. signal processing:

        - offsetFilter()      subtract an offset in array a
        - meanFilter()        apply sliding average to smoothen data
        - resample()          average over n samples
        - simplePeakfinder()  find peaks and dips in an array 
            recommend to ``use convolutionPeakfinder``
        - convolutionPeakfinder() find maxima (peaks) in an array
        - convolutionEdgefinder() find maxima of slope (rising) edges in an array
        - Fourier_fft()       fast Fourier transformation of an array
        - FourierSpectrum()   Fourier transformation of an array 
            ``(slow, preferably use fft version)``
        - autocorrelate()     autocorrelation function

      3. statistics:

        - wmean()  weighted mean

      4. histograms tools:

        - barstat()   statistical information (mean, sigma, erroron mean) from bar chart
        - nhist()    histogram plot based on np.historgram() and plt.bar()
            ``use matplotlib.pyplot.hist() instead``
        - histstat() statistical information from 1d-histogram
        - nhist2d()  2d-histotram plot based on np.histrogram2d, plt.colormesh()
            ``use matplotlib.pyplot.hist2d() instead``  
        - hist2dstat() statistical information from 1d-histogram
        - profile2d()  "profile plot" for 2d data
        - chi2p_indep2d() chi2 test on independence of data

      5. linear regression:

        - linRegression()    linear regression, y=ax+b, with analytical formula
        - linRegressionXY()  linear regression, y=ax+b, with x and y errors 
          ``! deprecated, use `odFit` with linear model instead``
        - odFit()            fit function with x and y errors (scipy ODR)
        - kRegression()      regression, y=ax+b, with (correlated) error on x, and y 
          ``! deprecated, use `kFit` with linear model instead``
        - kFit()             fit function with (correlated) errors on x and y (kafe)

      6. simulated data with MC-method:

        - smearData()          add random deviations to input data
        - generateXYdata()     generate simulated data 

'''

# Author:       G. Quast   Dec. 2013
# dependencies: PYTHON v2.7, numpy, matplotlib.pyplot 
#
# last modified: Nov. 2016
#   16-Nov-16    GQ  readPicoscope now also supports .csv export format    
#                GQ  added fuctions for signal processing/analysis
#   17-Nov-16    GQ  added readCassy for Cassy data in .txt format
#   24-Nov-16    GQ  fixes to FourierSpectrum()
#   07-Dec-16    GQ  changed normalisation of Fourier Amplitudes
#   23-Apr-17    GQ  added auto-correlation function
#                    added readCSV and writeCSV
#   20-May-17    GQ  added readtxt to read data in "txt"-format
#   21-May-17    GQ  simplified read_ColumnData and test_readColumnData
#   22-May-17    GQ  re-implemented readCassy() using readtxt()
#   25-May-17    GQ  allow scalar errors in odFit(), linRegressionXY(),
#                       as in all other fit interfaces
#   27-July-17   GQ  added convolutionEdgefinder() and refactored
#                    convolutionPeakfinder() to use similar components
# ----------------------------------------------------------------------

import numpy as np, matplotlib.pyplot as plt
from scipy import stats

## ------- section 1: input from text files ------------------------

def readColumnData(fname, cchar='#', delimiter=None, pr=True):
  """read column-data from file
       - input is assumed to be columns of floats
       - characters following <cchar>, and <cchar> itself, are ignored          
       - words with preceeding '*' are taken as keywords for meta-data,
         text following the keyword is returned in a dictionary 

     Args:
       * string fnam:      file name
       * int ncols:        number of columns
       * char delimiter:   character separating columns
       * bool pr:          print input to std out if True
  """ 

# -- helper function to filter input lines
  def filter_lines(f, keys, cc='#', delim=None):
    """ filter lines for np.loadtxt and 
        extract non-numerical information

      Args:
        * string f:  file name
        * dictionary keys: emtpy dictionary
        * char cc:   comment character
      Modifies:
        * dictionary keys with keywords found in file
      Yields:
        * a valid line with numerical data
    """
    while True:
      line=f.readline()
      if (not line): break # eof, exit
      if cc in line:
        line=line.split(cc)[0] # ignore everything after comment character    
        if (not line): continue # ignore comment lines
      if (not line.isspace()):  # ignore empty lines
         words=line.split()
         if (words[0][0]=="*"): # definition of a key
           keys[words[0]]=' '.join(words[1:]) # get rest of line 
         else:
           # have a valid line, change delimiter to white space
           if (delim != None): line=line.replace(delim, ' ')
           yield line  # pass line to loadtxt()
#   -- end filter_lines

# -------------------------------------------------------
# define a dictionary for meta data from file
  mdict = {}
  arr = np.loadtxt( filter_lines(open(fname,'r'), 
                    mdict, delim=delimiter, cc=cchar),
                    dtype=np.float32, unpack=True)

# eventually, print out the data we just read:
  if pr:
    print("\n*==* readColumnData: file read successfully")
    print("keywords found:")
    for key in mdict:
      if (mdict[key]!=None): print(key, ':', mdict[key])
    print("data read:")
    for i in range(arr.shape[0]): print(arr[i])

  return arr, mdict

def readCSV(file, nlhead=1):
  '''
  read Data in .csv format, skip header lines
  
  Args:
    * file: string, file name 
    * nhead: number of header lines to skip
    * delim: column separator
  Returns:
    * hlines: list of string, header lines
    * data: 2d array, 1st index for columns

  '''
# --------------------------------------------------------------------

  # open file for read (if necessary)
  if type(file)==type(' '): f = open(file, 'r') # file is a file name
  else: f=file     # assume input is file handle of an open file 

  hlines=[]
  
  # read header
  for i in range (nlhead):
   hlines.append(f.readline()) # header line(s)

  # read data
  data = np.loadtxt(f, delimiter=',', unpack=True) # column-wise data
  return hlines, data


def readtxt(file, nlhead=1, delim='\t'):
  '''
  read floating point data in general txt format
    skip header lines, replace decimal comma, remove special characters
  
  Args:
    * file: string, file name 
    * nhead: number of header lines to skip
    * delim: column separator
  Returns:
    * hlines: list of string, header lines
    * data: 2d array, 1st index for columns

  '''
# --------------------------------------------------------------------
# -- helper function to filter input lines
  def specialCharFilter(f, delim):
    '''a generator fo filter lines read from file
         replace German ',' by '.', remove special characters 

      Args:
        * string f:  file name
      Yields:
        * a valid line with numerical data
    '''
    while True:
      l=f.readline().strip()  # remove leading and trailing white spaces
      if (not l): break       # end-of-file reached, exit

      # remove ascii contol characters (except delimiter) 
      for i in range(32):
        if delim != chr(i) : l=l.replace(chr(i),'') 
      if l=='': continue        # skip empty lines
      # replace German decimal comma (if not CSV format)
      if delim != ',' : filtline=l.replace(',','.') 

      yield filtline                # pass filtered line to loadtxt()
#   -- end specialCharFilter

  # open file for read (if necessary)
  if type(file)==type(' '): f = open(file, 'r') # file is a file name
  else: f = file        # assume input is file handle of an open file 

  hlines=[]
  lfilt = specialCharFilter(f, delim) # python generator 
  # read header
  for i in range (nlhead):
    hlines.append(next(lfilt)) # header line(s)

  # read float data
  data = np.loadtxt(lfilt, dtype=np.float32, delimiter=delim, unpack=True)
  return hlines, data


def readPicoScope(file, prlevel=0):
  '''
  read Data exported from PicoScope in .txt or .csv format
  
  Args:
    * file: string, file name 
    * prlevel: printout level, 0 means silent

  Returns:
    * units: list of strings, channel units  
    * data: tuple of arrays, channel data

  '''
# --------------------------------------------------------------------
#        special treatment to skip/analyze first three lines
  f = open(file, 'r')
  line1=f.readline().strip() # remove leading and trailing white space chars
  line2=f.readline().strip()
  units=line2         # contains the units
  line3=f.readline()  # this is an empty line in PicoScope data

  if file.split('.')[1]=="csv":
    delim=','
  else:  
    delim='\t'

  units=units.split(delim)
  nc=len(units)
  data = np.loadtxt(f, dtype=np.float32, delimiter=delim, unpack=True)
  if prlevel: 
    print("*==* readPicoScope: %i columns found:"%nc)
    if prlevel>1:
      for i, d in enumerate(data):
        print("     channel %i,  %i values found, unit %s"%(i, len(d), units[i]))
     
  if len(data) != nc:
    print("  !!! number of data columns inconsistent with number of units")
    exit(1)
  else:  
    return units, data


def readCassy(file, prlevel=0):
  '''
  read Data exported from Cassy in .txt format
  
  Args:
    * file: string, file name 
    * prlevel: printout level, 0 means silent

  Returns:
    * units: list of strings, channel units  
    * data: tuple of arrays, channel data

  '''
# --------------------------------------------------------------------
  delim='\t'                 # Cassy uses <tab> as column delimiter
  hlines, data = readtxt(file, nlhead=5, delim=delim)
  tags = hlines[4].replace('DEF=','').split(delim)
  nc=len(tags)

  if prlevel: 
    print(("*==* readCassy: %i columns found:"%nc))
    if prlevel>1:
      for i, d in enumerate(data):
        print(("     channel %i,  %i values found, tag %s"%(i, len(d), tags[i])))
     
  if len(data) != nc:
    print("  !!! number of data columns inconsistent with number of units")
    exit(1)
  else:  
    return tags, data


def labxParser(file, prlevel=1):
  '''   
  read files in xml-format produced with Leybold CASSY
   
  Args:
     * file:  input data in .labx format
     * prlevel: control printout level, 0=no printout
 
  Returns:
     * list of strings: tags of measurmement vectors
     * 2d list:         measurement vectors read from file 
  '''
# --------------------------------------------------------------------
# dependencies: xml.etree.ElementTree
#
#  30-Oct-16  initial version
# changes :
# --------------------------------------------------------------------
  import xml.etree.ElementTree as ET
  import numpy as np, matplotlib.pyplot as plt
  import sys

  root = ET.parse(file).getroot()
  if root.tag != 'cassylab':
    print(" !!! only cassylab supported - exiting (1) !")
    sys.exit(1)    
  else:
    if(prlevel): print("\n\n*==* labxParser: name of XML root object:\n",\
    ' ', root.tag, root.attrib)
#
# some sanity checks wether we got the right kind of input
  if not root.findall('cassys'):
    print(" !!! no tag 'casssys' found  - exiting (2) !")
    sys.exit(2)    
  if not root.findall('ios'):
    print("! !!! tag 'ios' not found exiting (3) !")
    sys.exit(3)    
#
# print header info if requested 
  if (prlevel>1):
    childvals=[]
    childtags=[]
    for child in root:
      childtags.append(child.tag)
      childvals.append(child.attrib)
    print("    %i children found, " %(len(childtags)), end=' ') 
    print("tags and attributes: \n", end=' ')
    for i in range(len(childtags)):
      print('   ', childtags[i],' : ', childvals[i])

  if(prlevel>2):
    print('\n *==*  Details:') 
    print(" ** found tag 'ios', configuration:")
    for ios in root.findall('ios'):
      print('   ', ios.tag, ios.attrib)
    print("   measurement settings:")
    i=0
    for io in ios.findall('io'): 
      i+=1      
      print("  --> io %i:"%i, io.attrib)
      for qs in io.iter('quantities'): print('   ', qs.tag, qs.attrib)
      for q in qs.iter('quantity'): print('   ', q.tag, q.attrib)

  if(prlevel>2):
    if root.findall('calcs'):
      print("\n ** found tag 'calcs', calc settings:")
      for calcs in root.findall('calcs'):
        i=0
        for calc in calcs.findall('calc'): 
          i+=1      
          print("  --> calc %i:"%i, calc.attrib)

# ---- collect data in vectors 
  # cassylab stores data under the tag "channels:channel:values", 
  #    search for and extract data from xml structure
  varray=[]
  vnames=[]
  vsymbols=[]
  vunits=[]
  vtags=[]
  iv=0
  ic=0
  for clist in root.iter('channels'):
    for c in clist:
      ic+=1
      quantity=c.find('quantity').text
      vnames.append(quantity)
      symbol=c.find('symbol').text
      if symbol is None: symbol=''
      vsymbols.append(symbol)
      unit=c.find('unit').text
      if unit is None: unit=''
      vunits.append(unit)
      vtag = '%i:'%ic + quantity + ':' + symbol + ':' + unit
      vtags.append(vtag)
      if(prlevel>1): 
        print("   --> new channel found", vtag) 
        if(prlevel>2): print("     ", c.attrib)

      values=c.find('values')
      if(prlevel>2): print("     number of values: ", values.attrib)
      varray.append([])
      for v in values:
        varray[iv].append(np.float32(v.text))
      iv+=1

  if (prlevel): 
    print("*==* labxParser:  %i value lists found"%iv)
    for tag in vtags:
      print("  ", tag)
    print("\n\n")

  return vtags, varray


def writeCSV(file, ldata, hlines=[], fmt='%.10g'):
  '''
  write data in .csv format, including header lines
  
  Args:
    * file: string, file name 
    * ldata: list of columns to be written
    * hlines: list with header lines (optional)
    * fmt: format string (optional)

  Returns: 
    * 0/1  for success/fail

  '''
# --------------------------------------------------------------------

  # open file for read (if necessary)
  if type(file)==type(' '): f = open(file, 'w') # file is a file name
  else: f=file     # assume input is file handle of an open file 

  if type(hlines)==type(' '):
     f.write(hlines+'\n')
  elif type(hlines)==type([]):
    for i in range(len(hlines)):
      f.write(hlines[i]+'\n')

  try:
    np.savetxt(f, np.array(ldata).transpose(),
                fmt=fmt, delimiter =',', newline='\n')
    return 0
  except:
    return 1

## ------- section 2: statistics  -----------------------

def wmean(x, sx, pr=True):
  """ weighted mean of np-array x with uncertainties sx
 
    Args:
      * x: np-array of values
      * sx: uncertainties
      * pr: if True, print result

    Returns:
      * float: mean, sigma 
  """
# -------------------------------------------------------

  w = 1/sx**2
  sumw = np.sum(w)
  mean = np.sum(w*x)/sumw
  smean = np.sqrt(1./sumw)
  # eventually, print out the data we just read:
  if pr:
    print("\n weighted mean = %.3g +/- %.3g"%(mean, smean))
  return mean, smean
  
## ------- section 3: signal processing -----------------

def offsetFilter(a):
  ''' 
  correct an offset in array a 
  (assuming a symmetric signal around zero)
  by subtracting the mean
  '''
  return a-a.mean()

def meanFilter(a, width=5):
  ''' 
  apply a sliding average to smoothen data, 

  method:
    value at index i and int(width/2) neighbours are averaged
    to from the new value at index i

    Args:
      * a: np-array of values
      * width: int, number of points to average over
        (if width is an even number, width+1 is used)
 
    Returns:
      * av  smoothed signal curve
  '''
# -----------------------------------------------
  l=len(a)
  av = np.zeros(l) 
  k=int(width/2)
  for i in range(k, l-k+1):
    av[i]= sum(a[i-k:i+k+1])/(2*k+1)

  return av

def resample(a, t=None, n=11):
  ''' 
  perform average over n data points of array a, 
  return reduced array, eventually with corresponding time values 

  method:
    value at index `i` and `int(width/2)` neighbours are averaged
    to from the new value at index `i`

    Args:
      * a, t: np-arrays of values of same length
      * width: int, number of values of array `a` to average over
        (if width is an even number, width+1 is used)
 
    Returns:
      * av: array with reduced number of samples
      * tav:  a second, related array with reduced number of samples 
  '''
  k = int(n/2)
  nav = int( len(a) /(2*k+1))
  av = np.zeros(nav) 
  if t is not None: 
    tav=np.zeros(nav)
  j=0
  for i in range(k, len(a)-k, 2*k+1):
    av[j]= sum(a[i-k:i+k+1])/(2*k+1)
    if t is not None: tav[j]=t[i]
    j+=1
  
  if t is not None:
    return av, tav
  else: 
    return av

def Fourier_fft(t, a):
  ''' 
  Fourier transform of the amplitude spectrum a(t) 
  
  method: 
    uses `numpy.fft` and `numpy.fftfreq`; 
    output amplitude is normalised to number of samples; 

    Args:
      * t: np-array of time values
      * a: np-array amplidude a(t)
 
    Returns:
      * arrays f, a_f: frequencies and amplitudes
  '''
# -----------------------------------------------
  from numpy.fft import fft, fftfreq

  n = len(t)
  dt = (t[-1]-t[0])/(n-1.)       # time step
  freq = fftfreq(n, dt)[:n/2]    # only positive frequencies
  amp = abs(fft(a))[:n/2]*2./n

  return freq, amp


def FourierSpectrum(t, a, fmax=None):
  '''
  Fourier transform of amplitude spectrum a(t), for equidistant sampling times
   (a simple implementaion for didactical purpose only, 
   consider using ``Fourier_fft()`` )

    Args:
      * t: np-array of time values
      * a: np-array amplidude a(t)
 
    Returns:
      * arrays freq, amp: frequencies and amplitudes
  '''
# -----------------------------------------------

  n = len(t)      
  T = t[-1 ]-t[0] # total time covered by sample
  df = 1./T       # smallest frequency and frequency step
  dt = T / (n-1.) # time step, 1/2 1/dt is largest frequency
  fmx = 0.5/dt    # Nyquist Theorem: n/2 frequency components
  if fmax is not None:
    if fmax>fmx:
       print("!!! FourierSpectrum: fmax too large, set to ", fmx)
    fmx = min(fmax, fmx)

  freq = np.arange(df, fmx, df)

  # calulate coefficients
  amp = np.zeros(len(freq))
  i=0
  for f in freq:
    omega = 2. * np.pi * f
    s=sum(a * np.sin(omega * t))*2./n
    c=sum(a * np.cos(omega * t))*2./n
    amp[i] = np.sqrt(s**2 + c**2)
    i+=1
  # alternative implementation without explicitely writing the loop
  #omegat=np.outer(2.*np.pi*freq, t)  # this uses much memory !!
  #s = np.matmul(np.sin(omegat), a)*2./n
  #c = np.matmul(np.cos(omegat), a)*2./n
  #amp = np.sqrt(s**2 + c**2)

  return freq, np.array(amp)


def simplePeakfinder(x, a, th=0.):
  ''' 
  find positions of all maxima (peaks) in data
    x-coordinates are determined from weighted average over 3 data points

  this only works for very smooth data with well defined extrema
    use ``convolutionPeakfinder`` or ``scipy.signal.argrelmax()`` instead

    Args:
      * x: np-array of positions
      * a: np-array of values at positions x
      * th: float, threshold for peaks
 
    Returns:
      * np-array: x positions of peaks as weighted mean over neighbours
      * np-array: y values correspoding to peaks 
  '''
# -----------------------------------------------
# work on normalized input
  y = (a-min(a))/(max(a)-min(a))
# 
  xpeak=[]
  ypeak=[]
  if y[0]-y[1]>th and y[0]-y[2]>th:
    xpeak.append(x[0])    
    ypeak.append(y[0])    
  for i in range(1,len(x)-1):
    if y[i]-y[i-1]>=0. and y[i]-y[i+1]>th: 
      xpeak.append(sum(x[i-1:i+1]*y[i-1:i+1])/sum(y[i-1:i+1]))    
      ypeak.append(y[i])    
  if y[-1]-y[-2]>th and y[-1]-y[-3]>th:
    xpeak.append(x[-1])    
    ypeak.append(y[-1])    

  return np.array(xpeak), np.array(ypeak)

def convolutionFilter(a, v, th=0.):
  ''' 
  convolute normalized array with tmplate funtion and return maxima

  method: 
    convolute array a with a template and return extrema of 
    convoluted signal, i.e. places where template matches best

  Args:
    * a: array-like, input data
    * a: array-like, template 
    * th: float, 0.<= th <=1., relative threshold for places of
      best match above (global) minimum

  Returns:
    * pidx: list, indices (in original array) of best matches

  '''

  anrm = (a-min(a))/(max(a)-min(a))
  c = np.correlate( anrm, v, mode='same')
  #c = np.convolve( anrm, np.flipud(v), 'same')
  # remark: need reversed ordering of v to use np.convolve() for this purpose

# store places of best agreement with the template 
  pidx=[]
  for i in range (1, len(anrm)-1):
    if c[i]>0. and c[i]-c[i-1]>=0. and c[i]-c[i+1]>0. and anrm[i] > th : 
      pidx.append(i) 
  return pidx

def convolutionPeakfinder(a, width=10, th=0.0):
  ''' 
  find positions of all Peaks in data 
    (simple version for didactical purpose, 
    consider using ``scipy.signal.find_peaks_cwt()`` )

  method: 
    convolute array a with rectangular template of given width and
    return extrema of convoluted signal, i.e. places where 
    template matches best

  Args:
    * a: array-like, input data
    * width: int, width of signal to search for
    * th: float, 0.<= th <=1., relative threshold for peaks above (global)minimum

  Returns:
    * pidx: list, indices (in original array) of peaks
  ''' 

#construct a (rectangular) template for a peak
  k=int(width/2)
  v = np.array(\
        [-0.5 for i in range(k)] +\
        [0.5 for i in range(2*k+1)] +\
        [-0.5 for i in range(k)], 
               dtype=np.float32 )
  return convolutionFilter(a, v, th=th)

def convolutionEdgefinder(a, width=10, th = 0.):
  ''' 
  find positions of maximal positive slope in data 

  method: 
    convolute array `a` with an edge template of given width and
    return extrema of convoluted signal, i.e. places of rising edges

  Args:
    * a: array-like, input data
    * width: int, width of signal to search for
    * th: float, 0.<= th <=1., relative threshold above (global)minimum

  Returns:
    * pidx: list, indices (in original array) of rising edges
  ''' 

#construct a (rectangular) template for an edge
  k=int(width/2)
  v = np.array(\
        [-0.5 for i in range(k)] +\
               [0.] +\
        [0.5 for i in range(k)], 
               dtype=np.float32 )
  return convolutionFilter(a, v, th=th)

def autocorrelate(a):
  '''calculate autocorrelation function of input array 

     method: for array of length l, calulate 
     a[0]=sum_(i=0)^(l-1) a[i]*[i] and 
     a[i]= 1/a[0] * sum_(k=0)^(l-i) a[i] * a[i+k-1] for i=1,l-1 

     Args:
       * a: np-array 

     Returns 
       * np-array of len(a), the autocorrelation function
  '''

  l=len(a)
  rho=np.zeros(l)
  for i in range(1, l):
    rho[i] = np.inner(a[i:], a[:-i])
  rho[0] = np.inner(a, a)
  rho = rho/rho[0]

  return rho


## ------- section 4: histograms in 1d and 2d ----------------------

def barstat(bincont, bincent, pr=True):
  """statistics from a bar chart (histogram) 
     with given bin contents and bin centres

     Args:
       * bincont: array with bin content
       * bincent: array with bin centres

     Returns:
       * float: mean, sigma and sigma on mean    
  """
  mean=sum(bincont*bincent)/sum(bincont)
  rms=np.sqrt(sum(bincont*bincent**2)/sum(bincont) - mean**2)
  smean=rms/np.sqrt(sum(bincont))
  if pr: 
    print('bar chart statistics:\n'\
'   mean=%g, sigma=%g, sigma mean=%g\n' %(mean,rms,smean))
  return mean, rms, smean

def nhist(data, bins=50, xlabel='x', ylabel='frequency') :
# ### own implementation of one-dimensional histogram (numpy + matplotlib) ###
  """ Histogram.hist
      show a one-dimensional histogram 

      Args:
        * data: array containing float values to be histogrammed
        * bins: number of bins
        * xlabel: label for x-axis
        * ylabel: label for y axix

      Returns:
        * float arrays: bin contents and bin edges
  """

  bc,be = np.histogram(data,bins) # histogram data
  bincent=(be[:-1] + be[1:])/2.
  w=0.9*(be[1]-be[0])
  plt.bar(bincent,bc,align='center',width=w,facecolor='b',alpha=0.75) #
  plt.xlabel(xlabel,size='x-large') # ... for x ...
  plt.ylabel(ylabel,size='x-large') # ... and y axes
#  plt.show()
  return bc, be

def histstat(binc, bine, pr=True):
  """ Histogram.histstat
    calculate mean, standard deviation and uncertainty on mean 
    of a histogram with bin-contents `binc` and bin-edges `bine`
 
    Args:
      * binc: array with bin content
      * bine: array with bin edges

    Returns:
      * float: mean, sigma and sigma on mean    
  """

  bincent =(bine[1:]+bine[:-1])/2 # determine bincenters
  mean=sum(binc*bincent)/sum(binc)
  rms=np.sqrt(sum(binc*bincent**2)/sum(binc) - mean**2)
  sigma_m=rms/np.sqrt(sum(binc))
  if pr: 
    print('hist statistics:\n'\
'   mean=%g, sigma=%g  sigma of mean=%g\n' %(mean,rms,sigma_m))
  return mean, rms, sigma_m

def nhist2d(x, y, bins=10, xlabel='x axis', ylabel='y axis', clabel='counts'):
# ### own implementation of two-dimensional histogram ###
  """ Histrogram.hist2d
    create and plot a 2-dimensional histogram  

    Args:
      * x: array containing x values to be histogrammed
      * y: array containing y values to be histogrammed
      * bins: number of bins
      * xlabel: label for x-axis
      * ylabel: label for y axix
      * clabel: label for colour index

    Returns:
      * float array: array with counts per bin
      * float array: histogram edges in x
      * float array: histogram edges in y
  """
  H2d, xed, yed = np.histogram2d(x,y,bins) # numpy 2d histogram function
  Hpl = np.rot90(H2d)  # rotate, ...
  Hpl = np.flipud(Hpl) # ... flip, ... 
  Hpl = np.ma.masked_where(Hpl==0,Hpl) # ... and mask zero values, ...
  im = plt.pcolormesh(xed,yed,Hpl,cmap='Blues') # ... then make plot
  cbar = plt.colorbar() # show legend 
  cbar.ax.set_ylabel(clabel) # print lables for legend, ...
  plt.xlabel(xlabel) # ... for x ...
  plt.ylabel(ylabel) # ... and y axes
#  plt.show()
  return H2d, xed, yed

def hist2dstat(H2d, xed, yed, pr=True):
  """
    calculate statistical information from 2d Histogram

    Args:
      * H2d: histogram array (as returned by histogram2d)
      * xed: bin edges in x
      * yed: bin edges in y

    Returns:
      * float: mean x
      * float: mean y 
      * float: variance x
      * float: variance y
      * float: covariance of x and y
      * float: correlation of x and y
  """
  bcx=(xed[:-1]+xed[1:])/2 
  bcy=(yed[:-1]+yed[1:])/2
  sumxy,sumx,sumx2,sumy,sumy2,sum=0.,0.,0.,0.,0.,0.
  for ix in range(0,len(bcx)):
    for iy in range(0,len(bcy)):
      sumxy += H2d[ix,iy]*bcx[ix]*bcy[iy]
      sumx += H2d[ix,iy]*bcx[ix]
      sumx2 += H2d[ix,iy]*bcx[ix]*bcx[ix]
      sumy += H2d[ix,iy]*bcy[iy]
      sumy2 += H2d[ix,iy]*bcy[iy]*bcy[iy]
      sum += H2d[ix,iy]
  meanx = sumx/sum
  varx = (sumx2/sum-meanx*meanx)
  meany = sumy/sum
  vary = (sumy2/sum-meany*meany)
  cov = (sumxy/sum-meanx*meany) 
  cor = cov/np.sqrt(varx*vary)
  if pr: 
    print('hist2d statistics:\n'\
'   <x>=%g, <y>=%g\n\
    var_x=%.2g, var_y=%.2g\n\
    cov=%.2g, cor=%.2g\n'\
    %(meanx,meany,varx,vary,cov,cor))
  return meanx,meany,varx,vary,cov,cor

def profile2d(H2d, xed, yed):
  """
    generate a profile plot from 2d histogram:
      - mean y at a centre of x-bins, standard deviations as error bars

    Args:
      * H2d: histogram array (as returned by histogram2d)
      * xed: bin edges in x
      * yed: bin edges in y

    Returns:
      * float: array of bin centres in x
      * float: array mean
      * float: array rms
      * float: array sigma on mean
  """
  mean_y=[]
  rms_y=[]
  sigm_y=[]
  for ix in range(len(xed)-1):
    m, rms, sigm =histstat(H2d[ix,:], yed, False) 
    mean_y.append(m)
    rms_y.append(rms)
    sigm_y.append(sigm)
    bcx=(xed[:-1] + xed[1:])/2.
  plt.errorbar(bcx, mean_y, xerr=0., yerr=rms_y, fmt='bo')
  plt.errorbar(bcx, mean_y, xerr=0., yerr=sigm_y, fmt='k,',linewidth=2)
  return bcx, mean_y, rms_y, sigm_y
 
def chi2p_indep2d(H2d, bcx, bcy, pr=True):
  """
    perform a chi2-test on independence of x and y

    method: chi2-test on compatibility of 2d-distribution, f(x,y),
    with product of marginal distributions, f_x(x) * f_y(y)

    Args:
      * H2d: histogram array (as returned by histogram2d)
      * bcx: bin contents x (marginal distribution x)
      * bcy: bin contents y (marginal distribution y)

    Returns:
      * float: p-value w.r.t. assumption of independence
  """
  threshold=5. # minimum number of expected entries in a bin 
  Ntot=sum(bcx)
  chi2=0.
  ndf=0
  usedx=np.zeros(len(bcx))
  usedy=np.zeros(len(bcy))
  for ix in range(len(bcx)):
    for iy in range(len(bcy)):
      Nexp=bcx[ix]*bcy[iy]/Ntot
      if Nexp>threshold:
        usedx[ix]=1.
        usedy[iy]=1.
        ndf+=1.
        chi2+=((H2d[ix,iy]-Nexp)**2)/Nexp
  ndf-=(sum(usedx) + sum(usedy))
  # print 'chi2, ndf, npar =',chi2, ndf
  pval=1.- stats.chi2.cdf(chi2, ndf)
  if pr: 
    print('p-value of chi2-independence test: %.2g%%\n'%(pval*100.))
  return pval


## ------- section 5: linear regression ----------------------

def linRegression(x, y, sy):
  """
    linear regression y(x) = ax + b 

    method: 
      analytical formula

    Args:
      * x: np-array, independent data
      * y: np-array, dependent data
      * sy: scalar or np-array, uncertainty on y

    Returns:
      * float: a     slope
      * float: b     constant
      * float: sa  sigma on slope
      * float: sb  sigma on constant
      * float: cor   correlation
      * float: chi2  \chi-square
  """  
  # calculate auxilary quantities
  S1  = sum(1./sy**2)
  Sx  = sum(x/sy**2)
  Sy  = sum(y/sy**2)
  Sxx = sum(x**2/sy**2)
  Sxy = sum(x*y/sy**2)
  D = S1*Sxx-Sx**2

  # calculate results:
  a   = (S1*Sxy-Sx*Sy)/D # slope
  b   = (Sxx*Sy-Sx*Sxy)/D # constant
  sa  = np.sqrt(S1/D)
  sb  = np.sqrt(Sxx/D)
  cov   = -Sx/D
  cor  = cov/(sa*sb)
  chi2  = sum(((y-(a*x+b))/sy)**2)

  return a, b, sa, sb, cor, chi2


def linRegressionXY(x, y, sx, sy):
  """
    linear regression y(x) = ax + b  with errors on x and y
    uses numerical "orthogonal distance regression" from package scipy.odr

    Args:
      * x:  np-array, independent data
      * y:  np-array, dependent data
      * sx: scalar or np-array, uncertainty(ies) on x      
      * sy: scalar or np-array, uncertainty(ies) on y

    Returns:
      * float: a     slope
      * float: b     constant
      * float: sa    sigma on slope
      * float: sb    sigma on constant
      * float: cor   correlation
      * float: chi2  \chi-square
  """  
  from scipy import odr

  def fitf(P, x):     # the linear model (note order or parameters for odr !)
    return P[1]*x + P[0]

  # transform uncertainties to numpy-arrays, if necessary
  if not hasattr(sx,'__iter__'): sx=sx*np.ones(len(x))
  if not hasattr(sy,'__iter__'): sy=sy*np.ones(len(y))

  # get initial values for numerical optimisation from linear
  #   regression with analytical formula, ignoring x errors
  a0, b0, sa0, sb0, cor0, chi20 = linRegression(x, y, sy)

  # set up odr package:
  mod = odr.Model(fitf)
  dat = odr.RealData(x, y, sx, sy)
  odrfit = odr.ODR(dat, mod, beta0=[b0, a0])
  r = odr.ODR.run(odrfit)
  ndf = len(x)-2
  a, b, sa, sb = r.beta[1], r.beta[0],\
                 np.sqrt(r.cov_beta[1,1]), np.sqrt(r.cov_beta[0,0])
  cor = r.cov_beta[0,1]/(sa*sb) 
  chi2 = r.res_var*ndf
  
  return a, b, sa, sb, cor, chi2


def odFit(fitf, x, y, sx, sy, p0=None):
  """
    fit an arbitrary function with errors on x and y
    uses numerical "orthogonal distance regression" from package scipy.odr

    Args:
      * fitf: function to fit, arguments (array:P, float:x)
      * x:  np-array, independent data
      * y:  np-array, dependent data
      * sx: scalar or np-array, uncertainty(ies) on x      
      * sy: scalar or np-array, uncertainty(ies) on y
      * p0: none, scalar or array, initial guess of parameters

   Returns:
      * np-array of float: parameter values
      * np-array of float: parameter errors
      * np-array: cor   correlation matrix 
      * float: chi2  \chi-square
  """  
  from scipy.optimize import curve_fit
  from scipy import odr

  # define wrapper for fit function in ODR format
  def fitf_ODR(p, x):
    return fitf(x, *p)

  # transform uncertainties to numpy-arrays, if necessary
  if not hasattr(sx,'__iter__'): sx=sx*np.ones(len(x))
  if not hasattr(sy,'__iter__'): sy=sy*np.ones(len(y))

  # perform a simple fit with y-errors only to obtatain start values 
  par0, cov0 = curve_fit( fitf, x, y, sigma=sy, absolute_sigma=True, p0=p0 )
  #print '*==* result from curve fit:'
  #print ' -> par= ', par0
  #print ' -> pare= ', np.sqrt(np.diag(cov0))

  if(not np.sum(sx)):          # if no x-errors, we are done
    pare=np.sqrt(np.diag(cov0))
    cor = cov0/np.outer(pare,pare)
    chi2 = np.sum(((fitf(np.array(x), *par0) - y)/sy)**2)
    return par0, pare, cor, chi2
  else:  # use ODR package
    mod = odr.Model(fitf_ODR)
    dat = odr.RealData(x, y, sx, sy)
    odrfit = odr.ODR(dat, mod, beta0 = par0)
    r = odr.ODR.run(odrfit)
    par=r.beta
    cov=r.cov_beta
    pare=np.sqrt(np.diag(cov))
    cor = cov/np.outer(pare, pare) 
    ndf = len(x)-len(par)
    chi2 = r.res_var*ndf

    return par, pare, cor, chi2


def kRegression(x, y, sx, sy,
    xabscor=None, yabscor=None, xrelcor=None, yrelcor=None,
        title='Daten', axis_labels=['X', 'Y'], 
        plot=True, quiet=False):
  """
    linear regression y(x) = ax + b  with errors on x and y;
    uses package `kafe`

    Args:
      * x:  np-array, independent data
      * y:  np-array, dependent data

    the following are single floats or arrays of length of x
      * sx: scalar or np-array, uncertainty(ies) on x      
      * sy: scalar or np-array, uncertainty(ies) on y
      * xabscor: absolute, correlated error(s) on x
      * yabscor: absolute, correlated error(s) on y
      * xrelcor: relative, correlated error(s) on x
      * yrelcor: relative, correlated error(s) on y
      * title:   string, title of gaph
      * axis_labels: List of strings, axis labels x and y
      * plot: flag to switch off graphical ouput
      * quiet: flag to suppress text and log output

   Returns:
      * float: a     slope
      * float: b     constant
      * float: sa    sigma on slope
      * float: sb    sigma on constant
      * float: cor   correlation
      * float: chi2  \chi-square
  """  
  # regression with kafe
  import kafe
  from kafe.function_library import linear_2par

  # create a data set ...
  dat = kafe.Dataset(data=(x,y), title=title, axis_labels=axis_labels,
                       basename='kRegression') 
  # ... and add all error sources  
  dat.add_error_source('x', 'simple', sx)
  dat.add_error_source('y', 'simple', sy)
  if xabscor != None:
    dat.add_error_source('x', 'simple', xabscor, correlated=True)
  if yabscor != None:
    dat.add_error_source('y', 'simple', yabscor, correlated=True)
  if xrelcor != None:
    dat.add_error_source('x', 'simple', xrelcor, relative=True, correlated=True)
  if yrelcor != None:
    dat.add_error_source('y', 'simple', yrelcor, relative=True, correlated=True)
  # set up and run fit
  fit = kafe.Fit(dat, linear_2par) 
  fit.do_fit(quiet=quiet)                        

# harvest results
#  par, perr, cov, chi2 = fit.get_results() # for kafe vers. > 1.1.0
#  a = par[0]  
#  b = par[1]
#  sa = perr[0]
#  sb = perr[1]
#  cor = cov[1,0]/(sa*sb)
  a = fit.final_parameter_values[0]  
  b = fit.final_parameter_values[1]
  sa = fit.final_parameter_errors[0]
  sb = fit.final_parameter_errors[1]
  cor = fit.par_cov_mat[1,0]/(sa*sb)
  chi2 = fit.minimizer.get_fit_info('fcn') 

  if(plot):
    kplot=kafe.Plot(fit)
    kplot.plot_all()
    kplot.show()
    
  return a, b, sa, sb, cor, chi2  


def kFit(func, x, y, sx, sy, p0=None, p0e=None,
    xabscor=None, yabscor=None, xrelcor=None, yrelcor=None,
        title='Daten', axis_labels=['X', 'Y'], 
        plot=True, quiet=False):
  """
    fit function func with errors on x and y;
    uses package `kafe`

    Args:
      * func: function to fit
      * x:  np-array, independent data
      * y:  np-array, dependent data

    the following are single floats or arrays of length of x
      * sx: scalar or np-array, uncertainty(ies) on x      
      * sy: scalar or np-array, uncertainty(ies) on y
      * p0: array-like, initial guess of parameters
      * p0e: array-like, initial guess of parameter uncertainties
      * xabscor: absolute, correlated error(s) on x
      * yabscor: absolute, correlated error(s) on y
      * xrelcor: relative, correlated error(s) on x
      * yrelcor: relative, correlated error(s) on y
      * title:   string, title of gaph
      * axis_labels: List of strings, axis labels x and y
      * plot: flag to switch off graphical ouput
      * quiet: flag to suppress text and log output

   Returns:
      * np-array of float: parameter values
      * np-array of float: parameter errors
      * np-array: cor   correlation matrix 
      * float: chi2  \chi-square
  """  
  # regression with kafe
  import kafe

  # create a data set ...
  dat = kafe.Dataset(data=(x,y), title=title, axis_labels=axis_labels,
                       basename='kRegression') 
  # ... and add all error sources  
  dat.add_error_source('x','simple',sx)
  dat.add_error_source('y','simple',sy)
  if xabscor != None:
    dat.add_error_source('x','simple', xabscor, correlated=True)
  if yabscor != None:
    dat.add_error_source('y','simple', yabscor, correlated=True)
  if xrelcor != None:
    dat.add_error_source('x','simple', xrelcor, relative=True, correlated=True)
  if yrelcor != None:
    dat.add_error_source('y','simple', yrelcor, relative=True, correlated=True)
  # set up and run fit
  fit = kafe.Fit(dat, func) 
  if p0 is not None: fit.set_parameters(p0, p0e)
  fit.do_fit(quiet=quiet)                        

# harvest results
#  par, perr, cov, chi2 = fit.get_results() # for kafe vers. > 1.1.0
  par = np.array(fit.final_parameter_values) 
  pare = np.array(fit.final_parameter_errors)
  cor = fit.par_cov_mat/np.outer(pare, pare)
  chi2 = fit.minimizer.get_fit_info('fcn') 

  if(plot):
    kplot=kafe.Plot(fit)
    kplot.plot_all()
    kplot.show()
    
  return par, pare, cor, chi2

## ------- section 6: simulated data -------------------------

def smearData(d, s, srel=None, abscor=None, relcor=None):
  ''' Generate measurement data from "true" input d by
      adding random deviations according to the uncertainties 

    Args:
      * d:  np-array, (true) input data
    the following are single floats or arrays of length of array d
      * s: gaussian uncertainty(ies) (absolute)
      * srel: gaussian uncertainties (relative)
    the following are common (correlated) systematic uncertainties
      * abscor: absolute, correlated uncertainty
      * relcor: relative, correlated uncertainty
    Returns:
      * np-array of floats: dm, smeared (=measured) data    
  '''

  dm = d + s*np.random.randn(len(d)) # add independent (statistical) deviations
  if(srel): 
    dm += d*srel*np.random.randn(len(d)) # add relative  deviations
  if(abscor): 
    dm += abscor*np.random.randn(1) # add common absolute deviation
  if(relcor): 
    dm += d*relcor*np.random.randn(1) # add common relative  deviation
  return dm

def generateXYdata(xdata, model, sx, sy, mpar=None,
   srelx=None, srely=None,
   xabscor=None, yabscor=None, xrelcor=None, yrelcor=None):
  ''' Generate measurement data according to some model
    assumes xdata is measured within the given uncertainties; 
    the model function is evaluated at the assumed "true" values 
    xtrue, and a sample of simulated measurements is obtained by 
    adding random deviations according to the uncertainties given 
    as arguments.

    Args:
      * xdata:  np-array, x-data (independent data)
      * model: function that returns (true) model data (y-dat) for input x
      * mpar: list of parameters for model (if any)
    the following are single floats or arrays of length of x
      * sx: gaussian uncertainty(ies) on x      
      * sy: gaussian uncertainty(ies) on y
      * srelx: relative gaussian uncertainty(ies) on x      
      * srely: relative gaussian uncertainty(ies) on y
    the following are common (correlated) systematic uncertainties
      * xabscor: absolute, correlated error on x
      * yabscor: absolute, correlated error on y
      * xrelcor: relative, correlated error on x
      * yrelcor: relative, correlated error on y
    Returns:
      * np-arrays of floats: 

        * xtrue: true x-values
        * ytrue: true value = model(xtrue)
        * ydata:  simulated data  
  '''

  # first, add random statistical and systematic deviations on x
  xtrue = smearData(xdata, sx, srel=srelx, abscor=xabscor, relcor=xrelcor) 
     # take as "true" x

  #calculate model prediction for these:
  if mpar is not None:
   ytrue = model(xtrue, *mpar)
  else:
   ytrue = model(xtrue)

  # add uncertainties to y
  ydata = smearData(ytrue, sy, srel=srely, abscor=yabscor, relcor=yrelcor) 

  return xtrue, ytrue, ydata
