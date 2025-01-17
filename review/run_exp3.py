import utils
import constants
import random
from threading import Thread
import custom_extension

import tensorflow as tf
import keras
import numpy as np
from playsound import playsound as play


DEBUG = False

def run_single_case(
        experiment_name, 
        client_names,
        X_train, 
        y_train, 
        X_test,
        y_test,
        X_train_malicious,
        y_train_malicious, 
        X_test_malicious, 
        y_test_malicious,
        percentage_noisy_clients,
        how_small_percentage,
        special_clients, 
        input_shape, 
        nb_classes, 
        class_weights,
        test_batched_overall,
        test_batched_truflass):
    print("Creating clients...")
    clients_batched_original = utils.create_clients(X_train, y_train, nb_classes, constants.sampling_technique, client_names)    
    clients_batched_malicous = utils.create_clients(X_train_malicious, y_train_malicious, nb_classes, constants.sampling_technique, client_names)
    client_names = list(clients_batched_original.keys())

    # this is meant to give to all clients the same samples indexes
    original_sample_size = len(clients_batched_original[client_names[0]])
    small_sample_size = int(original_sample_size * how_small_percentage)
    sample_indices = np.random.choice(original_sample_size, small_sample_size, replace=False)

    client_batches_testing_trustfed = {}

    print("small_sample_size", small_sample_size)

    # create noisy batches
    clients_batched_dic = {}
    clients_batched_dic["NO_SELECTION"] = custom_extension.create_noisy_batches(clients_batched_original, clients_batched_malicous, special_clients, sample_indices)
    clients_batched_dic["TRUFLAAS"] = custom_extension.create_noisy_batches(clients_batched_original, clients_batched_malicous, special_clients, sample_indices)
    clients_batched_dic["TRUSTFED"] = custom_extension.create_noisy_batches(clients_batched_original, clients_batched_malicous, special_clients, sample_indices)

    global_model = {}
    global_model["NO_SELECTION"] : keras.Model = utils.get_model(input_shape, nb_classes)
    global_model["TRUFLAAS"] : keras.Model = utils.get_model(input_shape, nb_classes)
    global_model["TRUSTFED"] : keras.Model = utils.get_model(input_shape, nb_classes)

    # keep track of best global accuracy
    best_accuracy_overall : dict = {}
    best_accuracy_overall["NO_SELECTION"] : float = 0
    best_accuracy_overall["TRUFLAAS"] : float = 0
    best_accuracy_overall["TRUSTFED"] : float = 0

    if DEBUG:
        for client_name in client_names:
            print(" - - - TRAIN - - -")
            print("{}_no_selection".format(client_name), len(clients_batched_dic["NO_SELECTION"][client_name]))
            print("{}TRUFLAAS".format(client_name), len(clients_batched_dic["TRUFLAAS"][client_name]))
            print("{}TRUSTFED".format(client_name), len(clients_batched_dic["TRUSTFED"][client_name]))

    client_set : dict = {}
    client_set["NO_SELECTION"] : dict = {k: {} for k in client_names}
    client_set["TRUFLAAS"] : dict = {k: {} for k in client_names}
    client_set["TRUSTFED"] : dict = {k: {} for k in client_names}

    for (client_name, data) in clients_batched_dic["NO_SELECTION"].items():
        local_model = utils.get_model(input_shape, nb_classes)
        local_model.compile(loss=constants.loss,
                        optimizer=constants.optimizer,
                        metrics=constants.metrics)
        
        # creating test samples for TRUSTFED too
        if client_name in special_clients:
            X_test_sample, y_test_sample = custom_extension.sample_test(X_test_malicious, y_test_malicious, constants.local_testing_size)
        else:
            X_test_sample, y_test_sample = custom_extension.sample_test(X_test, y_test, constants.local_testing_size)
        client_batches_testing_trustfed[client_name] = {}
        client_batches_testing_trustfed[client_name]["X_test_sample"] = X_test_sample
        client_batches_testing_trustfed[client_name]["y_test_sample"] = y_test_sample

        client_set["NO_SELECTION"][client_name]["model"] = local_model
        client_set["NO_SELECTION"][client_name]["dataset"] = utils.batch_data(data, constants.BATCH_SIZE)
        client_set["NO_SELECTION"][client_name]["testing"] = custom_extension.create_testing_batched(client_batches_testing_trustfed[client_name]["X_test_sample"], client_batches_testing_trustfed[client_name]["y_test_sample"])
        

    for (client_name, data) in clients_batched_dic["TRUFLAAS"].items():
        local_model = utils.get_model(input_shape, nb_classes)
        local_model.compile(loss=constants.loss, 
                        optimizer=constants.optimizer, 
                        metrics=constants.metrics)
    
        client_set["TRUFLAAS"][client_name]["model"] = local_model
        client_set["TRUFLAAS"][client_name]["dataset"] = utils.batch_data(data, constants.BATCH_SIZE)
        # client_set["TRUFLAAS"][client_name]["testing"] = custom_extension.create_testing_batched(client_batches_testing_trustfed[client_name]["X_test_sample"], client_batches_testing_trustfed[client_name]["y_test_sample"])

    for (client_name, data) in clients_batched_dic["TRUSTFED"].items():
        local_model = utils.get_model(input_shape, nb_classes)
        local_model.compile(loss=constants.loss, 
                        optimizer=constants.optimizer, 
                        metrics=constants.metrics)
        client_set["TRUSTFED"][client_name]["model"] = local_model
        client_set["TRUSTFED"][client_name]["dataset"] = utils.batch_data(data, constants.BATCH_SIZE)
        client_set["TRUSTFED"][client_name]["testing"] = custom_extension.create_testing_batched(client_batches_testing_trustfed[client_name]["X_test_sample"], client_batches_testing_trustfed[client_name]["y_test_sample"])
        
    # initialize testing metrics
    testing_metrics : dict = {}
    testing_metrics["NO_SELECTION"] = {}
    testing_metrics["TRUFLAAS"] = {}
    testing_metrics["TRUSTFED"] = {}

    testing_metrics["NO_SELECTION"]["loss"] = []
    testing_metrics["NO_SELECTION"]["accuracy"] = []
    testing_metrics["NO_SELECTION"]["precision"] = []
    testing_metrics["NO_SELECTION"]["recall"] = []
    testing_metrics["NO_SELECTION"]["f1"] = []
    testing_metrics["NO_SELECTION"]["best_global_accuracy"] = 0

    testing_metrics["TRUFLAAS"]["loss"] = []
    testing_metrics["TRUFLAAS"]["accuracy"] = []
    testing_metrics["TRUFLAAS"]["precision"] = []
    testing_metrics["TRUFLAAS"]["recall"] = []
    testing_metrics["TRUFLAAS"]["f1"] = []
    testing_metrics["TRUFLAAS"]["best_global_accuracy"] = 0

    testing_metrics["TRUSTFED"]["loss"] = []
    testing_metrics["TRUSTFED"]["accuracy"] = []
    testing_metrics["TRUSTFED"]["precision"] = []
    testing_metrics["TRUSTFED"]["recall"] = []
    testing_metrics["TRUSTFED"]["f1"] = []
    testing_metrics["TRUSTFED"]["best_global_accuracy"] = 0

    threads : dict = {}
    threads["NO_SELECTION"] = [None] * constants.num_clients
    threads["TRUFLAAS"] = [None] * constants.num_clients
    threads["TRUSTFED"] = [None] * constants.num_clients
    
    print("Starting training...")
    for comm_round in range(constants.comms_round):            
        # get the global model's weights - will serve as the initial weights for all local models
        global_weights : dict = {}
        global_weights["NO_SELECTION"] = global_model["NO_SELECTION"].get_weights()
        global_weights["TRUFLAAS"] = global_model["TRUFLAAS"].get_weights()
        global_weights["TRUSTFED"] = global_model["TRUSTFED"].get_weights()
        
        #initial list to collect local model weights after scalling
        local_weight_list : dict = {}
        local_weight_list["NO_SELECTION"] : list = list()
        local_weight_list["TRUFLAAS"] : list = list()
        local_weight_list["TRUSTFED"] : list = list()

        average_weights : dict = {}
        average_weights["NO_SELECTION"] : list = list()
        average_weights["TRUFLAAS"] : list = list()
        average_weights["TRUSTFED"] : list = list()

        # create appropriate testing batches TRUFLAAS
        this_round_truflass_testing = test_batched_truflass[comm_round]
        test_batched_truflaas = custom_extension.create_testing_batched(this_round_truflass_testing["x"], this_round_truflass_testing["y"])
        
        #loop through each client and create new local model
        # no_selection_clients
        for i, client_name in enumerate(client_names):    
            threads["NO_SELECTION"][i] : Thread = Thread(target=utils.train_client, args=(client_name, global_weights["NO_SELECTION"], class_weights, client_set["NO_SELECTION"], comm_round))     
            threads["NO_SELECTION"][i].start()

        for i in range(constants.num_clients):
            threads["NO_SELECTION"][i].join()         

        # truflaas_selection_clients
        for i, client_name in enumerate(client_names):    
            threads["TRUFLAAS"][i] : Thread = Thread(target=utils.train_client, args=(client_name, global_weights["TRUFLAAS"], class_weights, client_set["TRUFLAAS"], comm_round))     
            threads["TRUFLAAS"][i].start()

        for i in range(constants.num_clients):
            threads["TRUFLAAS"][i].join()     

        # trustfed_selection_clients
        for i, client_name in enumerate(client_names):
            threads["TRUSTFED"][i] : Thread = Thread(target=utils.train_client, args=(client_name, global_weights["TRUSTFED"], class_weights, client_set["TRUSTFED"], comm_round))     
            threads["TRUSTFED"][i].start()
        
        for i in range(constants.num_clients):
            threads["TRUSTFED"][i].join()

        local_weight_list["NO_SELECTION"] : list = custom_extension.select_all_clients(client_set["NO_SELECTION"])
        local_weight_list["TRUFLAAS"] : list = custom_extension.select_best_clients(client_set["TRUFLAAS"], test_batched_truflaas, comm_round, mode = "TRUFLAAS", experiment_name = experiment_name)
        local_weight_list["TRUSTFED"] : list = custom_extension.select_best_clients(client_set["TRUSTFED"], None, comm_round, mode = "TRUSTFED", experiment_name = experiment_name)

        #to get the average over all the local model, we simply calculate the average of the sum of local weights
        average_weights["NO_SELECTION"] : list = utils.average_model_weights(local_weight_list["NO_SELECTION"])
        average_weights["TRUFLAAS"] : list = utils.average_model_weights(local_weight_list["TRUFLAAS"])
        average_weights["TRUSTFED"] : list = utils.average_model_weights(local_weight_list["TRUSTFED"])

        #update global model 
        global_model["NO_SELECTION"].set_weights(average_weights["NO_SELECTION"])
        global_model["TRUFLAAS"].set_weights(average_weights["TRUFLAAS"])
        global_model["TRUSTFED"].set_weights(average_weights["TRUSTFED"])

        # testing global model with NO_SELECTION
        for(x_batch, y_batch) in test_batched_overall:
            g_loss, g_accuracy, g_precision, g_recall, g_f1 = utils.test_model(x_batch, y_batch, global_model["NO_SELECTION"], comm_round, "[{}] global NO_SELECTION".format(experiment_name))
            testing_metrics["NO_SELECTION"]["loss"].append(g_loss)
            testing_metrics["NO_SELECTION"]["accuracy"].append(g_accuracy)
            testing_metrics["NO_SELECTION"]["precision"].append(g_precision)
            testing_metrics["NO_SELECTION"]["recall"].append(g_recall)
            testing_metrics["NO_SELECTION"]["f1"].append(g_f1)
   
            # if g_accuracy > best_accuracy_overall["NO_SELECTION"]:
            #     best_accuracy_overall["NO_SELECTION"] = g_accuracy
            #     global_model["NO_SELECTION"].save_weights('global_model_best_no_selection.h5')
            #     print("New NO_SELECTION Weights Saved")
            
        # testing global model with TRUFLAAS
        for (x_batch, y_batch) in test_batched_overall:
            g_loss, g_accuracy, g_precision, g_recall, g_f1 = utils.test_model(x_batch, y_batch, global_model["TRUFLAAS"], comm_round, "[{}] global TRUFLAAS".format(experiment_name))
            testing_metrics["TRUFLAAS"]["loss"].append(g_loss)
            testing_metrics["TRUFLAAS"]["accuracy"].append(g_accuracy)
            testing_metrics["TRUFLAAS"]["precision"].append(g_precision)
            testing_metrics["TRUFLAAS"]["recall"].append(g_recall)
            testing_metrics["TRUFLAAS"]["f1"].append(g_f1)

            # if g_accuracy > best_accuracy_overall["TRUFLAAS"]:
            #     best_accuracy_overall["TRUFLAAS"] = g_accuracy
            #     global_model["TRUFLAAS"].save_weights('global_model_best_truflaas.h5')
            #     print("New TRUFLAAS Weights Saved")

        # testing global model with TRUSTFED
        for (x_batch, y_batch) in test_batched_overall:
            g_loss, g_accuracy, g_precision, g_recall, g_f1 = utils.test_model(x_batch, y_batch, global_model["TRUSTFED"], comm_round, "[{}] global TRUSTFED".format(experiment_name))
            testing_metrics["TRUSTFED"]["loss"].append(g_loss)
            testing_metrics["TRUSTFED"]["accuracy"].append(g_accuracy)
            testing_metrics["TRUSTFED"]["precision"].append(g_precision)
            testing_metrics["TRUSTFED"]["recall"].append(g_recall)
            testing_metrics["TRUSTFED"]["f1"].append(g_f1)

            # if g_accuracy > best_accuracy_overall["TRUSTFED"]:
            #     best_accuracy_overall["TRUSTFED"] = g_accuracy
            #     global_model["TRUSTFED"].save_weights('global_model_best_trustfed.h5')
            #     print("New TRUSTFED Weights Saved")

    print("Best Accuracy Overall NO_SELECTION: ", best_accuracy_overall["NO_SELECTION"])
    print("Best Accuracy Overall TRUFLAAS: ", best_accuracy_overall["TRUFLAAS"])
    print("Best Accuracy Overall TRUSTFED: ", best_accuracy_overall["TRUSTFED"])

    print("-------------------- --------------------- ---------------------")
    print("saving and showing graphs")

    custom_extension.save_graphs(testing_metrics, experiment_name, percentage_noisy_clients)

    print("-------------------- --------------------- ---------------------")
    print("saving csv file")

    custom_extension.save_csv(testing_metrics, experiment_name, percentage_noisy_clients)


