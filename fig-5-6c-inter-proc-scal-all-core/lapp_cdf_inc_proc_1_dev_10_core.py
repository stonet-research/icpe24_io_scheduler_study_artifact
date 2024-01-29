import argparse
import os.path
import subprocess
import pickle
import numpy as np

import fio
from util import *

# Machine-dependent settings
num_processes = ['1', '2', '4', '8', '16', '32', '64', '128', '256']
schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']
log_sample_size = 10000

# Some settings that control which data will be processed
lat_load_sample = True  # load sampled latency data

# settings
results_root = 'results_lapp_cdf_inc_proc_1_dev_10_core'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
latency_log_dir = os.path.join(results_root, 'latency_log')
parsed_file_dir = os.path.join(results_root, 'parsed_file')

fig_name_prefix = 'lapp_cdf_inc_proc_1_dev_10_core'

FIO_RAMP_TIME = 30
FIO_RUN_TIME = 120

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
FIO_OPTIONS = '--size=100% --bs=4kb --norandommap=1 --group_reporting=1 --direct=1 --rw=randread --allow_file_create=0 --iodepth=1 --output-format=json'.format(
    FIO_RAMP_TIME, FIO_RUN_TIME)
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


if config['run']:
    os.makedirs(fio_results_dir)
    os.makedirs(latency_log_dir)
    os.makedirs(parsed_file_dir)
    for cur_num_process in num_processes:
        for cur_sched in schedulers:
            output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
                cur_num_process, 1, cur_sched)
            output_file = os.path.join(fio_results_dir, output_file)

            latency_log_prefix = 'lat_log_proc_{}_dev_{}_sche_{}'.format(
                cur_num_process, 1, cur_sched)
            latency_log_prefix = os.path.join(latency_log_dir,
                                              latency_log_prefix)

            scheduler_option = '--ioscheduler=' + cur_sched
            jobs = '--numjobs=' + cur_num_process
            latency_log_option = '--write_lat_log=' + latency_log_prefix
            fio_option_cur = ' '.join([scheduler_option, jobs])

            cur_fio_command = ' '.join([
                FIO_CMD, fio_option_cur, FIO_COMMAND_GENERAL, '-o',
                output_file, latency_log_option
            ])

            # execute command
            exec_cmd(cur_fio_command)

latency_log = {}
s_latency_log = {}
c_latency_log = {}

## Parse log
# If the data has been processed, load them directly
if os.path.exists(parsed_file_dir) and os.path.exists(
        os.path.join(parsed_file_dir, 'sampled_latency_log.pkl')):
    print('Pre-parsed file found, load parsed file directly.')

    if lat_load_sample:
        latency_log = pickle_load(
            os.path.join(parsed_file_dir, 'sampled_' + 'latency_log.pkl'))
        s_latency_log = pickle_load(
            os.path.join(parsed_file_dir, 'sampled_' + 's_latency_log.pkl'))
        c_latency_log = pickle_load(
            os.path.join(parsed_file_dir, 'sampled_' + 'c_latency_log.pkl'))
    else:
        latency_log = pickle_load(
            os.path.join(parsed_file_dir, 'latency_log.pkl'))
        s_latency_log = pickle_load(
            os.path.join(parsed_file_dir, 's_latency_log.pkl'))
        c_latency_log = pickle_load(
            os.path.join(parsed_file_dir, 'c_latency_log.pkl'))

