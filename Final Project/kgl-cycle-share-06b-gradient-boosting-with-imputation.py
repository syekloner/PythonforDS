## ######################################################################### ##
## Analysis of 
## For EdX Course
## Python for Data Science (Week 9 and 10 Final Project)
## ######################################################################### ##

## Gradient Boosting (scikit-learn)

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
from scipy import stats
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
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score

import pathvalidate as pv

from fancyimpute import KNN, NuclearNormMinimization, SoftImpute, IterativeImputer, BiScaler

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
                               #NA_action = 'drop',
                               NA_action=patsy.NAAction(NA_types=[]),
                               return_type = 'dataframe')
#dat_x.head()
#dat_x.shape

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

#dat_test_x.shape
#dat_train_x.shape
#dat_x.shape

## ------------------------------------------------------------------------- ##
## normalize data
## ------------------------------------------------------------------------- ##

## [[todo]]

## ------------------------------------------------------------------------- ##
## impute missing values
## ------------------------------------------------------------------------- ##

## training data:
dat_train_x.isnull().any()
dat_train_x.apply(lambda x: x.isnull().sum(), axis = 0)

## all data: number of missing values (absolute and percent):
dat_x.apply(lambda x: x.isnull().sum(), axis = 0)
dat_x.apply(lambda x: x.isnull().sum() / dat_x.shape[0], axis = 0)

#from fancyimpute import KNN, NuclearNormMinimization, SoftImpute, IterativeImputer, BiScaler

## iterative imputation:
## [[?]] probably only works for continuous variables only...
mod_impute = IterativeImputer(imputation_order = "ascending",
                             n_iter = 10,
                             #predictor = sklearn.linear.RidgeCV(), ## default
                             random_state = 21)

## fit on training data:
mod_impute.fit(dat_train_x)

## impute training data:
dat_train_x_nparray = mod_impute.transform(dat_train_x)
#type(dat_train_x_nparray)  ## numpy.ndarray (!)

## transform back into a pandas dataframe:
dat_train_x = pd.DataFrame(data =    dat_train_x_nparray,
                           index =   dat_train_x.index,
                           columns = dat_train_x.columns)


## impute test data:
dat_test_x_nparray = mod_impute.transform(dat_test_x)
#type(dat_train_x_nparray)  ## numpy.ndarray (!)

## transform back into a pandas dataframe:
dat_test_x = pd.DataFrame(data =    dat_test_x_nparray,
                          index =   dat_test_x.index,
                          columns = dat_test_x.columns)


## impute complete dataset:
dat_x_nparray = mod_impute.transform(dat_x)
#type(dat_train_x_nparray)  ## numpy.ndarray (!)

## transform back into a pandas dataframe:
dat_x = pd.DataFrame(data =    dat_x_nparray,
                     index =   dat_x.index,
                     columns = dat_x.columns)

## ------------------------------------------------------------------------- ##
## estimate model and evaluate fit and model assumptions
## ------------------------------------------------------------------------- ##

## Instantiate random forest estimator:
mod_gb = GradientBoostingRegressor(n_estimators = 100, 
                                   random_state = 42,
                                   loss = 'ls',
                                   learning_rate = 0.1,
                                   max_depth = 20, 
                                   min_samples_split = 70,
                                   min_samples_leaf = 30,
                                   verbose = 1)

## Train the model using the training sets:
mod_gb.fit(dat_train_x, dat_train_y)

## ------------------------------------------------------------------------- ##
## Randomized Search Cross-validation
## ------------------------------------------------------------------------- ##

## [[here]] [[todo]] 
## * different distributions to sample from? (double values, log scale?)
##   (more reserach needed here)

# specify parameters and distributions to sample from:
param_distributions = { 
    "n_estimators" : stats.randint(50, 201),
    "learning_rate" : [0.2, 0.1, 0.05], # stats.uniform(0.05, 0.2 - 0.05),
    "max_depth" : stats.randint(4, 21),
    #"min_samples_split" : stats.randint(40, 101),
    "min_samples_leaf" : stats.randint(30, 61)
}

#stats.randint(1, 4).rvs(20)

