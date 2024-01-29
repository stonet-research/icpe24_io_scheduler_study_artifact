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
results_root = 'results_lapp_inc_wtapp_8_dev_10_cpu'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
latency_log_dir = os.path.join(results_root, 'latency_log')
parsed_file_dir = os.path.join(results_root, 'parsed_file')
fig_name_prefix = 'lapp_inc_wtapp_8_dev_10_cpu'
os.mkdir(results_root)

FIO_RAMP_TIME = 600
FIO_RUN_TIME = 600

# Parameters for plot
USE_LAT_SAMPLE = True
LOG_SAMPLE_SIZE = 10000

# Parse command line settings
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-r',
                    '--run',
                    action='store_true',
                    help='Run the experiment')
parser.add_argument('-p',
                    '--print_only',
                    action='store_true',
                    help='Only print the command')
parser.add_argument('--fio',
                    action='store',
                    default='fio',
                    help='Path to the fio executable')
parser.add_argument('--debug',
                    action='store_true',
                    help='Run experiments with short time')
parser.add_argument(
    '--dev',
    action='store',
    default='',
    help=
    'Storage devices to be tested, separated by : if there are multiple devices'
)
parser.add_argument(
    '--spdk_dev',
    action='store',
    default='',
    help=
    'Storage devices to be tested, separated by : if there are multiple devices for SPDK'
)
parser.add_argument('--spdk_dir',
                    action='store',
                    default='',
                    help='Path to SPDK isntallation directory')
args = parser.parse_args()
config = vars(args)
print(config)

# Update constants
FIO_CMD = config['fio']
devices = config['dev']
spdk_devices = config['spdk_dev']
SPDK_DIR = config['spdk_dir']
SPDK_FIO_PLUGIN = os.path.join(SPDK_DIR, 'build/fio/spdk_nvme')

if config['debug']:
    FIO_RAMP_TIME = 3
    FIO_RUN_TIME = 5

## construct fio options
ENGINE_OPTIONS = '--ioengine=io_uring --registerfiles=1 --fixedbufs=1'
FIO_OPTIONS = '--size=100% --norandommap=1 --group_reporting=1 --direct=1 --allow_file_create=0 --output-format=json'
FIO_TIME_OPTIONS = '--time_based=1 --ramp_time={}s --runtime={}s'.format(
    FIO_RAMP_TIME, FIO_RUN_TIME)
FIO_FILE = '--filename=' + devices
FIO_JOBS = '--name=1'
FIO_COMMAND_GENERAL = ' '.join(
    [FIO_TIME_OPTIONS, ENGINE_OPTIONS, FIO_OPTIONS, FIO_FILE, FIO_JOBS])


def exec_cmd(cmd):
    print(cmd)
    if config['print_only']:
        return

    res = subprocess.run(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         shell=True,
                         check=True)
    print(res.stdout)
    print(res.stderr)


def exec_cmd_background(cmd):
    print(cmd)
    if config['print_only']:
        return

    p = subprocess.Popen(
        cmd,
        #stdout=subprocess.PIPE,
        #stderr=subprocess.STDOUT,
        shell=True)
    return p


if config['run']:
    os.mkdir(fio_results_dir)
    os.mkdir(latency_log_dir)
    os.mkdir(parsed_file_dir)
    for cur_t_app_num in t_app_num:
        for cur_sched in schedulers:
            all_proc = []
            # Start T-apps
            if cur_t_app_num != 0:
                for cur_t_index in range(1, cur_t_app_num + 1):
                    output_file = 't_dev_1_sche_{}_num_t_{}_index_{}.txt'.format(
                        cur_sched, cur_t_app_num, cur_t_index)
                    output_file = os.path.join(fio_results_dir, output_file)
                    scheduler_option = '--ioscheduler=' + cur_sched
                    bs_option = '--bs=4k'
                    io_depth_option = '--iodepth=128'
                    rw_option = '--rw=randwrite'
                    fio_option_cur = ' '.join(
                        [scheduler_option, bs_option, io_depth_option])
                    cur_fio_command = ' '.join([
                        FIO_CMD, fio_option_cur, rw_option,
                        FIO_COMMAND_GENERAL, '-o', output_file
                    ])

                    # execute command
                    p = exec_cmd_background(cur_fio_command)
                    all_proc.append(p)

            # L-app
            output_file = 'l_dev_1_sche_{}_num_t_{}.txt'.format(
                cur_sched, cur_t_app_num)
            output_file = os.path.join(fio_results_dir, output_file)
            latency_log_prefix = 'lat_log_l_dev_1_sche_{}_num_t_{}.txt'.format(
                cur_sched, cur_t_app_num)
            latency_log_prefix = os.path.join(latency_log_dir,
                                              latency_log_prefix)
            scheduler_option = '--ioscheduler=' + cur_sched
            bs_option = '--bs=4k'
            io_depth_option = '--iodepth=1'
            rw_option = '--rw=randread'
            latency_log_option = '--write_lat_log=' + latency_log_prefix
            fio_option_cur = ' '.join([
                scheduler_option, bs_option, rw_option, io_depth_option,
                latency_log_option
            ])
            cur_fio_command = ' '.join([
                FIO_CMD, fio_option_cur, FIO_COMMAND_GENERAL, '-o', output_file
            ])

            # execute command
            p = exec_cmd_background(cur_fio_command)
            all_proc.append(p)

            for p in all_proc:
                p.wait()

# Read and parse results, throughput
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'read:clat_ns:percentile:99.000000', 'usr_cpu', 'sys_cpu', 'ctx',
    'read:clat_ns:percentile:95.000000', 'read:bw'
]
write_jobs_rk = ['write:iops', 'write:iops_stddev', 'write:bw']

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

        # T-apps: write
        if cur_t_app_num != 0:
            for cur_t_index in range(1, cur_t_app_num + 1):
                output_file = 't_dev_1_sche_{}_num_t_{}_index_{}.txt'.format(
                    cur_sched, cur_t_app_num, cur_t_index)
                output_file = os.path.join(fio_results_dir, output_file)
                _, j_res = fio.parse_experiment(output_file, global_rk,
                                                write_jobs_rk)
                j_res = j_res[0]
                cur_total_iops += j_res['write:iops'] / 1000  # KIOPS
                cur_total_bandwidth += j_res['write:bw'] / 1024 / 1024  # GB/s

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

# from plt_util import *

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
    fig_save_path = 'fig-11c-' + fig_name_prefix + '_p99_lat.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    plt.xlabel(xlabel, fontsize=axis_label_font_size)
    plt.ylabel(ylabel, fontsize=axis_label_font_size)
    plt.grid(True)
    # ax.set_yscale('log')

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks(range(1, len(t_app_num) + 1), t_app_num)
    ax.set_xlim([0, len(t_app_num) + 0.5])
    # ax.yaxis.set_ticks([0, 1000, 2000, 3000, 4000, 5000])
    # ax.set_yticklabels(['0', '1,000', '2,000', '3,000', '4,000', '5,000'])
    # ax.set_ylim([0, 5300])
    # ax.set_ylim([1, 1000])

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

    plt.savefig(fig_save_path, bbox_inches='tight')
