import torch
import time

import matplotlib.pyplot as plt
import numpy as np
import copy
np.random.seed(1)

from worker import Worker
from net_review import Net
from review_worker_validator import WorkerValidator
from review_worker_final_validator import WorkerFinalValidator

from utils_review import aggregate_model, aggregate_model_weighted, process_data_final, select_node_to_discard_trustfed, select_node_to_discard_truflass, save_np_to_file, save_2d_matrix_to_csv_file, create_folder_if_not_exists
import random

from playsound import playsound as play

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
device = "cpu"

experiments = 5
iterations = 20
size = 20
num_workers = 100
n_validators = 100
rounds = 100
special_options = [0, 25, 40]

def experiment_rare_cases(experiment_counter, n_specials, final_data):

    n_rares = n_specials
    all_trainers = range(num_workers)
    no_rare_nodes = random.sample(all_trainers, n_specials)
    standard_nodes = list(set(all_trainers) - set(no_rare_nodes))
    print("-----------------------------------")
    print("standard_nodes", standard_nodes)
    print("-----------------------------------")
    print("no_rare_nodes", no_rare_nodes)

    model_original = Net(input_shape = final_data["train_loader"].dataset.tensors[0].shape[-1])
    workers_baseline = {}
    workers_yes_rares_no_filter = {}
    workers_yes_rares_overall_filter = {}
    workers_yes_rares_rares_filter = {}
    workers_yes_rares_both_filters_intersection = {}
    workers_yes_rares_both_filters_union = {}

    memory = {}
    memory["rares"] = {}
    memory["overall"] = {}
    memory["intersection"] = {}
    memory["union"] = {}

    train_standard = [(data, target) for _,(data, target) in enumerate(final_data["train_loader"])]
    test_standard = [(data, target) for _,(data, target) in enumerate(final_data["test_loader"])]

    train_loader_no_rares = [(data, target) for _,(data, target) in enumerate(final_data["train_loader_no_rares"])]
    test_loader_no_rares = [(data, target) for _,(data, target) in enumerate(final_data["test_loader_no_rares"])]

    train_loader_yes_rares = [(data, target) for _,(data, target) in enumerate(final_data["train_loader_yes_rares"])]
    test_loader_yes_rares = [(data, target) for _,(data, target) in enumerate(final_data["test_loader_yes_rares"])]

    train_standard_small = [(data, target) for _,(data, target) in enumerate(final_data["train_loader_small"])]
    test_standard_small = [(data, target) for _,(data, target) in enumerate(final_data["test_loader_small"])]

    train_standard_big = [(data, target) for _,(data, target) in enumerate(final_data["train_loader_big"])]
    test_standard_big = [(data, target) for _,(data, target) in enumerate(final_data["test_loader_big"])]


    # training and testing baseline
    my_index_train = 0
    my_index_test = 0
    for w in all_trainers:
        # train
        data_train = train_standard[my_index_train][0]
        target_train = train_standard[my_index_train][1]
        # test
        data_test = test_standard[my_index_test][0]
        target_test = test_standard[my_index_test][1]
        workers_baseline[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
 
        my_index_train+=1
        my_index_test+=1
        if my_index_train > len(train_standard) - 1:
            my_index_train = 0
        if my_index_test > len(test_standard) - 1:
            my_index_test = 0

    # [standard nodes] - nodes with overall data 
    my_index_train, my_index_test = 0, 0
    for w in standard_nodes:
        data_train = train_standard[my_index_train][0]
        target_train = train_standard[my_index_train][1]
        data_test = test_standard[my_index_test][0]
        target_test = test_standard[my_index_test][1]
        workers_yes_rares_no_filter[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_overall_filter[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_rares_filter[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_both_filters_intersection[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_both_filters_union[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        my_index_train+=1
        my_index_test+=1
        if my_index_train > len(train_standard) - 1:
            my_index_train = 0
        if my_index_test > len(test_standard) - 1:
            my_index_test = 0

    # [special nodes] - no rares nodes 
    my_index_train, my_index_test = 0, 0
    for w in no_rare_nodes:
        data_train = train_loader_no_rares[my_index_train][0]
        target_train = train_loader_no_rares[my_index_train][1]
        data_test = test_loader_no_rares[my_index_test][0]
        target_test = test_loader_no_rares[my_index_test][1]
        workers_yes_rares_no_filter[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_overall_filter[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_rares_filter[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_both_filters_intersection[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        workers_yes_rares_both_filters_union[w] = Worker(w, 0.1, copy.deepcopy(model_original), (data_train, target_train), (data_test, target_test))
        my_index_train+=1
        my_index_test+=1
        if my_index_train > len(train_loader_no_rares) - 1:
            my_index_train = 0
        if my_index_test > len(test_loader_no_rares) - 1:
            my_index_test = 0

    # validator nodes rares
    worker_validator_rares = WorkerValidator(0, test_loader_yes_rares)

    # validator nodes overall
    worker_validator_overall = WorkerValidator(0, test_standard_big)

    # tester node - [testing on overall]
    test_index_overall = random.sample(range(len(test_standard)), 1)[0]
    test_index_rare = random.sample(range(len(test_loader_yes_rares)), 1)[0]
    # test_index_overall = 0
    # test_index_rare = 0
    test_worker = WorkerFinalValidator(0, (test_standard[test_index_overall][0], test_standard[test_index_overall][1]), (test_loader_yes_rares[test_index_rare][0], test_loader_yes_rares[test_index_rare][1]))

    results_only_rares = np.zeros(num_workers)
    results_only_overall = np.zeros(num_workers)
    acc_performance_metrics = np.zeros((6,iterations))

    csv_results = [["iterations", 
                    "no_special_loss", "no_special_f1", "no_special_accuracy",
                    "no_filter_loss", "no_filter_f1", "no_filter_accuracy",
                    "rare_only_filter_loss", "rare_only_filterf1", "rare_only_filter_accuracy",
                    "overall_filter_loss", "overall_filter_f1", "overall_filter_accuracy",
                    "both_filters_intersection_loss", "both_filters_intersection_f1", "both_filters_intersection_accuracy",
                    "both_filters_union_loss", "both_filters_union_f1", "both_filters_union_accuracy"]]
    
    # ------------------------------------------- learning starts here
    for itr in range(iterations):

        print(f'--------------------------------------------------------')
        print(f'exp2B_rare_data_intersection_and_union_overall_scoring')
        print(f'exp_counter: {experiment_counter} - iterations {itr}')
        print(f'n_specials: {n_specials}')
        print(f'--------------------------------------------------------')
        # train nodes without specials
        for node in workers_baseline:
            for _ in range(rounds):
                loss = workers_baseline[node].train_my_model()

        # train nodes with rares but no filter
        for node in workers_yes_rares_no_filter:
            for _ in range(rounds):
                loss = workers_yes_rares_no_filter[node].train_my_model()

        # train nodes with rares and only rare filter
        for node in workers_yes_rares_rares_filter:
            for _ in range(rounds):
                loss = workers_yes_rares_rares_filter[node].train_my_model()

        # train nodes with rares and only overall filter
        for node in workers_yes_rares_overall_filter:
            for _ in range(rounds):
                loss = workers_yes_rares_overall_filter[node].train_my_model()

        # train nodes with rares and both intersection filter
        for node in workers_yes_rares_both_filters_intersection:
            for _ in range(rounds):
                loss = workers_yes_rares_both_filters_intersection[node].train_my_model()

        # train nodes with rares and both union filter
        for node in workers_yes_rares_both_filters_union:
            for _ in range(rounds):
                loss = workers_yes_rares_both_filters_union[node].train_my_model()

        start_time = time.time()
        # node democratic validation only rares
        losses_rares = worker_validator_rares.test_other_model(workers_yes_rares_rares_filter, results_only_rares)

        # node democratic validation only overall
        losses_overall = worker_validator_overall.test_other_model(workers_yes_rares_overall_filter, results_only_overall)

        complaints_rares = np.zeros((num_workers))
        complaints_overall = np.zeros((num_workers))
        to_remove_detected_rares = []
        to_remove_detected_overall = []
        to_remove_detected_both_intersection = []

        complaints_rares = select_node_to_discard_truflass(results_only_rares)
        complaints_overall = select_node_to_discard_truflass(results_only_overall)

        to_remove_detected_rares = complaints_rares
        to_remove_detected_overall = complaints_overall
        to_remove_detected_both_intersection = list(set(to_remove_detected_rares) & set(to_remove_detected_overall))
        to_remove_detected_both_union = list(set(to_remove_detected_rares) | set(to_remove_detected_overall))

        # memory detection
        # rares
        for w in to_remove_detected_rares:
            if not w in memory["rares"].keys():
                memory["rares"][w] = 0
            memory["rares"][w] += 1
        # overall
        for w in to_remove_detected_overall:
            if not w in memory["overall"].keys():
                memory["overall"][w] = 0
            memory["overall"][w] += 1
        # intersection
        for w in to_remove_detected_both_intersection:
            if not w in memory["intersection"].keys():
                memory["intersection"][w] = 0
            memory["intersection"][w] += 1
        # union
        for w in to_remove_detected_both_union:
            if not w in memory["union"].keys():
                memory["union"][w] = 0
            memory["union"][w] += 1

        print("memory", memory)

        print("to_remove_detected_rares", to_remove_detected_rares)
        print("to_remove_detected_overall", to_remove_detected_overall)
        print("to_remove_detected_both_intersection", to_remove_detected_both_intersection)
        print("to_remove_detected_both_union", to_remove_detected_both_union)

    
        end_time = time.time()
        time_taken = end_time - start_time
        print(f'Time taken for validation is {time_taken}')

        models_without_outliers = [workers_baseline[index].model for index in workers_baseline]
        models_with_outliers_no_filter = [workers_yes_rares_no_filter[index].model for index in workers_yes_rares_no_filter]
        
        models_with_outliers_rares_filter = []
        models_with_rares_overall_filter = []
        models_with_rares_both_filters_intersection = []
        models_with_rares_both_filters_union = []

        # for w in workers_yes_rares_no_filter:
        #     if not w in to_remove_detected_rares:
        #         models_with_outliers_rares_filter.append(workers_yes_rares_no_filter[w].model)
        # for w in workers_yes_rares_overall_filter:
        #     if not w in to_remove_detected_overall:
        #         models_with_rares_overall_filter.append(workers_yes_rares_overall_filter[w].model)
        # for w in workers_yes_rares_both_filters_intersection:
        #     if not w in to_remove_detected_both_intersection:
        #         models_with_rares_both_filters_intersection.append(workers_yes_rares_both_filters_intersection[w].model)
        # for w in workers_yes_rares_both_filters_union:
        #     if not w in to_remove_detected_both_union:
        #         models_with_rares_both_filters_union.append(workers_yes_rares_both_filters_union[w].model)


        for w in workers_yes_rares_rares_filter:
            models_with_outliers_rares_filter += [(workers_yes_rares_rares_filter[w].model, workers_yes_rares_rares_filter[w].id)]
        for w in workers_yes_rares_overall_filter:
            models_with_rares_overall_filter += [(workers_yes_rares_overall_filter[w].model, workers_yes_rares_overall_filter[w].id)]
        for w in workers_yes_rares_both_filters_intersection:
            models_with_rares_both_filters_intersection += [(workers_yes_rares_both_filters_intersection[w].model, workers_yes_rares_both_filters_intersection[w].id)]
        for w in workers_yes_rares_both_filters_union:
            models_with_rares_both_filters_union += [(workers_yes_rares_both_filters_union[w].model, workers_yes_rares_both_filters_union[w].id)]

        # print("len(models_with_outliers_rares_filter)", len(models_with_outliers_rares_filter))
        # print("len(models_with_rares_overall_filter)", len(models_with_rares_overall_filter))
        # print("len(models_with_rares_both_filters_intersection)", len(models_with_rares_both_filters_intersection))
        # print("len(models_with_rares_both_filters_union)", len(models_with_rares_both_filters_union))

        model_without_outliers_aggreated = aggregate_model(models_without_outliers, device)
        model_with_outliers_no_filter_aggregated = aggregate_model(models_with_outliers_no_filter, device)


        # model_with_outliers_rares_filter_aggregated = aggregate_model(models_with_outliers_rares_filter, device)
        # model_with_rare_overall_filter_aggregated = aggregate_model(models_with_rares_overall_filter, device)
        # model_with_rare_both_filters_aggregated_intersection = aggregate_model(models_with_rares_both_filters_intersection, device)
        # model_with_rare_both_filters_aggregated_union = aggregate_model(models_with_rares_both_filters_union, device)

        model_with_outliers_rares_filter_aggregated = aggregate_model_weighted(models_with_outliers_rares_filter, memory["rares"], itr, iterations)
        model_with_rare_overall_filter_aggregated = aggregate_model_weighted(models_with_rares_overall_filter, memory["overall"], itr, iterations)
        model_with_rare_both_filters_aggregated_intersection = aggregate_model_weighted(models_with_rares_both_filters_intersection, memory["intersection"], itr, iterations)
        model_with_rare_both_filters_aggregated_union = aggregate_model_weighted(models_with_rares_both_filters_union, memory["union"], itr, iterations)

        save_np_to_file(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/models/', f'test_{experiment_counter}_model_without_rares_aggreated', model_without_outliers_aggreated)
        save_np_to_file(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/models/', f'test_{experiment_counter}_model_with_rares_no_filter_aggregated', model_with_outliers_no_filter_aggregated)
        save_np_to_file(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/models/', f'test_{experiment_counter}_model_with_rares_rares_filter_aggregated', model_with_outliers_rares_filter_aggregated)
        save_np_to_file(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/models/', f'test_{experiment_counter}_model_with_rare_overall_filter_aggregated', model_with_rare_overall_filter_aggregated)
        save_np_to_file(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/models/', f'test_{experiment_counter}_model_with_rare_both_filters_aggregated', model_with_rare_both_filters_aggregated_intersection)
        save_np_to_file(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/models/', f'test_{experiment_counter}_model_with_rare_both_filters_aggregated', model_with_rare_both_filters_aggregated_union)

        model_without_outliers = Net()
        model_without_outliers = model_without_outliers.to(device)
        for i, param in enumerate(model_without_outliers.parameters()):
            param.data = torch.from_numpy(model_without_outliers_aggreated[i]).type('torch.FloatTensor')

        model_with_outliers_no_filter = Net()
        model_with_outliers_no_filter = model_with_outliers_no_filter.to(device)
        for i, param in enumerate(model_with_outliers_no_filter.parameters()):
            param.data = torch.from_numpy(model_with_outliers_no_filter_aggregated[i]).type('torch.FloatTensor')

        model_with_outliers_rares_filter = Net()
        model_with_outliers_rares_filter = model_with_outliers_rares_filter.to(device)
        for i, param in enumerate(model_with_outliers_rares_filter.parameters()):
            param.data = torch.from_numpy(model_with_outliers_rares_filter_aggregated[i]).type('torch.FloatTensor')

        model_with_rare_overall_filter = Net()
        model_with_rare_overall_filter = model_with_rare_overall_filter.to(device)
        for i, param in enumerate(model_with_rare_overall_filter.parameters()):
            param.data = torch.from_numpy(model_with_rare_overall_filter_aggregated[i]).type('torch.FloatTensor')

        model_with_rare_both_filters_intersection = Net()
        model_with_rare_both_filters_intersection = model_with_rare_both_filters_intersection.to(device)
        for i, param in enumerate(model_with_rare_both_filters_intersection.parameters()):
            param.data = torch.from_numpy(model_with_rare_both_filters_aggregated_intersection[i]).type('torch.FloatTensor')

        model_with_rare_both_filters_union = Net()
        model_with_rare_both_filters_union = model_with_rare_both_filters_union.to(device)
        for i, param in enumerate(model_with_rare_both_filters_union.parameters()):
            param.data = torch.from_numpy(model_with_rare_both_filters_aggregated_union[i]).type('torch.FloatTensor')

        # set aggregated weights on workers
        for w in workers_baseline:
            workers_baseline[w].set_weights(model_without_outliers_aggreated)
        for w in workers_yes_rares_no_filter:
            workers_yes_rares_no_filter[w].set_weights(model_with_outliers_no_filter_aggregated)
        for w in workers_yes_rares_rares_filter:
            workers_yes_rares_rares_filter[w].set_weights(model_with_outliers_rares_filter_aggregated)
        for w in workers_yes_rares_overall_filter:
            workers_yes_rares_overall_filter[w].set_weights(model_with_rare_overall_filter_aggregated)
        for w in workers_yes_rares_both_filters_intersection:
            workers_yes_rares_both_filters_intersection[w].set_weights(model_with_rare_both_filters_aggregated_intersection)
        for w in workers_yes_rares_both_filters_union:
            workers_yes_rares_both_filters_union[w].set_weights(model_with_rare_both_filters_aggregated_union)

        model_performance_without_rares = test_worker.test_final_model(model_without_outliers)
        model_performance_with_rares_no_filter = test_worker.test_final_model(model_with_outliers_no_filter)
        model_performance_with_rares_rares_filter = test_worker.test_final_model(model_with_outliers_rares_filter)
        model_performance_with_rares_overall_filter = test_worker.test_final_model(model_with_rare_overall_filter)
        model_performance_with_rares_both_intersection_filters = test_worker.test_final_model(model_with_rare_both_filters_intersection)
        model_performance_with_rares_both_union_filters = test_worker.test_final_model(model_with_rare_both_filters_union)

        acc_performance_metrics[0][itr] = model_performance_without_rares["accuracy"]
        acc_performance_metrics[1][itr] = model_performance_with_rares_no_filter["accuracy"]
        acc_performance_metrics[2][itr] = model_performance_with_rares_rares_filter["accuracy"]
        acc_performance_metrics[3][itr] = model_performance_with_rares_overall_filter["accuracy"]
        acc_performance_metrics[4][itr] = model_performance_with_rares_both_intersection_filters["accuracy"]
        acc_performance_metrics[5][itr] = model_performance_with_rares_both_union_filters["accuracy"]

        this_run_results = []
        this_run_results.append(itr)
        this_run_results.append(model_performance_without_rares["loss"])
        this_run_results.append(model_performance_without_rares["f1"])
        this_run_results.append(model_performance_without_rares["accuracy"])

        this_run_results.append(model_performance_with_rares_no_filter["loss"])
        this_run_results.append(model_performance_with_rares_no_filter["f1"])
        this_run_results.append(model_performance_with_rares_no_filter["accuracy"])

        this_run_results.append(model_performance_with_rares_rares_filter["loss"])
        this_run_results.append(model_performance_with_rares_rares_filter["f1"])
        this_run_results.append(model_performance_with_rares_rares_filter["accuracy"])

        this_run_results.append(model_performance_with_rares_overall_filter["loss"])
        this_run_results.append(model_performance_with_rares_overall_filter["f1"])
        this_run_results.append(model_performance_with_rares_overall_filter["accuracy"])

        this_run_results.append(model_performance_with_rares_both_intersection_filters["loss"])
        this_run_results.append(model_performance_with_rares_both_intersection_filters["f1"])
        this_run_results.append(model_performance_with_rares_both_intersection_filters["accuracy"])

        this_run_results.append(model_performance_with_rares_both_union_filters["loss"])
        this_run_results.append(model_performance_with_rares_both_union_filters["f1"])
        this_run_results.append(model_performance_with_rares_both_union_filters["accuracy"])

        print("this round accuracies:")
        print("model_performance_with_rares_no_filter[accuracy]", model_performance_with_rares_no_filter["accuracy"])
        print("model_performance_with_rares_rares_filter[accuracy]", model_performance_with_rares_rares_filter["accuracy"])
        print("model_performance_with_rares_overall_filter[accuracy]", model_performance_with_rares_overall_filter["accuracy"])
        print("model_performance_with_rares_both_filters[accuracy] inters", model_performance_with_rares_both_intersection_filters["accuracy"])
        print("model_performance_with_rares_both_filters[accuracy] union", model_performance_with_rares_both_union_filters["accuracy"])
        print("this round losses:")
        print("model_performance_with_rares_no_filter[loss]", model_performance_with_rares_no_filter["loss"])
        print("model_performance_with_rares_rares_filter[loss]", model_performance_with_rares_rares_filter["loss"])
        print("model_performance_with_rares_overall_filter[loss]", model_performance_with_rares_overall_filter["loss"])
        print("model_performance_with_rares_both_filters[loss] inters", model_performance_with_rares_both_intersection_filters["loss"])
        print("model_performance_with_rares_both_filters[loss] union", model_performance_with_rares_both_union_filters["loss"])

        csv_results.append(this_run_results)

        save_2d_matrix_to_csv_file(f'./results/exp2C_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/csvs/', f'test_{experiment_counter}.csv', csv_results)

    plt.figure(figsize = (5,5))
    plt.xlabel('Rounds')
    plt.ylabel('Accuracy [%]')
    plt.ylim([30, 90])
    plt.plot(range(iterations), (acc_performance_metrics[1])*100, label='No filter', linestyle = ':', color="grey")
    plt.plot(range(iterations), (acc_performance_metrics[2])*100, label='Rares filter', linestyle = '--')
    plt.plot(range(iterations), (acc_performance_metrics[3])*100, label='Overall filter', linestyle = '-.')
    plt.plot(range(iterations), (acc_performance_metrics[3])*100, label='Both filters - union', linestyle = ':')
    plt.plot(range(iterations), (acc_performance_metrics[4])*100, label='Both filters - intersection', color="red", linestyle = '-')
    plt.axhline(y = 80, color = 'gray', linestyle = '--')
    plt.locator_params(axis="x", nbins=5)
    plt.legend()
    plt.title(f"{n_rares} nodes with rares data")
    create_folder_if_not_exists(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/pngs/')
    create_folder_if_not_exists(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/pdfs/')
    plt.savefig(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/pngs/test_{experiment_counter}.png', format="png", bbox_inches='tight')
    plt.savefig(f'./results/exp2B_rare_data_intersection_and_union_overall_scoring/{n_rares}_rares/pdfs/test_{experiment_counter}.pdf', format="pdf", bbox_inches='tight')

if __name__ == '__main__':
    
    final_data = process_data_final()
    
    for experiment_counter in range(experiments):
        for n_specials in special_options:
            print("---------------- REVIEW -------------------")
            print("running experiment:", experiment_counter)
            print("-------------------------------------------")
            experiment_rare_cases(experiment_counter, n_specials, final_data)
    play('./data/alarm.mp3')
    


# ------------------------------- TO DO ---------------------------------------------------------------------

# 1. tutti i nodi vanno bene
# 2. tutti i nodi malevoli (malevoli inclusi)
# 3. detection dei nodi malevoli con il nostro algoritmo
# 4. confronto con il loro approccio

# graph A: 1,2,3
# graph B: 3,4
# graph C: confronto tempi di inferenza tra la nostra soluzione e trustFed
# graph D: cercare i casi rari, o nei tempi di rottura o nei valori dentro al training

# -----------------------------------------------------------------------------------------------------------

# quanti nodi riusciamo a detect noi e quanti nodi riescono a fare detection loro
# metriche di misurazione dell'accuratezza diverse (f1, MAPE, R2)
# trustfed non prioritizza i nodi con loss piu' bassa

# fare forgiatura e far vedere come il loro fa schifo
# mantenere quindi una parte del dataset per fare il testing finale, il loro modello deve fare schifo
# il nostro deve passare

# trustfullness del nodo equivale al peso di aggregazione

# last but not least
# risoluzione caso raro: quelli che hanno RUL < 10
# il loro non deve passare perche' vengono aggregati anche i nodi che 
# non riescono ad identificare i casi rari
# mentre la nostra soluzione ci deve riuscire