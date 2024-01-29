import argparse
import os.path
import subprocess

import fio

# Machine-dependent settings
devices = []
# devices = [
#    '/dev/nvme0n1', '/dev/nvme1n1', '/dev/nvme2n1', '/dev/nvme3n1',
#    '/dev/nvme4n1', '/dev/nvme5n1', '/dev/nvme6n1', '/dev/nvme7n1'
# ]

num_processes = 10

schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']

# Machine-dependent settings done

# settings
results_root = 'results_tapp_inc_dev_10_proc'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
fig_name_prefix = 'tapp_inc_dev_10_proc'

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
spdk_devices = config['spdk_dev']
SPDK_DIR = config['spdk_dir']
SPDK_FIO_PLUGIN = os.path.join(SPDK_DIR, 'build/fio/spdk_nvme')

if config['debug']:
    FIO_RAMP_TIME = 3
    FIO_RUN_TIME = 5

## construct fio options
ENGINE_OPTIONS = '--ioengine=io_uring --registerfiles=1 --fixedbufs=1'
FIO_OPTIONS = '--size=100% --bs=4kb --norandommap=1 --group_reporting=1 --direct=1 --rw=randread --allow_file_create=0 --iodepth=128 --output-format=json'.format(
    FIO_RAMP_TIME, FIO_RUN_TIME)
FIO_TIME_OPTIONS = '--time_based=1 --ramp_time={}s --runtime={}s'.format(
    FIO_RAMP_TIME, FIO_RUN_TIME)
FIO_JOBS = '--name=1 --numjobs={}'.format(num_processes)
FIO_COMMAND_GENERAL = ' '.join(
    [FIO_TIME_OPTIONS, ENGINE_OPTIONS, FIO_OPTIONS, FIO_JOBS])


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
    cur_device = ''
    for (cur_num_devices, cur_new_device) in zip(range(1,
                                                       len(devices) + 1),
                                                 devices):
        if cur_device == '':
            cur_device = cur_new_device
        else:
            cur_device += (':' + cur_new_device)

        for cur_sched in schedulers:
            output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
                num_processes, cur_num_devices, cur_sched)
            output_file = os.path.join(fio_results_dir, output_file)
            scheduler_option = '--ioscheduler=' + cur_sched
            device_option = '--filename=' + cur_device
            fio_option_cur = ' '.join([scheduler_option, device_option])

            cur_fio_command = ' '.join([
                FIO_CMD, fio_option_cur, FIO_COMMAND_GENERAL, '-o', output_file
            ])

            # execute command
            print(cur_fio_command)
            exec_cmd(cur_fio_command)

# # Read and parse results, throughput

global_rk = []
jobs_rk = [
    'read:lat_ns:mean',
    'read:iops',
    'read:lat_ns:stddev',
    'read:iops_stddev',
    'usr_cpu',
    'sys_cpu',
    'read:bw',
    #'read:clat_ns:percentile:99.900000'
]

iops_results = {}
iops_stddev = {}
cpu_results = {}
bw_results = {}
for cur_sched in schedulers:
    iops_results[cur_sched] = []
    iops_stddev[cur_sched] = []
    cpu_results[cur_sched] = []
    bw_results[cur_sched] = []
    for cur_num_devices in range(1, len(devices) + 1):
        output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
            num_processes, cur_num_devices, cur_sched)
        output_file = os.path.join(fio_results_dir, output_file)

        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        iops_results[cur_sched].append(j_res['read:iops'] / 1000)
        iops_stddev[cur_sched].append(j_res['read:iops_stddev'] / 1000)
        cpu_results[cur_sched].append(
            (j_res['usr_cpu'] + j_res['sys_cpu']) * num_processes / 100)
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

#####################################
# Throughput
#####################################
if True:
    # Data, set unused value to none
    group_list = schedulers
    y_values = iops_results
    std_dev = iops_stddev
    x_ticks = range(1, 21)
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL'
    }

    title = None
    xlabel = 'Number of SSDs'
    ylabel = 'Throughput (MIOPS)'
    fig_save_path = 'fig-9a-' + fig_name_prefix + '_iops.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel, fontsize=axis_label_font_size)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks(list(range(0, len(devices) + 1)))
    ax.set_xlim(0, 8.5)
    ax.set_ylim(0, 3.6)

    # Throughput
    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        x = range(1, len(y_values[group_name]) + 1)
        y = y_values[group_name]
        y = [i / 1000 for i in y]
        yerr = None
        if std_dev:
            yerr = std_dev[group_name]
            yerr = [i / 1000 for i in yerr]

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            label=legend_label[group_name],
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )

    # None + Kyber
    plt.annotate('',
                 xy=(1, 0.776),
                 xytext=(0.5, 1.5),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(0, 1.6, '776 KIOPS', size=datalabel_size)
    # BFQ
    plt.annotate('',
                 xy=(1, 0.286),
                 xytext=(2, 0.2),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(2, 0.1, '286 KIOPS', size=datalabel_size)

    # MQ-DL
    plt.annotate('',
                 xy=(1, 0.489),
                 xytext=(2.5, 1.3),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(2.3, 1.3, '489 KIOPS', size=datalabel_size)

    # None
    plt.annotate('',
                 xy=(5, 3.42),
                 xytext=(6, 3),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(6, 2.95, '3.42 MIOPS', size=datalabel_size)
    # BFQ
    plt.annotate('',
                 xy=(8, 1.25),
                 xytext=(7, 0.5),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(6, 0.3, '1.25 MIOPS', size=datalabel_size)
    # Kyber
    plt.annotate('',
                 xy=(4, 2.63),
                 xytext=(5, 2.4),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(5, 2.3, '2.63 MIOPS', size=datalabel_size)
    # MQ-DL
    plt.annotate('',
                 xy=(8, 1.90),
                 xytext=(6, 2),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(3.7, 1.9, '1.90 MIOPS', size=datalabel_size)

    ax.legend(
        fontsize=legend_font_size,
        ncol=1,
        loc='upper left',
        bbox_to_anchor=(-0.02, 1.05),
        columnspacing=0.2,
        labelspacing=0.1,
        borderpad=0.1,
    )

    plt.savefig(fig_save_path, bbox_inches='tight')

#####################################
# CPU
#####################################
if True:
    # Data, set unused value to none
    group_list = schedulers
    y_values = cpu_results
    std_dev = None
    x_ticks = range(1, 21)
    legend_label = {
        'none': 'None',
        'kyber': 'Kyber',
        'bfq': 'BFQ',
        'mq-deadline': 'MQ-DL'
    }

    title = None
    xlabel = 'Number of SSDs'
    ylabel = 'CPU usage'
    fig_save_path = 'fig-9b-' + fig_name_prefix + '_cpu.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel, fontsize=axis_label_font_size)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks(list(range(1, len(devices) + 1)))
    ax.yaxis.set_ticks([0, 2, 4, 6, 8, 10])
    ax.set_xlim(0, 8.5)
    ax.set_ylim(0, 11)

    # Throughput
    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        x = range(1, len(y_values[group_name]) + 1)
        y = y_values[group_name]
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

    plt.savefig(fig_save_path, bbox_inches='tight')