else:
    # Parsed files do not exit, parse the original files
    print('Parse file')
    for cur_sched in schedulers:
        latency_log[cur_sched] = []
        s_latency_log[cur_sched] = []
        c_latency_log[cur_sched] = []
        for cur_num_proc in num_processes:
            latency_log_prefix = 'lat_log_proc_{}_dev_{}_sche_{}'.format(
                cur_num_proc, 1, cur_sched)
            latency_log_prefix = os.path.join(latency_log_dir,
                                              latency_log_prefix)

            # parse latency log
            for cur_lat_name, cur_lat_log in zip(
                ['lat', 'slat', 'clat'],
                [latency_log, s_latency_log, c_latency_log]):
                cur_latencies = []
                for proc_index in range(1, int(cur_num_proc) + 1):
                    cur_lat_log_file = latency_log_prefix + '_' + cur_lat_name + '.' + str(
                        proc_index) + '.log'
                    print('parse: ' + cur_lat_log_file)
                    cur_latencies += fio.parse_latency_log(cur_lat_log_file)
                cur_lat_log[cur_sched].append(cur_latencies)

    # sample latency log
    for cur_file_name, cur_lat_log in zip(
        ['latency_log.pkl', 's_latency_log.pkl', 'c_latency_log.pkl'],
        [latency_log, s_latency_log, c_latency_log]):
        cur_filename = os.path.join(parsed_file_dir,
                                    'sampled_' + cur_file_name)
        cur_lat_log_sampled = {}
        for cur_sched in schedulers:
            cur_lat_log_sampled[cur_sched] = []
            for cur_latencies in cur_lat_log[cur_sched]:
                cur_lat_log_sampled[cur_sched].append(
                    sample_list(cur_latencies, log_sample_size))
        f = open(cur_filename, 'wb')
        pickle.dump(cur_lat_log_sampled, f)
        f.close()
## Parse log done

## Always parse the fio file
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'read:clat_ns:percentile:99.000000', 'usr_cpu', 'sys_cpu', 'ctx',
    'read:clat_ns:percentile:95.000000', 'read:clat_ns:percentile:99.900000',
    'read:clat_ns:percentile:90.000000'
]

iops_results = {}
iops_stddev = {}
avg_latency_results = {}
avg_latency_stddev = {}
p90_tail_latency_results = {}
p95_tail_latency_results = {}
p99_tail_latency_results = {}
p999_tail_latency_results = {}
cpu_usage_results = {}
ctx_results = {}

for cur_sched in schedulers:
    iops_results[cur_sched] = []
    iops_stddev[cur_sched] = []
    avg_latency_results[cur_sched] = []
    avg_latency_stddev[cur_sched] = []
    p90_tail_latency_results[cur_sched] = []
    p95_tail_latency_results[cur_sched] = []
    p99_tail_latency_results[cur_sched] = []
    p999_tail_latency_results[cur_sched] = []
    cpu_usage_results[cur_sched] = []
    ctx_results[cur_sched] = []

    for cur_qd in num_processes:
        output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(cur_qd, 1, cur_sched)
        output_file = os.path.join(fio_results_dir, output_file)

        latency_log_prefix = 'lat_log_proc_{}_dev_{}_sche_{}'.format(
            cur_qd, 1, cur_sched)
        latency_log_prefix = os.path.join(latency_log_dir, latency_log_prefix)

        # Parse the normal result
        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        iops_results[cur_sched].append(j_res['read:iops'] / 1000)
        iops_stddev[cur_sched].append(j_res['read:iops_stddev'] / 1000)
        avg_latency_results[cur_sched].append(j_res['read:lat_ns:mean'] / 1000)
        avg_latency_stddev[cur_sched].append(j_res['read:lat_ns:stddev'] /
                                             1000)
        p90_tail_latency_results[cur_sched].append(
            j_res['read:clat_ns:percentile:90.000000'] / 1000)
        p95_tail_latency_results[cur_sched].append(
            j_res['read:clat_ns:percentile:95.000000'] / 1000)
        p99_tail_latency_results[cur_sched].append(
            j_res['read:clat_ns:percentile:99.000000'] / 1000)
        p999_tail_latency_results[cur_sched].append(
            j_res['read:clat_ns:percentile:99.900000'] / 1000)
        cpu_usage_results[cur_sched].append(
            (j_res['usr_cpu'] + j_res['sys_cpu']) * int(cur_qd) / 100)
        ctx_results[cur_sched].append(j_res['ctx'])

print('p99')
for cur_sched in p99_tail_latency_results:
    print(cur_sched)
    print(p99_tail_latency_results[cur_sched])

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

