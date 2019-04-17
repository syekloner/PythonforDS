## ######################################################################### ##
## Analysis of 
## For EdX Course
## Python for Data Science (Week 9 and 10 Final Project)
## ######################################################################### ##

## Random Forest (scikit-learn)

## ========================================================================= ## 
## import libraries
## ========================================================================= ##

import requests
import io
import zipfile
import os
import urllib.parse
import re   ## for regular expressions
from itertools import chain  ## for chain, similar to R's unlist (flatten lists)
import collections   ## for Counters (used in frequency tables, for example)
import numpy as np
import pandas as pd
from pandas.api.types import CategoricalDtype  ## for sorted plotnine/ggplot categories
from plotnine import *
import matplotlib.pyplot as plt
import seaborn as sns  ## for correlation heatmap
#from mpl_toolkits.basemap import Basemap
import folium

## ========================================================================= ##
## modeling number of trips
## ========================================================================= ##

## using all data (as opposed to using only data with only non-zero trips):

import patsy ## for design matrices like R
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

import pathvalidate as pv

## ------------------------------------------------------------------------- ##
## define features and formula
## ------------------------------------------------------------------------- ##

## convert categorical variables to strings
## (in order for patsy to automatically dummy-code them without
## having to use the C() function):

# dat_hr_all['Month'] = dat_hr_all['Month'].astype('str')
# dat_hr_all['hr_of_day'] = dat_hr_all['hr_of_day'].astype('str')

## interesting:
## accuracy seems to be higher for non-categorical features!
## categorical     r^2 (train/test):  0.82382485701064379 / 0.79690027372546179
## non-categorical r^2 (train/test):  0.85217150610946379 / 0.82428144266270897

## also for weekday_name vs. weekday
## categorical     r^2 (train/test):  0.89759620156755338 / 0.87826354433724219
## non-categorical r^2 (train/test):  0.90785676507150148 / 0.89120320733183955

## define target and features:
target = 'trip_cnt'
features = ['Month',
            'Temp (°C)',
            # 'Dew Point Temp (°C)', ## -- exclude, because highly correlated with Temp
            'Rel Hum (%)',
            'Wind Dir (10s deg)',
            'Wind Spd (km/h)',
            'Stn Press (kPa)',
            'hr_of_day',
            'day_of_week']
list(dat_hr_all)

## add patsy-quoting to features (for weird column names):
target = 'Q(\'' + target + '\')' 
features = ['Q(\'' + i + '\')' for i in features]

## formula as text for patsy: without interactions
formula_txt = target + ' ~ ' + \
    ' + '.join(features) + ' - 1'
formula_txt

# ## try all twofold interactions, in order to 
# ## find important ones via variable importance plots:
# formula_txt = target + ' ~ (' + ' + '.join(features) + ') ** 2 - 1'
# formula_txt

## create design matrices using patsy (could directly be used for modeling):
#patsy.dmatrix?
dat_y, dat_x = patsy.dmatrices(formula_txt, dat_hr_all, 
                               NA_action = 'drop',
                               return_type = 'dataframe')
dat_x.head()

## other possibilities for dummy coding:
## * pd.get_dummies [[?]] which to use?

## ------------------------------------------------------------------------- ##
## train / test split
## ------------------------------------------------------------------------- ##

## Split the data into training/testing sets (using patsy/dmatrices):
dat_train_x, dat_test_x, dat_train_y, dat_test_y = train_test_split(
    dat_x, dat_y, test_size = 0.1, random_state = 142)

## convert y's to Series (to match data types between patsy and non-patsy data prep:)
dat_train_y = dat_train_y[target]
dat_test_y = dat_test_y[target]

## ------------------------------------------------------------------------- ##
## normalize data
## ------------------------------------------------------------------------- ##

## [[todo]]


## ------------------------------------------------------------------------- ##
## estimate model and evaluate fit and model assumptions
## ------------------------------------------------------------------------- ##

## Instantiate random forest estimator:
mod_rf = RandomForestRegressor(n_estimators = 500, 
                               random_state = 42,
                               max_depth = 20, 
                               min_samples_split = 50,
                               min_samples_leaf = 20,
                               oob_score = True,
                               n_jobs = -2,
                               verbose = 1)