if __name__ == "__main__":
    #initialize global model

    # experiments 1 --------------------------------------- 
    experiment_name = "exp3"
    how_small_percentage = 0.01
    runs = [
        {
            "percentage_noisy_clients": 0
        },
        {
            "percentage_noisy_clients": 0.1
        },
        {
            "percentage_noisy_clients": 0.25
        }
    ]

    df = utils.load_data()
    df_malicious = custom_extension.create_noisy_df(df = df)
    X_train, y_train, X_test, y_test, label_encoder = utils.split_df(df)
    X_train_malicious, y_train_malicious, X_test_malicious, y_test_malicious, _ = utils.split_df(df_malicious)

    client_names = ['{}_{}'.format("client", i+1) for i in range(constants.num_clients)]

    input_shape = X_train.shape[1:]
    nb_classes = len(label_encoder.classes_)
    class_weights = utils.get_class_weights(y_train)

    y_test = utils.convert_to_categorical(y_test, nb_classes)

    # this is used to test the global model with the whole test set
    test_batched_overall = tf.data.Dataset.from_tensor_slices((X_test, y_test)).batch(len(y_test))
    
    # this is used to test the local model on a subset of the overall test set [TRUFLAAS]
    test_batched_truflass = custom_extension.split_x_y_into_chunks(X_test, y_test, constants.comms_round)

    for r in runs:
        _percentage_noisy_clients = r["percentage_noisy_clients"]
        special_client_amount = int(len(client_names) * _percentage_noisy_clients)
        random.shuffle(client_names)
        special_clients = client_names[:special_client_amount]
        print("--- --- --- STARTING NEW RUN --- --- ---")
        print("percentage_noisy_clients: ", _percentage_noisy_clients)
        print("experiment_name: ", experiment_name)
        print("how_small_percentage: ", how_small_percentage)
        print(" --- --- --- ---- --- -- --- ---- ------ ---")
        run_single_case(experiment_name = experiment_name,
                        
                        client_names=client_names,

                        X_train = X_train, 
                        y_train = y_train,
                        X_test = X_test, 
                        y_test = y_test,

                        X_train_malicious = X_train_malicious,
                        y_train_malicious = y_train_malicious,
                        X_test_malicious = X_test_malicious,
                        y_test_malicious = y_test_malicious,

                        percentage_noisy_clients = _percentage_noisy_clients,
                        how_small_percentage = how_small_percentage,
                        special_clients = special_clients, 
                        input_shape=input_shape, 
                        nb_classes=nb_classes, 
                        class_weights=class_weights, 
                        test_batched_overall=test_batched_overall, 
                        test_batched_truflass=test_batched_truflass)
        
    play('./assets/alarm.mp3')
        