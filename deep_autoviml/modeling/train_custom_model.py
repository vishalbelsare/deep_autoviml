############################################################################################
#Copyright 2021 Google LLC

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
############################################################################################
import pandas as pd
import numpy as np
pd.set_option('display.max_columns',500)
import matplotlib.pyplot as plt
import tempfile
import pdb
import copy
import warnings
warnings.filterwarnings(action='ignore')
import functools
# Make numpy values easier to read.
np.set_printoptions(precision=3, suppress=True)
############################################################################################
# TensorFlow ≥2.4 is required
import tensorflow as tf
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
def set_seed(seed=31415):
    np.random.seed(seed)
    tf.random.set_seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    os.environ['TF_DETERMINISTIC_OPS'] = '1'
from tensorflow.keras import layers
from tensorflow import keras
from tensorflow.keras.layers.experimental.preprocessing import Normalization, StringLookup
from tensorflow.keras.layers.experimental.preprocessing import IntegerLookup, CategoryEncoding
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization, Discretization, Hashing
from tensorflow.keras.layers import Embedding, Reshape, Dropout, Dense, GaussianNoise

from tensorflow.keras.optimizers import SGD, Adam, RMSprop
from tensorflow.keras import layers
from tensorflow.keras import optimizers
from tensorflow.keras.models import Model, load_model
from tensorflow.keras import callbacks
from tensorflow.keras import backend as K
from tensorflow.keras import utils
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.optimizers import SGD
from tensorflow.keras import regularizers
from tensorflow.keras.layers import LeakyReLU
#####################################################################################
from deep_autoviml.modeling.create_model import return_optimizer
from deep_autoviml.utilities.utilities import get_model_defaults, get_compiled_model

# Utils
from deep_autoviml.utilities.utilities import print_one_row_from_tf_dataset, print_one_row_from_tf_label
from deep_autoviml.utilities.utilities import print_classification_metrics, print_regression_model_stats
from deep_autoviml.utilities.utilities import plot_regression_residuals
from deep_autoviml.utilities.utilities import print_classification_model_stats, plot_history, plot_classification_results
from deep_autoviml.utilities.utilities import add_outputs_to_model_body
from deep_autoviml.utilities.utilities import add_outputs_to_auto_model_body
from deep_autoviml.utilities.utilities import check_if_GPU_exists, get_chosen_callback
from deep_autoviml.utilities.utilities import save_valid_predictions, get_callbacks
from deep_autoviml.utilities.utilities import print_classification_header
from deep_autoviml.utilities.utilities import check_keras_options
from deep_autoviml.utilities.utilities import save_model_artifacts, save_model_architecture

from deep_autoviml.data_load.extract import find_batch_size
from deep_autoviml.modeling.one_cycle import OneCycleScheduler
#####################################################################################
from sklearn.metrics import roc_auc_score, mean_squared_error, mean_absolute_error
from IPython.core.display import Image, display
import pickle
#############################################################################################
##### Suppress all TF2 and TF1.x warnings ###################
tf2logger = tf.get_logger()
tf2logger.warning('Silencing TF2.x warnings')
tf2logger.root.removeHandler(tf2logger.root.handlers)
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
############################################################################################
from tensorflow.keras.layers import Reshape, MaxPooling1D, MaxPooling2D, AveragePooling2D, AveragePooling1D
from tensorflow.keras import Model, Sequential
from tensorflow.keras.layers import Activation, Dense, Embedding, GlobalAveragePooling1D, GlobalMaxPooling1D, Dropout, Conv1D
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization
############################################################################################
#### probably the most handy function of all!
def left_subtract(l1,l2):
    lst = []
    for i in l1:
        if i not in l2:
            lst.append(i)
    return lst
##############################################################################################
import time
import os
import math

from sklearn.metrics import balanced_accuracy_score, classification_report
from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score
from collections import defaultdict
from tensorflow.keras import callbacks
#########################################################################################
### This is the Storm-Tuner which stands for Stochastic Random Mutator tuner
###  More details can be found in this github: https://github.com/ben-arnao/stochasticmutatortuner
###   You can also pip install storm-tuner --upgrade to get the latest version ##########
#########################################################################################
from storm_tuner import Tuner
#########################################################################################
### Split raw_train_set into train and valid data sets first
### This is a better way to split a dataset into train and test ####
### It does not assume a pre-defined size for the data set.
def is_valid(x, y):
    return x % 5 == 0
def is_test(x, y):
    return x % 2 == 0
def is_train(x, y):
    return not is_test(x, y)
##################################################################################
# Reset Keras Session
def reset_keras():
    sess = get_session()
    K.clear_session()
    sess.close()
    sess = get_session()

    try:
        del opt_model  ### delete this if it exists
        del best_model # this is from global space - change this as you need
        del deep_model  ### delete this if it exists
        print('deleted deep and best models from memory')
    except:
        pass

    print(gc.collect()) # if it does something you should see a number as output

    # use the same config as you used to create the session
    config = tf.compat.v1.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = 1
    config.gpu_options.visible_device_list = "0"
    set_session(tf.compat.v1.Session(config=config))