heatmap_axis_tick_font_size = 26
heatmap_data_tag_size = 16
vmin = 0
vmax = 60

############################################
# Heatmap: Base none-qd0
############################################
if True:
    percentile_name = ['p99']
    percentile_value = [p99_tail_latency_results, p999_tail_latency_results]

    for cur_percentile_name, cur_percentile_value in zip(
            percentile_name, percentile_value):
        # Plot the difference between schedulers
        diff = []
        for cur_qd_index, cur_qd in zip(range(len(num_processes)),
                                        num_processes):
            cur_qd_diff = []
            for cur_sched_index, cur_sched in zip(range(len(schedulers)),
                                                  schedulers):
                base = cur_percentile_value['none'][0]
                qd_cur_percentile = cur_percentile_value[cur_sched][
                    cur_qd_index]
                cur_qd_diff.append(qd_cur_percentile / base)
            diff.append(cur_qd_diff)

        reset_color()
        fig_save_path = 'fig-6c-' + fig_name_prefix + '_heatmap_base_none_0_{}.pdf'.format(
            cur_percentile_name)

        scheduler_labels = ['None', 'BFQ', 'Kyber', 'MQ-DL']
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_xticks(np.arange(len(schedulers)),
                      labels=scheduler_labels,
                      fontsize=heatmap_axis_tick_font_size)
        num_proc_rev = num_processes.copy()
        num_proc_rev.reverse()
        print(num_proc_rev)
        ax.set_yticks(np.arange(len(num_proc_rev)),
                      labels=num_proc_rev,
                      fontsize=heatmap_axis_tick_font_size)

        # Rotate the tick labels and set their alignment.
        plt.setp(ax.get_xticklabels(),
                 rotation=45,
                 ha="right",
                 rotation_mode="anchor")

        diff.reverse()
        im = ax.imshow(diff,
                       cmap='plasma',
                       interpolation='nearest',
                       vmin=vmin,
                       vmax=vmax)
        color_threshold = (vmin + vmax) / 2

        for i in range(len(num_processes)):
            for j in range(len(schedulers)):
                if diff[i][j] < color_threshold:
                    color = 'w'
                else:
                    color = 'black'
                text = ax.text(j,
                               i,
                               round(diff[i][j], 1),
                               ha="center",
                               va="center",
                               color=color,
                               fontsize=heatmap_data_tag_size)

        plt.savefig(fig_save_path, bbox_inches='tight')

