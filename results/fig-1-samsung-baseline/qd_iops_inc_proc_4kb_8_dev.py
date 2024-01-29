import argparse
import os.path
import subprocess

import fio

# Machine-dependent settings
num_proc = ['1', '2', '4', '6', '8', '10', '16']
all_qd = ['1', '2', '4', '8', '16', '32', '64', '128', '256']
spdk_qd = all_qd + ['512', '1024']
bs = '4kb'

# Machine-dependent settings done

# settings
results_root = 'results_qd_iops_inc_proc_4kb_8_dev'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
fig_name_prefix = 'qd_iops_inc_proc_4kb_8_dev'

# Read and parse results, throughput
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'usr_cpu', 'sys_cpu', 'read:bw'
    #'read:clat_ns:percentile:99.900000'
]

iops_results = {}
iops_stddev = {}
avg_lat_results = {}
cpu_results = {}
bw_results = {}

# Linux storage stack
for cur_proc in num_proc:
    iops_results[cur_proc] = []
    iops_stddev[cur_proc] = []
    avg_lat_results[cur_proc] = []
    cpu_results[cur_proc] = []
    bw_results[cur_proc] = []
    for cur_qd in all_qd:
        output_file = 'bs_4_proc_{}_qd_{}.txt'.format(cur_proc, cur_qd)
        output_file = os.path.join(fio_results_dir, output_file)
        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        iops_results[cur_proc].append(j_res['read:iops'] / 1000)
        iops_stddev[cur_proc].append(j_res['read:iops_stddev'] / 1000)
        avg_lat_results[cur_proc].append(j_res['read:lat_ns:mean'] / 1000)
        cpu_results[cur_proc].append(
            (j_res['usr_cpu'] + j_res['sys_cpu']) / 100)
        bw_results[cur_proc].append(j_res['read:bw'] / 1024 / 1024)

# SPDK
spdk_iops_results = {}
spdk_iops_stddev = {}
spdk_avg_lat_results = {}
spdk_cpu_results = {}
spdk_bw_results = {}

for cur_proc in [1, 4, 5, 6]:
    spdk_iops_results[cur_proc] = []
    spdk_iops_stddev[cur_proc] = []
    spdk_avg_lat_results[cur_proc] = []
    spdk_cpu_results[cur_proc] = []
    spdk_bw_results[cur_proc] = []
    for cur_qd in spdk_qd:
        output_file = 'bs_4_proc_{}_qd_{}_spdk.txt'.format(cur_proc, cur_qd)
        output_file = os.path.join(fio_results_dir, output_file)
        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        spdk_iops_results[cur_proc].append(j_res['read:iops'] / 1000)
        spdk_iops_stddev[cur_proc].append(j_res['read:iops_stddev'] / 1000)
        spdk_avg_lat_results[cur_proc].append(j_res['read:lat_ns:mean'] / 1000)
        spdk_cpu_results[cur_proc].append(
            (j_res['usr_cpu'] + j_res['sys_cpu']) / 100)
        spdk_bw_results[cur_proc].append(j_res['read:bw'] / 1024 / 1024)

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

####################################
# Throughput: IOPS
####################################
if True:
    # Data, set unused value to none
    group_list = num_proc
    y_values_ax1 = avg_lat_results
    y_values_ax2 = cpu_results
    std_dev_ax1 = None
    std_dev_ax2 = None
    x_ticks = iops_results
    legend_label = {
        '1': '1p',
        '2': '2p',
        '4': '4p',
        '6': '6p',
        '8': '8p',
        '10': '10p',
        '16': '16p'
    }

    title = None
    xlabel = 'Throughput (MIOPS)'
    ylabel_ax1 = 'Latency ($\mu$s)'
    fig_save_path = 'fig-3c-qd-iops-inc-proc-4kb-8-dev.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel_ax1, fontsize=axis_label_font_size)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks([1, 2, 3, 4, 5])
    ax.set_xlim([0, 5.5])
    ax.set_ylim([0, 1000])

    # Throughput storage stack
    group_list = ['1', '2', '4', '8', '10', '16']
    for (index, group_name) in zip(range(len(group_list)), group_list):
        if x_ticks:
            x = x_ticks[group_name]
        y = y_values_ax1[group_name]
        y = [i for i in y if i < 1000]
        x = x[:len(y)]
        yerr = None
        if std_dev_ax1:
            yerr = std_dev_ax1[group_name]
        label = legend_label[group_name]
        x = [i / 1000 for i in x]
        ax.errorbar(
            x,
            y,
            yerr=yerr,
            label=label,
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )

    # Throughput SPDK
    # group_list = [1, 4, 5, 6]
    group_list = [1, 6]
    y_values_ax1 = spdk_avg_lat_results
    std_dev_ax1 = None
    x_ticks = spdk_iops_results
    legend_label = {1: '1p SPDK', 4: '4p SPDK', 5: '5p SPDK', 6: '6p SPDK'}
    for (index, group_name) in zip(range(len(group_list)), group_list):
        if x_ticks:
            x = x_ticks[group_name]
        y = y_values_ax1[group_name]
        y = [i for i in y if i < 1000]
        x = x[:len(y)]
        yerr = None
        if std_dev_ax1:
            yerr = std_dev_ax1[group_name]
        label = legend_label[group_name]
        x = [i / 1000 for i in x]
        ax.errorbar(
            x,
            y,
            yerr=yerr,
            label=label,
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )

    ax.legend(
        fontsize=legend_font_size - 4,
        ncol=4,
        loc='upper left',
        bbox_to_anchor=(-0.003, 1.022),
        handlelength=1.5,
        handletextpad=0.2,
        columnspacing=0.2,
        labelspacing=0,
        borderpad=0,
    )

    plt.savefig(fig_save_path, bbox_inches='tight')
