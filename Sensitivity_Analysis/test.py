#%% imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython import get_ipython

ipython = get_ipython()
if ipython is not None:
    ipython.run_line_magic("matplotlib", "widget")

pi = np.pi

#%% read file

df = pd.read_parquet("results/spray_timeseriesdf.parquet")

#%% plotting

plt.figure()
plt.plot(df['t'], df['u'])
plt.minorticks_on()
plt.grid(which='major', color='#dbdada', linestyle='-', lw=0.7)
plt.grid(which='minor', color='#dbdada', linestyle=':', lw=0.5)