##################################################################################
def build_model_optuna(trial, inputs, meta_outputs, output_activation, num_predicts, modeltype,
                        optimizer_options, loss_fn, val_metrics, cols_len, targets, nlp_flag, regular_body):

    #tf.compat.v1.reset_default_graph()
    #K.clear_session()
    #reset_keras()
    #tf.keras.backend.reset_uids()
    ### Keep the number of layers slightly higher to increase model complexity ##
    n_layers = trial.suggest_int("n_layers", 2, 8)
    #num_hidden = trial.suggest_categorical("n_units", [32, 48, 64, 96, 128])
    num_hidden = trial.suggest_categorical("n_units", [50, 100, 150, 200, 250, 300, 350, 400, 450, 500])
    weight_decay = trial.suggest_float("weight_decay", 1e-8, 1e-3, log=True)
    use_bias = trial.suggest_categorical("use_bias", [True, False])
    batch_norm = trial.suggest_categorical("batch_norm", [True, False])
    add_noise = trial.suggest_categorical("add_noise", [True, False])
    dropout = trial.suggest_float("dropout", 0.5, 0.9)
    activation_fn = trial.suggest_categorical("activation", ['relu', 'elu', 'selu'])
    kernel_initializer = trial.suggest_categorical("kernel_initializer",
                                 ['glorot_uniform','he_normal','lecun_normal','he_uniform'])
    kernel_size = num_hidden
    model = tf.keras.Sequential()

    for i in range(n_layers):
        kernel_size =  int(kernel_size*0.80)

        model.add(
            tf.keras.layers.Dense(
                kernel_size,
                name="opt_dense_"+str(i), use_bias=use_bias,
                kernel_initializer=kernel_initializer,
                #kernel_regularizer=tf.keras.regularizers.l2(weight_decay),
            )
        )
        model.add(Activation(activation_fn,name="opt_activation_"+str(i)))

        if batch_norm:
            model.add(BatchNormalization(name="opt_batchnorm_"+str(i)))

        if add_noise:
            model.add(GaussianNoise(trial.suggest_float("adam_learning_rate", 1e-7, 1e-3, log=True)))

        model.add(Dropout(dropout, name="opt_drop_"+str(i)))

    #### Now we add the final layers to the model #########
    kwargs = {}
    if isinstance(optimizer_options,str):
        if optimizer_options == "":
            optimizer_options = ["Adam", "SGD"]
            optimizer_selected = trial.suggest_categorical("optimizer", optimizer_options)
        else:
            optimizer_selected = optimizer_options
    else:
        optimizer_selected = trial.suggest_categorical("optimizer", optimizer_options)
    if optimizer_selected == "Adam":
        kwargs["learning_rate"] = trial.suggest_float("adam_learning_rate", 1e-7, 1e-3, log=True)
        kwargs["epsilon"] = trial.suggest_float(
            "adam_epsilon", 1e-14, 1e-4, log=True
        )
    elif optimizer_selected == "SGD":
        kwargs["learning_rate"] = trial.suggest_float(
            "sgd_opt_learning_rate", 1e-7, 1e-3, log=True
        )
        kwargs["momentum"] = trial.suggest_float("sgd_opt_momentum", 0.8, 0.95)

    optimizer = getattr(tf.optimizers, optimizer_selected)(**kwargs)
    ##### This is the simplest way to convert a sequential model to functional!
    if regular_body:
        opt_outputs = add_outputs_to_model_body(model, meta_outputs)
    else:
        opt_outputs = add_outputs_to_auto_model_body(model, meta_outputs, nlp_flag)

    comp_model = get_compiled_model(inputs, opt_outputs, output_activation, num_predicts,
                        modeltype, optimizer, loss_fn, val_metrics, cols_len, targets)

    return comp_model

###############################################################################
def build_model_storm(hp, *args):
    #### Before every sequential model definition you need to clear the Keras backend ##
    keras.backend.clear_session()
    
    ######  we need to use the batch_size in a few small sizes ####
    if len(args) == 2:
        batch_limit, batch_nums = args[0], args[1]
        batch_size = hp.Param('batch_size', [32, 64, 128, 256, 512, 1024, 2048],
                 ordered=True)
    elif len(args) == 1:
        batch_size = args[0]
        batch_size = hp.Param('batch_size', [batch_size])
    else:
        batch_size = hp.Param('batch_size', [32, 64, 128, 256, 512, 1024, 2048])

    num_layers = hp.Param('num_layers', [1, 2, 3], ordered=True)
    ##### Now let us build the model body ###############
    model_body = Sequential([])

    # example of model-wide unordered categorical parameter
    activation_fn = hp.Param('activation', ['relu', 'selu', 'elu'])
    use_bias = hp.Param('use_bias', [True, False])
    weight_decay = hp.Param("weight_decay", np.logspace(-8, -3, 10))
    #weight_decay = hp.Param("weight_decay", [1e-8, 1e-7,1e-6, 1e-5,1e-4])

    batch_norm = hp.Param("batch_norm", [True, False])
    kernel_initializer = hp.Param("kernel_initializer",
                        ['glorot_uniform','he_normal','lecun_normal','he_uniform'], ordered=False)
    dropout_flag = hp.Param('use_dropout', [True, False])
    batch_norm_flag = hp.Param('use_batch_norm', [True, False])

    # example of per-block parameter
    num_hidden = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]

    model_body.add(Dense(hp.Param('kernel_size_' + str(0),
                            num_hidden, ordered=True),
                            use_bias=use_bias,
                            kernel_initializer = kernel_initializer,
                            name="storm_dense_0",
                            #kernel_regularizer=keras.regularizers.l2(weight_decay)
                            ))

    model_body.add(Activation(activation_fn,name="activation_0"))

    # example of boolean param
    if batch_norm_flag:
        model_body.add(BatchNormalization(name="batch_norm_0"))

    if dropout_flag:
        # example of nested param
        #
        # this param will not affect the configuration hash, if this block of code isn't executed
        # this is to ensure we do not test configurations that are functionally the same
        # but have different values for unused parameters
        model_body.add(Dropout(hp.Param('dropout_value', [0.5, 0.6, 0.7, 0.8, 0.9], ordered=True),
                                        name="dropout_0"))

    kernel_size =  hp.values['kernel_size_' + str(0)]
    if dropout_flag:
        dropout_value = hp.values['dropout_value']
    else:
        dropout_value =  0.5
    batch_norm_flag = hp.values['use_batch_norm']
    # example of inline ordered parameter
    num_copy = copy.deepcopy(num_layers)
    
    for x in range(num_copy):
        #### slowly reduce the kernel size after each round ####
        kernel_size = int(0.75*kernel_size)
        # example of per-block parameter
        model_body.add(Dense(kernel_size, name="storm_dense_"+str(x+1),
                            use_bias=use_bias,
                            kernel_initializer = kernel_initializer,
                            #kernel_regularizer=keras.regularizers.l2(weight_decay)
                            ))

        model_body.add(Activation(activation_fn, name="activation_"+str(x+100)))

        # example of boolean param
        if batch_norm_flag:
            model_body.add(BatchNormalization(name="batch_norm_"+str(x+1)))

        if dropout_flag:
            # example of nested param
            # this param will not affect the configuration hash, if this block of code isn't executed
            # this is to ensure we do not test configurations that are functionally the same
            # but have different values for unused parameters
            model_body.add(Dropout(dropout_value, name="dropout_"+str(x+1)))

    selected_optimizer = hp.Param('optimizer', ["Adam", "AdaMax", "Adagrad", "SGD", "RMSprop", "Nadam", 'nesterov'],
                                  ordered=False)
    
    optimizer = return_optimizer_trials(hp, selected_optimizer)
    
    return model_body, optimizer