## Train the model using the training sets:
mod_rf.fit(dat_train_x, dat_train_y)

## manual best (train/test r2): 
## 0.90785676507150148 / 0.89120320733183955 
## 0.91307831745877188 / 0.89403614532062348

## ------------------------------------------------------------------------- ##
## Randomized Search Cross-validation
## ------------------------------------------------------------------------- ##

## [[here]] [[todo]] 
## * different distributions to sample from? (double values, log scale?)
##   (more reserach needed here)

# specify parameters and distributions to sample from:
param_distributions = { 
    "n_estimators" : stats.randint(300, 700),
    "max_depth" : stats.randint(10, 31),
    #"min_samples_split" : stats.randint(40, 101),
    "min_samples_leaf" : stats.randint(20, 51)
}

#stats.randint(1, 4).rvs(20)

n_iter = 40
mod_randsearch = RandomizedSearchCV(
    estimator = mod_rf,
    param_distributions = param_distributions,
    n_iter = n_iter,
    scoring = "r2", ## "roc_auc", # "neg_mean_squared_error", "neg_mean_absolute_error"
    cv = 4,   ## k-fold cross-validation for binary classification
    verbose = 2,
    random_state = 7,
    n_jobs = -1)
mod_randsearch.fit(dat_train_x, dat_train_y)
## time: about 20 min for 40 iterations

## best parameters and score in CV:
mod_randsearch.best_params_
mod_randsearch.best_score_

## get best model (estimator): 
mod_rf = mod_randsearch.best_estimator_

## ------------------------------------------------------------------------- ##
## use and inspect model
## ------------------------------------------------------------------------- ##

## [[?]] missing: how to plot oob error by number of trees, like in R?
    
## Make predictions using the testing set
dat_test_pred = mod_rf.predict(dat_test_x)
dat_train_pred = mod_rf.predict(dat_train_x)

## Inspect model:
mean_squared_error(dat_train_y, dat_train_pred)  # MSE in training set
mean_squared_error(dat_test_y, dat_test_pred)    # MSE in test set
r2_score(dat_train_y, dat_train_pred)            # R^2 (r squared) in test set
r2_score(dat_test_y, dat_test_pred)              # R^2 (r squared) in test set

## ------------------------------------------------------------------------- ##
## save model to disk
## ------------------------------------------------------------------------- ##

## [[?]] who to persist models?
## * don't use pickle or joblib (unsafe and not persistent)
##   see https://pyvideo.org/pycon-us-2014/pickles-are-for-delis-not-software.html or
##   http://scikit-learn.org/stable/modules/model_persistence.html
##   (3.4.2. Security & maintainability limitations)

from sklearn.externals import joblib

# filename_model = 'model_random_forest_interactions.pkl'
filename_model = 'model_random_forest.pkl'
joblib.dump(mod_rf, os.path.join(path_out, filename_model))

# ## load:
# filename_model = 'model_random_forest.pkl'
# mod_rf = joblib.load(os.path.join(path_out, filename_model))



"""
print(var_imp[['varname', 'importance']].head(n = 15))

                                  varname  importance
19          Q('Temp (°C)'):Q('hr_of_day')    0.548121
33    Q('Stn Press (kPa)'):Q('hr_of_day')    0.171389
18    Q('Temp (°C)'):Q('Stn Press (kPa)')    0.090000
8               Q('Month'):Q('Temp (°C)')    0.028317
35        Q('hr_of_day'):Q('day_of_week')    0.025828
23  Q('Rel Hum (%)'):Q('Stn Press (kPa)')    0.022665
6                  Hour of the Day (0-23)    0.018860
12        Q('Month'):Q('Stn Press (kPa)')    0.018096
34  Q('Stn Press (kPa)'):Q('day_of_week')    0.013438
24        Q('Rel Hum (%)'):Q('hr_of_day')    0.010271
25      Q('Rel Hum (%)'):Q('day_of_week')    0.009835
2                   Relative Humidity (%)    0.007337
20        Q('Temp (°C)'):Q('day_of_week')    0.006104
7                   Day of the Week (0-6)    0.005593
13              Q('Month'):Q('hr_of_day')    0.004156
"""