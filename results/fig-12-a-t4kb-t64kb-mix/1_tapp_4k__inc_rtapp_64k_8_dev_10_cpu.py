import argparse
import os.path
import subprocess
import numpy as np
import pickle
import matplotlib.pyplot as plt

import fio
from plt_util import *

# Machine-dependent settings
t_app_num = [0, 1, 2, 4, 8, 16, 32]
schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']

# Machine-dependent settings done

# settings
results_root = 'results_tapp_4k_inc_rtapp_64k_8_dev_10_cpu'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
fig_name_prefix = 'tapp_4k_inc_rtapp_64k_8_dev_10_cpu'

# # Read and parse results, throughput

# Read and parse results, throughput
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'read:clat_ns:percentile:99.000000', 'usr_cpu', 'sys_cpu', 'ctx',
    'read:clat_ns:percentile:95.000000', 'read:bw'
]

total_iops_results = {}
total_bw_results = {}
fg_iops_results = {}
fg_iops_stddev = {}
fg_bw_results = {}

save_parsed_latency_log = False
for cur_sched in schedulers:
    total_iops_results[cur_sched] = []
    total_bw_results[cur_sched] = []
    fg_iops_results[cur_sched] = []
    fg_iops_stddev[cur_sched] = []
    fg_bw_results[cur_sched] = []
    for cur_t_app_num in t_app_num:
        cur_total_iops = 0
        cur_total_bandwidth = 0
        # Start T-64k-apps
        if cur_t_app_num != 0:
            for cur_t_index in range(1, cur_t_app_num + 1):
                output_file = 't_64k_dev_1_sche_{}_num_t_{}_index_{}.txt'.format(
                    cur_sched, cur_t_app_num, cur_t_index)
                output_file = os.path.join(fio_results_dir, output_file)
                _, j_res = fio.parse_experiment(output_file, global_rk,
                                                jobs_rk)
                j_res = j_res[0]
                cur_total_iops += j_res['read:iops'] / 1000  # KIOPS
                cur_total_bandwidth += j_res['read:bw'] / 1024  # GB/s

        # T-4k-app
        output_file = 't_4k_dev_1_sche_{}_num_t_{}.txt'.format(
            cur_sched, cur_t_app_num)
        output_file = os.path.join(fio_results_dir, output_file)
        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]

        cur_total_iops += j_res['read:iops'] / 1000  # KIOPS
        cur_total_bandwidth += j_res['read:bw'] / 1024  # GB/s

        total_iops_results[cur_sched].append(cur_total_iops)
        total_bw_results[cur_sched].append(cur_total_bandwidth)

        fg_iops_results[cur_sched].append(j_res['read:iops'] / 1000)  # KIOPS
        fg_iops_stddev[cur_sched].append(j_res['read:iops_stddev'] /
                                         1000)  # KIOPS
        fg_bw_results[cur_sched].append(j_res['read:bw'] / 1024 / 1024)  # GB/s

# Global parameters
linewidth = 4
markersize = 15

datalabel_size = 36
datalabel_va = 'bottom'
axis_tick_font_size = 46
axis_label_font_size = 52
legend_font_size = 46

# global config for plot
legend_label = {
    'none': 'None',
    'kyber': 'Kyber',
    'bfq': 'BFQ',
    'mq-deadline': 'MQ-DL'
}

############################################
# FG Throughput (IOPS)
############################################
if True:
    group_list = schedulers
    y_values = fg_iops_results
    std_dev = fg_iops_stddev
    x_ticks = t_app_num
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL'
    }

    title = None
    xlabel = 'Concurrent applications'
    ylabel = 'Throughput (KIOPS)'
    fig_save_path = 'fig-12a-' + fig_name_prefix + '_iops_fg.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    plt.xlabel(xlabel, fontsize=axis_label_font_size)
    plt.ylabel(ylabel, fontsize=axis_label_font_size)
    plt.grid(True)
    plt.yscale('symlog', linthresh=1e-4)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks(range(1, len(x_ticks) + 1), x_ticks)
    # ax.yaxis.set_ticks([0, 100, 200, 300, 400])
    ax.yaxis.set_ticks([0.1, 1, 10, 100])
    ax.set_xlim([0.8, len(x_ticks) + 0.5])
    ax.set_ylim([0.1, 420])

    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        y = y_values[group_name][0:len(t_app_num)]
        x = range(1, len(y) + 1)
        yerr = std_dev[group_name][0:len(t_app_num)]

        plt.errorbar(
            x,
            y,
            yerr=yerr,
            label=legend_label[group_name],
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )
        # Add data label
        # for i in range(len(data_label)):
        #     ax.text(x[i], y[i], data_label[i], size=datalabel_size)

    plt.legend(fontsize=legend_font_size,
               labelspacing=0.1,
               ncol=2,
               columnspacing=0.2,
               borderpad=0.2)

    plt.savefig(fig_save_path, bbox_inches='tight')

# ##########################
# # Total Bandwidth
# ##########################
# if True:
#     # Data, set unused value to none
#     group_list = schedulers
#     y_values = total_bw_results
#     std_dev = None

#     title = None
#     xlabel = 'Concurrent applications'
#     ylabel = 'Bandwidth (GiB/s)'
#     fig_save_path = fig_name_prefix + '_total_bw.pdf'
#     fig_save_path = os.path.join(fig_dir, fig_save_path)

#     reset_color()
#     fig, ax = plt.subplots(figsize=(12, 8))

#     plt.xlabel(xlabel, fontsize=axis_label_font_size)
#     plt.ylabel(ylabel, fontsize=axis_label_font_size)
#     plt.grid(True)

#     ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
#     ax.xaxis.set_ticks(range(1, len(x_ticks) + 1), x_ticks)
#     ax.set_xlim([0.8, len(x_ticks) + 0.5])
#     ax.yaxis.set_ticks([0, 5, 10, 15])
#     ax.set_ylim(0, 16)

#     for (index, group_name) in zip(range(len(group_list)), group_list):
#         # x, y, std_dev, data_label = data[group_name]
#         x = range(1, len(y) + 1)
#         y = y_values[group_name]
#         y = [i / 1024 for i in y]
#         yerr = None
#         if std_dev:
#             yerr = std_dev[group_name]
#             yerr = [i / 1024 for i in yerr]

#         plt.errorbar(
#             x,
#             y,
#             yerr=yerr,
#             label=legend_label[group_name],
#             marker=dot_style[index % len(dot_style)],
#             linewidth=linewidth,
#             markersize=markersize,
#             # color = get_next_color(),
#         )
#         # Add data label
#         # for i in range(len(data_label)):
#         #     ax.text(x[i], y[i], data_label[i], size=datalabel_size)

#     # if legend_label != None:
#     #     plt.legend(fontsize=legend_font_size, labelspacing=0.1)
#     # plt.legend(fontsize=legend_font_size,
#     #            ncol=2,
#     #            loc='upper left',
#     #            bbox_to_anchor=(0, 1.2),
#     #            columnspacing=0.3)

#     plt.savefig(fig_save_path, bbox_inches='tight')