############################################################################################
class MyTuner(Tuner):

    def run_trial(self, trial, *args):
        hp = trial.hyperparameters
        #### Before every sequential model definition you need to clear the Keras backend ##
        keras.backend.clear_session()

        ##########    E N D    O F    S T R A T E G Y    S C O P E   #############
        train_ds, valid_ds = args[0], args[1]
        epochs, steps =  args[2], args[3]
        inputs, meta_outputs = args[4], args[5]
        cols_len, output_activation = args[6], args[7]
        num_predicts, modeltype = args[8], args[9]
        optimizer, val_loss =  args[10], args[11]
        val_metrics, patience = args[12], args[13]
        val_mode, DS_LEN = args[14], args[15]
        learning_rate, val_monitor = args[16], args[17]
        callbacks_list, modeltype = args[18], args[19]
        class_weights, batch_size =  args[20], args[21]
        batch_limit, batch_nums =  args[22], args[23]
        targets, nlp_flag, regular_body = args[24], args[25], args[26]
        project_name, keras_model_type,  = args[27], args[28]
        cat_vocab_dict, model_options = args[29], args[30]

        model_body, optimizer = build_model_storm(hp, batch_limit, batch_nums)
     
        ##### This is the simplest way to convert a sequential model to functional model!
        if regular_body:
            storm_outputs = add_outputs_to_model_body(model_body, meta_outputs)
        else:
            storm_outputs = add_outputs_to_auto_model_body(model_body, meta_outputs, nlp_flag)

        #### This final outputs is the one that is taken into final dense layer and compiled
        #print('    Custom model loaded successfully. Now compiling model...')

        ###### This is where you compile the model after it is built ###############
        #### Add a final layer for outputs during compiled model phase #############
        
        comp_model = get_compiled_model(inputs, storm_outputs, output_activation, num_predicts,
                            modeltype, optimizer, val_loss, val_metrics, cols_len, targets)
        
        #opt = comp_model.optimizer
        #for var in opt.variables():
        #    var.assign(tf.zeros_like(var))
        if len(self.trials) == 0:
            ### Just save it once. Don't save it again and again.
            save_model_architecture(comp_model, project_name, keras_model_type, cat_vocab_dict,
                model_options, chart_name="model_before")
        #print('    Custom model compiled successfully. Training model next...')
        batch_numbers = [32, 64, 128, 256, 512, 1024, 2048, 4096]
        shuffle_size = 1000
        batch_sizes = batch_numbers[:batch_nums]
        #print('storm batch sizes = %s' %batch_sizes)
        batch_size = np.random.choice(batch_sizes)
        #print('    selected batch size = %s' %batch_size)
        train_ds = train_ds.unbatch().batch(batch_size)
        train_ds = train_ds.shuffle(shuffle_size,
                        reshuffle_each_iteration=False, seed=42).prefetch(batch_size)#.repeat(5)
        valid_ds = valid_ds.unbatch().batch(batch_size)
        valid_ds = valid_ds.prefetch(batch_size)#.repeat(5)
        steps = 20
        storm_epochs = 5
        
        history = comp_model.fit(train_ds, epochs=storm_epochs, #steps_per_epoch=steps,# batch_size=batch_size,
                            validation_data=valid_ds, #validation_steps=steps,
                            callbacks=callbacks_list, shuffle=True, class_weight=class_weights,
                            verbose=0)
        # here we can define custom logic to assign a score to a configuration
        if len(targets) == 1:
            score = np.mean(history.history[val_monitor][-5:])
        else:
            for i in range(len(targets)):
                ### the next line uses the list of metrics to find one that is a closest match
                metric1 = [x for x in history.history.keys() if (targets[i] in x) & ("loss" not in x) ]
                val_metric = metric1[0]
                if i == 0:
                    results = history.history[val_metric][-5:]
                else:
                    results = np.c_[results,history.history[val_metric][-5:]]
            score = results.mean(axis=1).mean()
            #scores.append(score)
        ##### This is where we capture the best learning rate from the optimizer chosen ######
        model_lr = comp_model.optimizer.learning_rate.numpy()
        #self.user_var = model_lr
        print('    found best learning rate = %s' %model_lr)
        trial.metrics['final_lr'] = model_lr
        #print('    trial final_lr = %s' %trial.metrics['final_lr'])
        self.score_trial(trial, score)
        #self.score_trial(trial, min(scores))
#####################################################################################
def return_optimizer_trials(hp, hpq_optimizer):
    """
    This returns the keras optimizer with proper inputs if you send the string.
    hpq_optimizer: input string that stands for an optimizer such as "Adam", etc.
    """
    ##### These are the various optimizers we use ################################
    momentum = keras.optimizers.SGD(learning_rate=0.001, momentum=0.9)
    nesterov = keras.optimizers.SGD(learning_rate=0.001, momentum=0.9, nesterov=True)
    adagrad = keras.optimizers.Adagrad(learning_rate=0.001)
    rmsprop = keras.optimizers.RMSprop(learning_rate=0.001, rho=0.9)
    adam = keras.optimizers.Adam(learning_rate=0.001, beta_1=0.9, beta_2=0.999)
    adamax = keras.optimizers.Adamax(learning_rate=0.001, beta_1=0.9, beta_2=0.999)
    nadam = keras.optimizers.Nadam(learning_rate=0.001, beta_1=0.9, beta_2=0.999)
    best_optimizer = ''
    #############################################################################
    lr_list = [1e-2, 1e-3, 1e-4]
    if hpq_optimizer.lower() in ['adam']:
        best_optimizer = tf.keras.optimizers.Adam(learning_rate=hp.Param('init_lr', lr_list),
            epsilon=hp.Param('epsilon', [1e-6, 1e-8, 1e-10, 1e-12, 1e-14], ordered=True))
    elif hpq_optimizer.lower() in ['sgd']:
        best_optimizer = keras.optimizers.SGD(lr=hp.Param('init_lr', lr_list),
                             momentum=0.9)
    elif hpq_optimizer.lower() in ['nadam']:
        best_optimizer = keras.optimizers.Nadam(learning_rate=hp.Param('init_lr', lr_list),
                         beta_1=0.9, beta_2=0.999)
    elif hpq_optimizer.lower() in ['adamax']:
        best_optimizer = keras.optimizers.Adamax(learning_rate=hp.Param('init_lr', lr_list),
                         beta_1=0.9, beta_2=0.999)
    elif hpq_optimizer.lower() in ['adagrad']:
        best_optimizer = keras.optimizers.Adagrad(learning_rate=hp.Param('init_lr', lr_list))
    elif hpq_optimizer.lower() in ['rmsprop']:
        best_optimizer = keras.optimizers.RMSprop(learning_rate=hp.Param('init_lr', lr_list),
                         rho=0.9)
    elif hpq_optimizer.lower() in ['nesterov']:
        best_optimizer = keras.optimizers.SGD(learning_rate=0.001, momentum=0.9, nesterov=True)
    else:
        best_optimizer = keras.optimizers.SGD(learning_rate=0.001, momentum=0.9)
    
    return best_optimizer