n_iter = 40
mod_randsearch = RandomizedSearchCV(
    estimator = mod_gb,
    param_distributions = param_distributions,
    n_iter = n_iter,
    scoring = "r2", ## "roc_auc", # "neg_mean_squared_error", "neg_mean_absolute_error"
    cv = 4,   ## k-fold cross-validation for binary classification
    verbose = 2,
    random_state = 7,
    n_jobs = -1)
mod_randsearch.fit(dat_train_x, dat_train_y)

## best parameters and score in CV:
mod_randsearch.best_params_
mod_randsearch.best_score_

## get best model (estimator): 
mod_gb = mod_randsearch.best_estimator_

## ------------------------------------------------------------------------- ##
## use and inspect model
## ------------------------------------------------------------------------- ##

## Make predictions using the testing set
dat_test_pred = mod_gb.predict(dat_test_x)
dat_train_pred = mod_gb.predict(dat_train_x)

## Inspect model:
mean_squared_error(dat_train_y, dat_train_pred)  # MSE in training set
mean_squared_error(dat_test_y, dat_test_pred)    # MSE in test set
mean_absolute_error(dat_train_y, dat_train_pred)  # MSE in training set
mean_absolute_error(dat_test_y, dat_test_pred)    # MSE in test set
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

# filename_model = 'model_gradient_boosting_interactions.pkl'
# filename_model = 'model_gradient_boosting.pkl'
filename_model = 'model_gradient_boosting_imputed.pkl'
joblib.dump(mod_gb, os.path.join(path_out, filename_model))

# ## load:
# filename_model = 'model_gradient_boosting.pkl'
# mod_this = joblib.load(os.path.join(path_out, filename_model))



## Notes:
## most important interactions (17 Oct 2018, 12:45):
"""
                                   varname  importance
19           Q('Temp (°C)'):Q('hr_of_day')    0.158654
33     Q('Stn Press (kPa)'):Q('hr_of_day')    0.093486
12         Q('Month'):Q('Stn Press (kPa)')    0.066666
15         Q('Temp (°C)'):Q('Rel Hum (%)')    0.052042
18     Q('Temp (°C)'):Q('Stn Press (kPa)')    0.043930
34   Q('Stn Press (kPa)'):Q('day_of_week')    0.043399
8                Q('Month'):Q('Temp (°C)')    0.043129
5               Atmospheric Pressure (kPa)    0.043117
20         Q('Temp (°C)'):Q('day_of_week')    0.042098
23   Q('Rel Hum (%)'):Q('Stn Press (kPa)')    0.031272
16  Q('Temp (°C)'):Q('Wind Dir (10s deg)')    0.030179
17     Q('Temp (°C)'):Q('Wind Spd (km/h)')    0.028586
24         Q('Rel Hum (%)'):Q('hr_of_day')    0.027554
9              Q('Month'):Q('Rel Hum (%)')    0.025869
25       Q('Rel Hum (%)'):Q('day_of_week')    0.023910

[
["Q('Temp (°C)')", "Q('hr_of_day')"], 
["Q('Stn Press (kPa)')", "Q('hr_of_day')"], 
["Q('Month')", "Q('Stn Press (kPa)')"], 
["Q('Temp (°C)')", "Q('Rel Hum (%)')"], 
["Q('Temp (°C)')", "Q('Stn Press (kPa)')"], 
["Q('Stn Press (kPa)')", "Q('day_of_week')"], 
["Q('Month')", "Q('Temp (°C)')"], 
["Atmospheric Pressure (kPa)"], 
["Q('Temp (°C)')", "Q('day_of_week')"], 
["Q('Rel Hum (%)')", "Q('Stn Press (kPa)')"], 
["Q('Temp (°C)')", "Q('Wind Dir (10s deg)')"], 
["Q('Temp (°C)')", "Q('Wind Spd (km/h)')"], 
["Q('Rel Hum (%)')", "Q('hr_of_day')"], 
["Q('Month')", "Q('Rel Hum (%)')"], 
["Q('Rel Hum (%)')", "Q('day_of_week')"]
]
"""
