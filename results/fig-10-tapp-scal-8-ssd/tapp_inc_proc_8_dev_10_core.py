import argparse
import os.path
import subprocess

import fio

# Machine-dependent settings
max_process = 15
schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']

# settings
results_root = 'results_tapp_inc_proc_8_dev_10_core'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
fig_name_prefix = 'tapp_inc_proc_8_dev_10_core'

# # Read and parse results, throughput

global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'usr_cpu', 'sys_cpu', 'read:bw'
    #'read:clat_ns:percentile:99.900000'
]

schedulers.append('spdk')
iops_results = {}
iops_stddev = {}
cpu_results = {}
bw_results = {}
for cur_sched in schedulers:
    iops_results[cur_sched] = []
    iops_stddev[cur_sched] = []
    cpu_results[cur_sched] = []
    bw_results[cur_sched] = []
    for cur_num_process in range(1, max_process + 1):
        output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
            cur_num_process, 1, cur_sched)
        output_file = os.path.join(fio_results_dir, output_file)

        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        iops_results[cur_sched].append(j_res['read:iops'] / 1000)
        iops_stddev[cur_sched].append(j_res['read:iops_stddev'] / 1000)
        cpu_results[cur_sched].append(
            (j_res['usr_cpu'] + j_res['sys_cpu']) * cur_num_process / 100)
        bw_results[cur_sched].append(j_res['read:bw'] / 1024 / 1024)

import matplotlib
import matplotlib.pyplot as plt

# Switch to Type 1 Fonts.
# matplotlib.rcParams['text.usetex'] = True
# plt.rc('font', **{'family': 'serif', 'serif': ['Times']})

matplotlib_color = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5']
m_color_index = 0

matplotlib_colors = [
    'blue', 'green', 'red', 'cyan', 'magenta', 'yellw', 'white'
]

dot_style = [
    '+',
    'X',
    'o',
    'v',
    's',
    'P',
]


def get_next_color():
    global m_color_index
    c = matplotlib_color[m_color_index]
    m_color_index += 1

    return c


def reset_color():
    global m_color_index
    m_color_index = 0


# Global parameters
linewidth = 4
markersize = 15

datalabel_size = 36
datalabel_va = 'bottom'
axis_tick_font_size = 46
axis_label_font_size = 52
legend_font_size = 46

for sched in schedulers:
    print(sched, '\n', iops_results[sched])
########################
# Throughput
########################
if True:
    # Data, set unused value to none
    group_list = schedulers
    y_values = iops_results
    std_dev = None
    x_ticks = range(1, 21)
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL',
        'spdk': "SPDK"
    }

    title = None
    xlabel = 'Number of processes'
    ylabel = 'Throughput (MIOPS)'
    fig_save_path = 'fig-10-a-tapp-inc-proc-8-dev-10-core.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel, fontsize=axis_label_font_size)
    # plt.grid(True)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks([0, 1, 3, 5, 7, 9, 11, 13, 15])
    ax.set_xlim([0, 15.5])
    ax.set_ylim([0, 6])

    # Throughput
    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        x = range(1, len(y_values[group_name]) + 1)
        y = y_values[group_name]
        y = [i / 1000 for i in y]
        yerr = None
        if std_dev:
            yerr = std_dev[group_name]

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            label=legend_label[group_name],
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )

    # None
    plt.annotate('',
                 xy=(10, 3.42),
                 xytext=(11, 3.7),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(11, 3.6, '3.42 MIOPS', size=datalabel_size)
    # BFQ
    plt.annotate('',
                 xy=(10, 1.27),
                 xytext=(11, 1),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(11, 0.9, '1.26 MIOPS', size=datalabel_size)
    # Kyber
    plt.annotate('',
                 xy=(10, 2.67),
                 xytext=(11, 3),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(11, 2.9, '2.67 MIOPS', size=datalabel_size)
    # MQ-DL
    plt.annotate('',
                 xy=(10, 1.90),
                 xytext=(11, 2.3),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(11, 2.2, '1.90 MIOPS', size=datalabel_size)

    # SPDK
    plt.annotate('',
                 xy=(9, 5.45),
                 xytext=(11, 4.3),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(11, 4.3, '5.45 MIOPS', size=datalabel_size)

    plt.savefig(fig_save_path, bbox_inches='tight')

    # Add legend
    ax.legend(
        fontsize=legend_font_size,
        ncol=1,
        loc='upper left',
        bbox_to_anchor=(-0.02, 1.05),
        labelspacing=0,
        handlelength=1,
        handletextpad=0.3,
        columnspacing=0.,
        borderpad=0.,
    )

    plt.savefig(fig_save_path, bbox_inches='tight')

# ####################################
# # CPU
# ####################################
# if True:
#     # Data, set unused value to none
#     group_list = schedulers
#     y_values = cpu_results
#     std_dev = None
#     x_ticks = range(1, 21)
#     legend_label = {
#         'none': 'None',
#         'kyber': 'Kyber',
#         'bfq': 'BFQ',
#         'mq-deadline': 'MQ-DL',
#         'spdk': "SPDK"
#     }

#     title = None
#     xlabel = 'Number of processes'
#     ylabel = 'CPU usage'
#     fig_save_path = 'fig-10-a-tapp-inc-proc-8-dev-10-core-cpu.pdf'

#     reset_color()
#     fig, ax = plt.subplots(figsize=(12, 8))

#     ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
#     ax.set_ylabel(ylabel, fontsize=axis_label_font_size)
#     # plt.grid(True)
#     ax.grid(True)

#     ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
#     ax.xaxis.set_ticks([0, 1, 3, 5, 7, 9, 11, 13, 15])
#     ax.yaxis.set_ticks([0, 2, 4, 6, 8, 10])
#     ax.set_xlim([0, 15.5])
#     ax.set_ylim([0, 10.5])

#     # Throughput
#     for (index, group_name) in zip(range(len(group_list)), group_list):
#         x = range(1, len(y_values[group_name]) + 1)
#         y = y_values[group_name]
#         yerr = None
#         ax.errorbar(
#             x,
#             y,
#             yerr=yerr,
#             label=legend_label[group_name],
#             marker=dot_style[index % len(dot_style)],
#             linewidth=linewidth,
#             markersize=markersize,
#         )

#     plt.savefig(fig_save_path, bbox_inches='tight')