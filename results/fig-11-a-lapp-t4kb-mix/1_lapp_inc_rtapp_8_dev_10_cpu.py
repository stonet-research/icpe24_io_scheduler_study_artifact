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

# settings
results_root = 'results_lapp_inc_rtapp_8_dev_10_cpu'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
latency_log_dir = os.path.join(results_root, 'latency_log')
parsed_file_dir = os.path.join(results_root, 'parsed_file')
fig_name_prefix = 'lapp_inc_rtapp_8_dev_10_cpu'

# Read and parse results, throughput
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'read:clat_ns:percentile:99.000000', 'usr_cpu', 'sys_cpu', 'ctx',
    'read:clat_ns:percentile:95.000000', 'read:bw'
]

total_iops_results = {}
total_bw_results = {}
lapp_avg_latency_results = {}
lapp_avg_latency_stddev = {}
lapp_p95_tail_latency_results = {}
lapp_p99_tail_latency_results = {}

save_parsed_latency_log = False
for cur_sched in schedulers:
    total_iops_results[cur_sched] = []
    total_bw_results[cur_sched] = []
    lapp_avg_latency_results[cur_sched] = []
    lapp_avg_latency_stddev[cur_sched] = []
    lapp_p95_tail_latency_results[cur_sched] = []
    lapp_p99_tail_latency_results[cur_sched] = []

    for cur_t_app_num in t_app_num:
        cur_total_iops = 0
        cur_total_bandwidth = 0

        # T-apps
        if cur_t_app_num != 0:
            for cur_t_index in range(1, cur_t_app_num + 1):
                output_file = 't_dev_1_sche_{}_num_t_{}_index_{}.txt'.format(
                    cur_sched, cur_t_app_num, cur_t_index)
                output_file = os.path.join(fio_results_dir, output_file)
                _, j_res = fio.parse_experiment(output_file, global_rk,
                                                jobs_rk)
                j_res = j_res[0]
                cur_total_iops += j_res['read:iops'] / 1000  # KIOPS
                cur_total_bandwidth += j_res['read:bw'] / 1024 / 1024  # GB/s

        # L-app
        output_file = 'l_dev_1_sche_{}_num_t_{}.txt'.format(
            cur_sched, cur_t_app_num)
        output_file = os.path.join(fio_results_dir, output_file)
        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        lapp_avg_latency_results[cur_sched].append(j_res['read:lat_ns:mean'] /
                                                   1000)
        lapp_avg_latency_stddev[cur_sched].append(j_res['read:lat_ns:stddev'] /
                                                  1000)
        lapp_p95_tail_latency_results[cur_sched].append(
            j_res['read:clat_ns:percentile:95.000000'] / 1000)  # us
        lapp_p99_tail_latency_results[cur_sched].append(
            j_res['read:clat_ns:percentile:99.000000'] / 1000)

        cur_total_iops += j_res['read:iops'] / 1000  # KIOPS
        cur_total_bandwidth += j_res['read:bw'] / 1024 / 1024  # GB/s

        total_iops_results[cur_sched].append(cur_total_iops)
        total_bw_results[cur_sched].append(cur_total_bandwidth)

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
# P99 Tail Latency
############################################
if True:
    group_list = schedulers
    y_values = lapp_p99_tail_latency_results
    std_dev = None
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL'
    }

    title = None
    xlabel = 'Concurrent applications'
    ylabel = 'Latency (millisecond)'
    fig_save_path = 'fig-11a-' + fig_name_prefix + '_p99_lat.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    plt.xlabel(xlabel, fontsize=axis_label_font_size)
    plt.ylabel(ylabel, fontsize=axis_label_font_size)
    plt.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks(range(1, len(t_app_num) + 1), t_app_num)
    ax.yaxis.set_ticks([0, 0.05, 0.10, 0.15, 0.20])
    # ax.set_yticklabels(['0', '1,000', '2,000', '3,000', '4,000', '5,000'])
    ax.set_xlim([0, len(t_app_num) + 0.5])
    ax.set_ylim([0, 0.23])

    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        y = y_values[group_name][0:len(t_app_num)]
        y = [item / 1000 for item in y]
        x = range(1, len(y) + 1)
        yerr = None
        if std_dev:
            yerr = std_dev[group_name]

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

    plt.legend(
        fontsize=legend_font_size,
        labelspacing=0.1,
        ncol=2,
        #    loc='upper left',
        columnspacing=0.2,
        borderpad=0.2)

    plt.savefig(fig_save_path, bbox_inches='tight')