############################################
# Latency CDF by processes
############################################
if True:
    group_list = schedulers
    y_values = iops_results
    std_dev = iops_stddev
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL'
    }

    title = None
    xlabel = 'Latency ($\mu$s)'
    ylabel = 'Cumulative prob'

    # Group plot by processes
    for index, cur_num_proc in zip(range(len(num_processes)), num_processes):
        print('plot CDF')
        reset_color()
        fig_save_path = 'fig-5a-' + fig_name_prefix + '_cdf_proc_{}.pdf'.format(
            cur_num_proc)

        # plot
        fig, ax = plt.subplots(figsize=(12, 8))
        # ax.set_xticks([0, 1000, 2000, 3000, 4000, 5000])
        # ax.set_xticklabels(['0', '1,000', '2,000', '3,000', '4,000', '5,000'])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        # ax.set_xlim(0, 5000)
        ax.set_ylim(0, 1.1)
        # if cur_num_proc == '1':
        #     ax.set_xlim(0, 500)
        #     ax.set_xticks([0, 100, 200, 300, 400, 500])
        # elif cur_num_proc == '2':
        #     continue
        #     ax.set_xlim(0, 500)
        # elif cur_num_proc == '4':
        #     continue
        #     ax.set_xlim(0, 500)
        # elif cur_num_proc == '8':
        #     continue
        #     ax.set_xlim(0, 500)
        # elif cur_num_proc == '16':
        #     ax.set_xlim(0, 500)
        #     ax.set_xticks([0, 100, 200, 300, 400, 500])
        # elif cur_num_proc == '32':
        #     ax.set_xlim(0, 500)
        #     ax.set_xticks([0, 100, 200, 300, 400, 500])
        # elif cur_num_proc == '64':
        #     ax.set_xlim(0, 1000)
        #     ax.set_xticks([0, 200, 400, 600, 800, 1000])
        #     ax.set_xticklabels(['0', '200', '400', '600', '800', '1,000'])
        # elif cur_num_proc == '128':
        #     continue
        #     ax.set_xlim(0, 1500)
        # else:
        if cur_num_proc == '256':
            ax.set_xlim(0, 3000)
            ax.set_xticks([0, 500, 1000, 1500, 2000, 2500])
            ax.set_xticklabels(
                ['0', '500', '1,000', '1,500', '2,000', '2,500'])
            plt.annotate('',
                         xy=(1100, 0.99),
                         xytext=(1300, 0.73),
                         arrowprops=dict(arrowstyle='->', lw=5))
            plt.annotate('',
                         xy=(1810, 0.99),
                         xytext=(1600, 0.82),
                         arrowprops=dict(arrowstyle='->', lw=5))
            plt.text(1300, 0.65, 'None: 1089.5 $\mu$s', size=datalabel_size)
            plt.text(1500, 0.75, 'BFQ: 1810.4 $\mu$s', size=datalabel_size)
            plt.text(1300, 0.55, 'Kyber: 1073.2 $\mu$s', size=datalabel_size)
            plt.text(1300, 0.45, 'MQ-DL: 1155.1 $\mu$s', size=datalabel_size)
        else:
            continue

        plt.xlabel(xlabel, fontsize=axis_label_font_size)
        # if cur_num_proc == '1':
        if True:
            plt.ylabel(ylabel, fontsize=axis_label_font_size)
        else:
            ax.set_yticklabels([])
        plt.grid(True)
        ax.tick_params(axis='both',
                       which='major',
                       labelsize=axis_tick_font_size)

        # Plot graph for one scheduler
        for cur_sched in schedulers:
            latencies_sorted = np.sort(latency_log[cur_sched][index])
            p = 1. * np.arange(
                len(latencies_sorted)) / (len(latencies_sorted) - 1)
            cur_legend_label = legend_label[cur_sched]
            ax.plot(
                latencies_sorted,
                p,
                label=cur_legend_label,
                linewidth=linewidth,
                #marker=dot_style[index % len(dot_style)],
                #markersize=markersize,
            )
        # if cur_num_proc == '1':
        plt.legend(
            fontsize=legend_font_size,
            labelspacing=0.,
            ncol=2,
            handletextpad=0.5,
            #    loc='upper left',
            #    bbox_to_anchor=(0.65, 0.92),
            columnspacing=0.2,
            borderpad=0.)

        plt.savefig(fig_save_path, bbox_inches='tight')

############################################
# CPU usage
############################################
if True:
    group_list = schedulers
    y_values = cpu_usage_results
    std_dev = None
    x_ticks = num_processes
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL'
    }

    title = None
    xlabel = 'Number of processes'
    ylabel = 'CPU usage'
    fig_save_path = 'fig-5b-' + fig_name_prefix + '_cpu.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    plt.xlabel(xlabel, fontsize=axis_label_font_size)
    plt.ylabel(ylabel, fontsize=axis_label_font_size)
    plt.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks(range(1, len(x_ticks) + 1), x_ticks)
    ax.yaxis.set_ticks([0, 2, 4, 6, 8, 10])
    ax.set_xlim([0, len(x_ticks) + 0.5])
    ax.set_ylim([0, 10.5])

    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        y = y_values[group_name][0:len(num_processes)]
        x = range(1, len(y) + 1)
        yerr = None

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

    # plt.legend(fontsize=legend_font_size,
    #            labelspacing=0.1,
    #            ncol=1,
    #            columnspacing=0.2,
    #            borderpad=0.2)

    plt.savefig(fig_save_path, bbox_inches='tight')