#####################################################################################
from tensorflow.keras import backend as K
import tensorflow
import gc
from tensorflow.python.keras.backend import get_session, set_session
import tensorflow as tf

##########################################################################################
import optuna
def train_custom_model(nlp_inputs, meta_inputs, meta_outputs, nlp_outputs, full_ds, target,
                    keras_model_type, keras_options, model_options, var_df, cat_vocab_dict,
                    project_name="", save_model_flag=True, use_my_model='', verbose=0 ):
    """
    Given a keras model and a tf.data.dataset that is batched, this function will
    train a keras model. It will first split the batched_data into train_ds and
    valid_ds (80/20). Then it will select the right parameters based on model type and
    train the model and evaluate it on valid_ds. It will return a keras model fully
    trained on the full batched_data finally and train history.
    """
    save_model_path = model_options['save_model_path']
    inputs = nlp_inputs + meta_inputs
    nlps = var_df["nlp_vars"]
    lats = var_df["lat_vars"]
    lons = var_df["lon_vars"]
    if nlp_inputs:
        nlp_flag = True
    else:
        nlp_flag = False
    start_time = time.time()
    ########################   STORM TUNER and other DEFAULTS     ####################
    targets = cat_vocab_dict['target_variables']
    max_trials = model_options["max_trials"]
    overwrite_flag = True ### This overwrites the trials so every time it runs it is new
    data_size = check_keras_options(keras_options, 'data_size', 10000)
    batch_size = check_keras_options(keras_options, 'batchsize', 64)
    class_weights = check_keras_options(keras_options, 'class_weight', {})
    if not isinstance(model_options["label_encode_flag"], str):
        if not model_options["label_encode_flag"]:
            print('    removing class weights since label_encode_flag is set to False which means classes can be anything.')
            class_weights = {}
    print('    Class weights: %s' %class_weights)
    num_classes = model_options["num_classes"]
    num_labels = model_options["num_labels"]
    modeltype = model_options["modeltype"]
    patience = keras_options["patience"]
    cols_len = len([item for sublist in list(var_df.values()) for item in sublist])
    if isinstance(meta_outputs, list):
        data_dim = int(data_size)
        NON_NLP_VARS = []
    else:
        NON_NLP_VARS = left_subtract(cat_vocab_dict["predictors_in_train"], nlps)
        try:
            data_dim = int(data_size*meta_outputs.shape[1])
        except:
            data_dim = int(data_size*(meta_outputs[0].shape[1]))
    optimizer = keras_options['optimizer']
    early_stopping = check_keras_options(keras_options, "early_stopping", False)
    print('    original datasize = %s, initial batchsize = %s' %(data_size, batch_size))
    print("    Early stopping : %s" %early_stopping)
    NUMBER_OF_EPOCHS = check_keras_options(keras_options, "epochs", 100)
    if keras_options['lr_scheduler'] in ['expo', 'ExponentialDecay', 'exponentialdecay']:
        print('    chosen ExponentialDecay learning rate scheduler')
        expo_steps = (NUMBER_OF_EPOCHS*data_size)//batch_size
        learning_rate = keras.optimizers.schedules.ExponentialDecay(0.0001, expo_steps, 0.1)
    else:
        learning_rate = check_keras_options(keras_options, "learning_rate", 5e-2)
    #### The steps are actually not needed but remove them later.###
    if len(var_df['nlp_vars']) > 0:
        steps = 10
    else:
        steps = max(10, (data_size//(batch_size*2)))
        steps = min(300, steps)
    print('    recommended steps per epoch = %d' %steps)
    STEPS_PER_EPOCH = check_keras_options(keras_options, "steps_per_epoch",
                        steps)
    #### These can be standard for every keras option that you use layers ######
    kernel_initializer = check_keras_options(keras_options, 'kernel_initializer', 'lecun_normal')
    activation='selu'
    print('    default initializer = %s, default activation = %s' %(kernel_initializer, activation))
    ############################################################################
    use_bias = check_keras_options(keras_options, 'use_bias', True)
    lr_scheduler = check_keras_options(keras_options, 'lr_scheduler', "")
    onecycle_steps = max(10, np.ceil(data_size/(2*batch_size))*NUMBER_OF_EPOCHS)
    print('    Onecycle steps = %d' %onecycle_steps)
    ######################   set some defaults for model parameters here ##############
    keras_options, model_options, num_predicts, output_activation = get_model_defaults(keras_options,
                                                                    model_options, targets)
    ###################################################################################
    val_mode = keras_options["mode"]
    val_monitor = keras_options["monitor"]
    val_loss = keras_options["loss"]
    val_metrics = keras_options["metrics"]
    ########################################################################
    try:
        print('    number of classes = %s, output_activation = %s' %(
                            num_predicts, output_activation))
        print('    loss function: %s' %str(val_loss).split(".")[-1].split(" ")[0])
    except:
        print('    loss fn = %s    number of classes = %s, output_activation = %s' %(
                            val_loss, num_predicts, output_activation))
    ####  just use modeltype for printing that's all ###
    modeltype = cat_vocab_dict['modeltype']
    
    ############################################################################
    ### A Regular body does not have separate NLP outputs.  ####################
    ### However an Irregular body like fast models have separate NLP outputs. ##
    ############################################################################
    regular_body = True
    if isinstance(meta_outputs, list):
        if nlp_flag:
            if len(nlp_outputs) > 0:
                ### This is a true nlp and we need to use nlp inputs ##
                regular_body = False
            else:
                regular_body = True
        else:
            regular_body = False
    ############################################################################
    
    ### check the defaults for the following!
    save_weights_only = check_keras_options(keras_options, "save_weights_only", False)

    print('    steps_per_epoch = %s, number epochs = %s' %(STEPS_PER_EPOCH, NUMBER_OF_EPOCHS))
    print('    val mode = %s, val monitor = %s, patience = %s' %(val_mode, val_monitor, patience))

    callbacks_dict, tb_logpath = get_callbacks(val_mode, val_monitor, patience,
                                    learning_rate, save_weights_only, 
                                    onecycle_steps, save_model_path)
    chosen_callback = get_chosen_callback(callbacks_dict, keras_options)
    if not keras_options["lr_scheduler"]:
        print('    chosen keras LR scheduler = default')
    else:
        print('    chosen keras LR scheduler = %s' %keras_options['lr_scheduler'])

    ## You cannot use Unbatch to remove batch since we need it finding size below ####
    #full_ds = full_ds.unbatch()
    ############## Split train into train and validation datasets here ###############
    recover = lambda x,y: y
    print('\nSplitting train into 80+20 percent: train and validation data')
    valid_ds1 = full_ds.enumerate().filter(is_valid).map(recover)
    train_ds = full_ds.enumerate().filter(is_train).map(recover)
    heldout_ds1 = valid_ds1
    ##################################################################################
    print('    Splitting validation 20 into 10+10 percent: valid and heldout data')
    valid_ds = heldout_ds1.enumerate().filter(is_test).map(recover)
    heldout_ds = heldout_ds1.enumerate().filter(is_test).map(recover)
    print('\nLoading model and setting params. Will take 2-3 mins. Please be patient.')
    ##################################################################################
    ###   V E R Y    I M P O R T A N T  S T E P   B E F O R E   M O D E L   F I T  ###
    ##################################################################################
    shuffle_size = 1000
    if num_labels <= 1:
        try:
            y_test = np.concatenate(list(heldout_ds.map(lambda x,y: y).as_numpy_iterator()))
            print('    Single-Label: Heldout data shape: %s' %(y_test.shape,))
            max_batch_size = int(min(y_test.shape[0], 4096))
        except:
            max_batch_size = 48
            pass
    else:
        iters = int(data_size/batch_size) + 1
        for inum, each_target in enumerate(target):
            add_ls = []
            for feats, labs in heldout_ds.take(iters):
                add_ls.append(list(labs[each_target].numpy()))
            flat_list = [item for sublist in add_ls for item in sublist]
            if inum == 0:
                each_array = np.array(flat_list)
            else:
                each_array = np.c_[each_array, np.array(flat_list)]
        y_test = copy.deepcopy(each_array)
        print('    Multi-Label: Heldout data shape: %s' %(y_test.shape,))
        max_batch_size = y_test.shape[0]

    if modeltype == 'Regression':
        if (y_test>=0).all() :
            ### if there are no negative values, then set output as positives only
            output_activation = 'softplus'
            print('Setting output activation layer as softplus since there are no negative values')
    print(' Shuffle size = %d' %shuffle_size)
    
    train_ds = train_ds.prefetch(tf.data.AUTOTUNE).shuffle(
                            shuffle_size, reshuffle_each_iteration=False, seed=42)#.repeat()
    valid_ds = valid_ds.prefetch(tf.data.AUTOTUNE)#.repeat()
    if not isinstance(use_my_model, str):  ### That means no tuner in this case ####
        tuner = "None"
    else:
        tuner = model_options["tuner"]
    print('    Training %s model using %s. This will take time...' %(keras_model_type, tuner))

    from secrets import randbelow
    rand_num = randbelow(10000)
    tf.compat.v1.reset_default_graph()
    K.clear_session()

    #######################################################################################
    ###    E A R L Y    S T O P P I N G    T O    P R E V E N T   O V E R F I T T I N G  ##
    #######################################################################################
    if keras_options['lr_scheduler'] in ['expo', 'ExponentialDecay', 'exponentialdecay']:
        callbacks_list_tuner = callbacks_dict['early_stop']
    else:
        callbacks_list_tuner = [chosen_callback, callbacks_dict['early_stop']]

    targets = cat_vocab_dict["target_variables"]
    ############################################################################
    ########     P E R FO R M     T U N I N G    H E R E  ######################
    ############################################################################
    tune_mode = 'min'
    trials_saved_path = os.path.join(save_model_path, "trials")
    if num_labels > 1 and modeltype != 'Regression':
        tune_mode = 'max'
    else:
        tune_mode = val_mode
    if tuner.lower() == "storm":
        ########   S T O R M   T U N E R   D E F I N E D     H E R E ###########
        randomization_factor = 0.5
        tuner = MyTuner(project_dir=trials_saved_path,
                    build_fn=build_model_storm,
                    objective_direction=tune_mode,
                    init_random=5,
                    max_iters=max_trials,
                    randomize_axis_factor=randomization_factor,
                    overwrite=True)
        ###################   S T o R M   T U N E R   ###############################
        # parameters passed through 'search' go directly to the 'run_trial' method ##
        #### This is where you find best model parameters for keras using SToRM #####
        #############################################################################
        start_time1 = time.time()
        print('    STORM Tuner max_trials = %d, randomization factor = %0.2f' %(
                            max_trials, randomization_factor))
        tuner_epochs = 100  ### keep this low so you can run fast
        tuner_steps = STEPS_PER_EPOCH  ## keep this also very low
        batch_limit = min(max_batch_size, int(5 * find_batch_size(data_size)))
        batch_nums = int(min(8, math.log(batch_limit, 3)))
        print('Max. batch size = %d, number of batch sizes to try: %d' %(batch_limit, batch_nums))
        
        #### You have to make sure that inputs are unique, otherwise error ####
        tuner.search(train_ds, valid_ds, tuner_epochs, tuner_steps,
                            inputs, meta_outputs, cols_len, output_activation,
                            num_predicts, modeltype, optimizer, val_loss,
                            val_metrics, patience, val_mode, data_size,
                            learning_rate, val_monitor, callbacks_list_tuner,
                            modeltype,  class_weights, batch_size,
                            batch_limit, batch_nums, targets, nlp_flag, regular_body,
                            project_name, keras_model_type, cat_vocab_dict,
                            model_options)
        best_trial = tuner.get_best_trial()
        print('    best trial selected as %s' %best_trial)
        ##### get the best model parameters now. Also split it into two models ###########
        print('Time taken for tuning hyperparameters = %0.0f (mins)' %((time.time()-start_time1)/60))
        ##########    S E L E C T   B E S T   O P T I M I Z E R and L R  H E R E ############
        try:
            hpq = tuner.get_best_config()
            best_model, best_optimizer = build_model_storm(hpq, batch_size)
            best_batch = hpq.values['batch_size']
            hpq_optimizer = hpq.values['optimizer']
            if best_trial.metrics['final_lr'] < 0:
                print('    best learning rate less than zero. Resetting it....')
                optimizer_lr = 0.01
            else:
                optimizer_lr = best_trial.metrics['final_lr']
            print('Best hyperparameters: %s' %hpq.values)
        except:
            ### Sometimes the tuner cannot find a config that works!
            deep_model = return_model_body(keras_options)
            ### In some cases, the tuner doesn't select a good config in that case ##
            best_batch = batch_size
            hpq_optimizer = 'SGD'
            best_optimizer = keras.optimizers.SGD(learning_rate=0.001, momentum=0.9, nesterov=True)
            optimizer_lr = 0.01
            print('    Storm Tuner is erroring. Hence picking defaults including lr = %s' %optimizer_lr)

        ### Sometimes the learning rate is below zero - so reset it here!
        ### Set the learning rate for the best optimizer here ######
        print('\nSetting best optimizer %s its best learning_rate = %s' %(hpq_optimizer, optimizer_lr))
        best_optimizer = return_optimizer(hpq_optimizer)
        K.set_value(best_optimizer.learning_rate, optimizer_lr)
        
        ##### This is the simplest way to convert a sequential model to functional model!
        if regular_body:
            storm_outputs = add_outputs_to_model_body(best_model, meta_outputs)
        else:
            storm_outputs = add_outputs_to_auto_model_body(best_model, meta_outputs, nlp_flag)
        #### This final outputs is the one that is taken into final dense layer and compiled
        #print('    Custom model loaded successfully. Now compiling model...')

        ###### This is where you compile the model after it is built ###############
        #### Add a final layer for outputs during compiled model phase #############

        best_model = get_compiled_model(inputs, storm_outputs, output_activation, num_predicts, modeltype,
                            best_optimizer, val_loss, val_metrics, cols_len, targets)
        deep_model = best_model
        #######################################################################################
    elif tuner.lower() == "optuna":
        ######     O P T U N A    ##########################
        ### This is where you build the optuna model   #####
        ####################################################
        optuna_scores = []
        def objective(trial):
            optimizer_options = ""
            opt_model = build_model_optuna(trial, inputs, meta_outputs, output_activation, num_predicts,
                        modeltype, optimizer_options, val_loss, val_metrics, cols_len, targets, nlp_flag, regular_body)
            optuna_epochs = 5
            history = opt_model.fit(train_ds, validation_data=valid_ds,
                        epochs=optuna_epochs, shuffle=True,
                        callbacks=callbacks_list_tuner,
                        verbose=0)
            if num_labels == 1:
                score = np.mean(history.history[val_monitor][-5:])
            else:
                for i in range(num_labels):
                    ### the next line uses the list of metrics to find one that is a closest match
                    metric1 = [x for x in history.history.keys() if (targets[i] in x) & ("loss" not in x) ]
                    val_metric = metric1[0]
                    if i == 0:
                        results = history.history[val_metric][-5:]
                    else:
                        results = np.c_[results,history.history[val_metric][-5:]]
                score = results.mean(axis=1).mean()
            optuna_scores.append(score)
            return score
        ##### This where you run optuna ###################
        study_name = project_name+'_'+keras_model_type+'_study_'+str(rand_num)
        if tune_mode == 'max':
            study = optuna.create_study(study_name=study_name, direction="maximize", load_if_exists=False)
        else:
            study = optuna.create_study(study_name=study_name, direction="minimize", load_if_exists=False)
        ### now find the best tuning hyper params here ####
        study.optimize(objective, n_trials=max_trials)
        print('Best trial score in Optuna: %s' %study.best_trial.value)
        print('    Scores mean:', np.mean(optuna_scores), 'std:', np.std(optuna_scores))
        print('    Best params: %s' %study.best_params)
        optimizer_options = study.best_params['optimizer']
        best_model = build_model_optuna(study.best_trial, inputs, meta_outputs, output_activation, num_predicts,
                        modeltype, optimizer_options, val_loss, val_metrics, cols_len, targets, nlp_flag, regular_body)
        best_optimizer = best_model.optimizer
        deep_model = build_model_optuna(study.best_trial, inputs, meta_outputs, output_activation, num_predicts,
                        modeltype, optimizer_options, val_loss, val_metrics, cols_len, targets, nlp_flag, regular_body)
        best_batch = batch_size
        optimizer_lr = best_optimizer.learning_rate.numpy()
        print('\nBest optimizer = %s and best learning_rate = %s' %(best_optimizer, optimizer_lr))
        K.set_value(best_optimizer.learning_rate, optimizer_lr)
    elif tuner.lower() == "none":
        print('skipping tuner search since use_my_model flag set to True...')
        best_model = use_my_model
        deep_model = use_my_model
        if regular_body:
            best_outputs = add_outputs_to_model_body(best_model, meta_outputs)
            deep_outputs = add_outputs_to_model_body(deep_model, meta_outputs)
        else:
            best_outputs = add_outputs_to_auto_model_body(best_model, meta_outputs, nlp_flag)
            deep_outputs = add_outputs_to_auto_model_body(deep_model, meta_outputs, nlp_flag)
        best_optimizer = keras.optimizers.SGD(learning_rate=0.001, momentum=0.9, nesterov=True)
        best_batch = batch_size
        optimizer_lr = best_optimizer.learning_rate.numpy()
        print('\nBest optimizer = %s and best learning_rate = %s' %(best_optimizer, optimizer_lr))
        K.set_value(best_optimizer.learning_rate, optimizer_lr)
        #######################################################################################
        #### The best_model will be used for predictions on valid_ds to get metrics #########
        best_model = get_compiled_model(inputs, best_outputs, output_activation, num_predicts,
                            modeltype, best_optimizer, val_loss, val_metrics, cols_len, targets)
        deep_model = get_compiled_model(inputs, deep_outputs, output_activation, num_predicts,
                            modeltype, best_optimizer, val_loss, val_metrics, cols_len, targets)
        #######################################################################################

    ####################################################################################
    #####   T R A IN  A N D   V A L I D A T I O N   F O U N D    H E R E          ######
    ####################################################################################

    train_ds = train_ds.unbatch().batch(best_batch, drop_remainder=True)
    train_ds = train_ds.shuffle(shuffle_size,
                reshuffle_each_iteration=False, seed=42).prefetch(tf.data.AUTOTUNE)#.repeat()

    valid_ds = valid_ds.unbatch().batch(best_batch, drop_remainder=True)
    valid_ds = valid_ds.prefetch(tf.data.AUTOTUNE)#.repeat()

    ####################################################################################
    ############### F I R S T  T R A I N   F O R  1 0 0   E P O C H S ##################
    ### You have to set both callbacks in order to learn what the best learning rate is
    ####################################################################################
    if keras_options['lr_scheduler'] in ['expo', 'ExponentialDecay', 'exponentialdecay']:
        #### Exponential decay will take care of automatic reduction of Learning Rate
        if early_stopping:
            callbacks_list = [callbacks_dict['early_stop'], callbacks_dict['tensor_board']]
        else:
            callbacks_list = [callbacks_dict['tensor_board']]
    else:
        #### here you have to explicitly include Learning Rate reducer
        if early_stopping:
            callbacks_list = [callbacks_dict['early_stop'], callbacks_dict['tensor_board'], chosen_callback]
        else:
            callbacks_list = [callbacks_dict['tensor_board'], chosen_callback]

    print('Model training with best hyperparameters for %d epochs' %NUMBER_OF_EPOCHS)
    for each_callback in callbacks_list:
        print('    Callback added: %s' %str(each_callback).split(".")[-1])
    
    ############################    M O D E L     T R A I N I N G   ##################
    np.random.seed(42)
    tf.random.set_seed(42)
    history = best_model.fit(train_ds, validation_data=valid_ds, #batch_size=best_batch,
            epochs=NUMBER_OF_EPOCHS, #steps_per_epoch=STEPS_PER_EPOCH,
            callbacks=callbacks_list, class_weight=class_weights,
            #validation_steps=STEPS_PER_EPOCH,
           shuffle=True)
    print('    Model training completed. Following metrics available: %s' %history.history.keys())
    print('Time taken to train model (in mins) = %0.0f' %((time.time()-start_time)/60))

    #################################################################################
    #######          R E S E T    K E R A S      S E S S I O N
    #################################################################################
    # Reset Keras Session

    K.clear_session()
    reset_keras()
    tf.compat.v1.reset_default_graph()
    tf.keras.backend.reset_uids()

    ###   Once the best learning rate is chosen the model is ready to be trained on full data
    try:
         ## this is where it stopped
        stopped_epoch = max(5, int(pd.DataFrame(history.history).shape[0] - patience))
    except:
        stopped_epoch = 100
    print('    Stopped epoch = %s' %stopped_epoch)

    ###  Plot the epochs and loss metrics here #####################
    try:
        if modeltype == 'Regression':
            plot_history(history, val_monitor[4:], target)
        elif modeltype == 'Classification':
            plot_history(history, val_monitor[4:], target)
        else:
            plot_history(history, val_monitor[4:], target)
    except:
        print('    Plot history is erroring. Tensorboard logs can be found here: %s' %tb_logpath)

    print('Time taken to train model (in mins) = %0.0f' %((time.time()-start_time)/60))
    print('    Stopped epoch = %s' %stopped_epoch)

    #################################################################################
    ########     P R E D I C T   O N   H E L D   O U T  D A T A   H E R E      ######
    #################################################################################
    scores = []
    ls = []
    
    print('Held out data actuals shape: %s' %(y_test.shape,))
    if verbose >= 1:
        try:
            print_one_row_from_tf_label(heldout_ds)
        except:
            print('could not print samples from heldout ds labels')
    ###########################################################################
    y_probas = best_model.predict(heldout_ds)

    if isinstance(target, str):
        if modeltype != 'Regression':
            y_test_preds = y_probas.argmax(axis=1)
        else:
            if y_test.dtype == 'int':
                y_test_preds = y_probas.round().astype(int)
            else:
                y_test_preds = y_probas.ravel()
    else:
        if modeltype != 'Regression':
            #### This is for multi-label binary or multi-class problems ##
            for each_t in range(len(target)):
                if each_t == 0:
                    y_test_preds = y_probas[each_t].argmax(axis=1).astype(int)
                else:
                    y_test_preds = np.c_[y_test_preds, y_probas[each_t].argmax(axis=1).astype(int)]
        else:
            ### This is for Multi-Label Regression ###
            for each_t in range(len(target)):
                if each_t == 0:
                    y_test_preds = y_probas[each_t].mean(axis=1)
                else:
                    y_test_preds = np.c_[y_test_preds, y_probas[each_t].mean(axis=1)]
                if y_test.dtype == 'int':
                    y_test_preds = y_test_preds.round().astype(int)

    print('\nHeld out predictions shape:%s' %(y_test_preds.shape,))
    if verbose >= 1:
        if modeltype != 'Regression':
            print('    Sample predictions: %s' %y_test_preds[:10])
        else:
            if num_labels == 1:
                print('    Sample predictions: %s' %y_test_preds.ravel()[:10])
            else:
                print('    Sample predictions:\n%s' %y_test_preds[:10])

    #################################################################################
    ########     P L O T T I N G   V A L I D A T I O N   R E S U L T S         ######
    #################################################################################
    print('\n###########################################################')
    print('         Held-out test data set Results:')
    num_labels = cat_vocab_dict['num_labels']
    num_classes = cat_vocab_dict['num_classes']

    ######## Check for NaN in predictions ###############################
    if check_for_nan_in_array(y_probas):
        y_probas = pd.DataFrame(y_probas).fillna(0).values
    elif check_for_nan_in_array(y_test_preds):
        y_test_preds = pd.DataFrame(y_test_preds).fillna(0).values.ravel()

    ###############           P R I N T I N G   R E S U L T S      #################
    if num_labels <= 1:
        #### This is for Single-Label Problems only ################################
        if modeltype == 'Regression':
            print_regression_model_stats(y_test, y_test_preds,target,plot_name=project_name)
            ### plot the regression results here #########
            plot_regression_residuals(y_test, y_test_preds, target, project_name, num_labels)
        else:
            print_classification_header(num_classes, num_labels, target)
            labels = cat_vocab_dict['original_classes']
            if cat_vocab_dict['target_transformed']:
                target_names = cat_vocab_dict['transformed_classes']
                target_le = cat_vocab_dict['target_le']
                y_pred = y_probas.argmax(axis=1)
                y_test_trans = target_le.inverse_transform(y_test)
                y_pred_trans = target_le.inverse_transform(y_pred)
                labels = np.unique(y_test_trans) ### sometimes there is less classes
                plot_classification_results(y_test_trans, y_pred_trans, labels, labels, target)
            else:
                y_pred = y_probas.argmax(axis=1)
                labels = np.unique(y_test) ### sometimes there are fewer classes ##
                plot_classification_results(y_test, y_pred, labels, labels, target)
            print_classification_metrics(y_test, y_probas, proba_flag=True)
    else:
        if modeltype == 'Regression':
            #### This is for Multi-Label Regression ################################
            print_regression_model_stats(y_test, y_test_preds,target,plot_name=project_name)
            ### plot the regression results here #########
            plot_regression_residuals(y_test, y_test_preds, target, project_name, num_labels)
        else:
            #### This is for Multi-Label Classification ################################
            try:
                targets = cat_vocab_dict["target_variables"]
                for i, each_target in enumerate(targets):
                    print_classification_header(num_classes, num_labels, each_target)
                    labels = cat_vocab_dict[each_target+'_original_classes']
                    if cat_vocab_dict['target_transformed']:
                        ###### Use a nice classification matrix printing module here #########
                        target_names = cat_vocab_dict[each_target+'_transformed_classes']
                        target_le = cat_vocab_dict['target_le'][i]
                        y_pred = y_probas[i].argmax(axis=1)
                        y_test_trans = target_le.inverse_transform(y_test[:,i])
                        y_pred_trans = target_le.inverse_transform(y_pred)
                        labels = np.unique(y_test_trans) ### sometimes there is less classes
                        plot_classification_results(y_test_trans, y_pred_trans, labels, labels, each_target)
                    else:
                        y_pred = y_probas[i].argmax(axis=1)
                        labels = np.unique(y_test[:,i]) ### sometimes there are fewer classes ##
                        plot_classification_results(y_test[:,i], y_pred, labels, labels, each_target)
                    print_classification_metrics(y_test[:,i], y_probas[i], proba_flag=True)
                    #### This prints additional metrics #############
                    print(classification_report(y_test[:,i],y_test_preds[:,i]))
                    print(confusion_matrix(y_test[:,i], y_test_preds[:,i]))
            except:
                print_classification_metrics(y_test, y_test_preds, False)
                print(classification_report(y_test, y_test_preds ))
    ###############           P R I N T I N G   C O M P L E T E D      #################

    ##################################################################################
    ###   S E C O N D   T R A I N   O N  F U L L   T R A I N   D A T A   S E T     ###
    ##################################################################################
    ############       train the model on full train data set now      ###############
    print('\nFinally, training on full train dataset. This will take time...')
    full_ds = full_ds.unbatch().batch(best_batch)
    full_ds = full_ds.shuffle(shuffle_size,
            reshuffle_each_iteration=False, seed=42).prefetch(best_batch)#.repeat()

    #################   B E S T    D E E P   M O D E L       ##########################
    ##### You need to set the best learning rate from the best_model #################
    best_rate = best_model.optimizer.lr.numpy()
    if best_rate < 0:
        print('    best learning rate less than zero. Resetting it....')
        best_rate = 0.01
    else:
        pass
        print('    best learning rate = %s' %best_rate)
    K.set_value(deep_model.optimizer.learning_rate, best_rate)
    print("    set learning rate using best model:", deep_model.optimizer.learning_rate.numpy())
    ####   Dont set the epochs too low - let them be back to where they were stopped  ####
    print('    max epochs for training = %d' %stopped_epoch)

    ##### You save deep_model finally here using checkpoints ##############
    callbacks_list = [ callbacks_dict['check_point'] ]
    deep_model.fit(full_ds, epochs=stopped_epoch, #steps_per_epoch=STEPS_PER_EPOCH, batch_size=best_batch,
                class_weight = class_weights,
                callbacks=callbacks_list,  shuffle=True, verbose=0)
    ##################################################################################
    #######        S A V E the model here using save_model_name      #################
    ##################################################################################

    save_model_artifacts(deep_model, cat_vocab_dict, var_df, save_model_path, 
                    save_model_flag, model_options)

    #############################################################################
    #####     C L E A R      S E S S I O N     B E F O R E   C L O S I N G   ####
    #############################################################################
    #from numba import cuda
    #cuda.select_device(0)
    #cuda.close()
    # Reset Keras Session
    K.clear_session()
    tf.compat.v1.reset_default_graph()
    reset_keras()
    tf.keras.backend.reset_uids()

    print('\nDeep_Auto_ViML completed. Total time taken = %0.0f (in mins)' %((time.time()-start_time)/60))

    return deep_model, cat_vocab_dict
######################################################################################
def return_model_body(keras_options):
    num_layers = check_keras_options(keras_options, 'num_layers', 2)
    model_body = tf.keras.Sequential([])
    for l_ in range(num_layers):
        model_body.add(layers.Dense(64, activation='relu', kernel_initializer="lecun_normal",
                                    #activity_regularizer=tf.keras.regularizers.l2(0.01)
                                    ))
    return model_body
########################################################################################
def check_for_nan_in_array(array_in):
    """
    If an array has NaN in it, this will return True. Otherwise, it will return False.
    """
    array_sum = np.sum(array_in)
    array_nan = np.isnan(array_sum)
    return array_nan
########################################################################################

