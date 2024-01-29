import argparse
import os.path
import subprocess

import fio

# Machine-dependent settings
max_process = 15
schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']

# Machine-dependent settings done

# settings
results_root = 'results_tapp_inc_proc_1_dev_10_core'
fig_dir = results_root
fio_results_dir = os.path.join(results_root, 'fio_output')
fig_name_prefix = 'tapp_inc_proc_1_dev_10_core'

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
FIO_OPTIONS = '--size=100% --bs=4kb --norandommap=1 --group_reporting=1 --direct=1 --rw=randread --allow_file_create=0 --iodepth=128 --output-format=json'.format(
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
    for cur_num_process in range(1, max_process + 1):
        for cur_sched in schedulers:
            output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
                cur_num_process, 1, cur_sched)
            output_file = os.path.join(fio_results_dir, output_file)
            scheduler_option = '--ioscheduler=' + cur_sched
            jobs = '--numjobs=' + str(cur_num_process)
            fio_option_cur = ' '.join([scheduler_option, jobs])

            cur_fio_command = ' '.join([
                FIO_CMD, fio_option_cur, FIO_COMMAND_GENERAL, '-o', output_file
            ])

            # execute command
            print(cur_fio_command)
            exec_cmd(cur_fio_command)

    # SPDK
    spdk_setup = os.path.join(SPDK_DIR, 'scripts/setup.sh')
    spdk_reset = spdk_setup + ' reset'
    exec_cmd(spdk_setup)
    for cur_num_process in range(1, max_process + 1):
        output_file = 'proc_{}_dev_{}_sche_spdk.txt'.format(cur_num_process, 1)
        output_file = os.path.join(fio_results_dir, output_file)
        spdk_preload = 'LD_PRELOAD={} '.format(SPDK_FIO_PLUGIN)
        engine_options = '--ioengine=spdk'
        filename = "--filename='{}'".format(spdk_devices)
        fio_option_cur = '--time_based=1 --ramp_time={}s --runtime={}s --bs=4kb --norandommap=1 --group_reporting=1 --direct=1 --rw=randread --allow_file_create=0 --output-format=json  --iodepth=128 --thread=1 --name=1 --numjobs={}'.format(
            FIO_RAMP_TIME, FIO_RUN_TIME, cur_num_process)

        cur_fio_command = ' '.join([
            spdk_preload, FIO_CMD, engine_options, filename, fio_option_cur,
            '-o', output_file
        ])

        # execute command
        print(cur_fio_command)
        exec_cmd(cur_fio_command)
    exec_cmd(spdk_reset)

# Read and parse results, throughput
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

print('throughput')
for k in iops_results:
    print(k)
    print(iops_results[k])

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
# Throughput
####################################
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
    ylabel = 'Throughput (KIOPS)'
    fig_save_path = 'fig-7-a-tapp-inc-proc-1-dev-10-core.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel, fontsize=axis_label_font_size)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks([0, 1, 3, 5, 7, 9, 11, 13, 15])
    ax.set_xlim([0, 15.5])
    ax.set_ylim([0, 820])

    # Throughput
    for (index, group_name) in zip(range(len(group_list)), group_list):
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

    plt.annotate('',
                 xy=(3, 780),
                 xytext=(5, 700),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.annotate('',
                 xy=(2, 780),
                 xytext=(5, 700),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(5, 700, '$\sim$785 KIOPS', size=datalabel_size)
    plt.annotate('',
                 xy=(3, 567),
                 xytext=(7, 550),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(7, 550, '569.2 KIOPS', size=datalabel_size)
    plt.annotate('',
                 xy=(5, 315),
                 xytext=(7, 350),
                 arrowprops=dict(arrowstyle='->', lw=5))
    plt.text(7, 350, '315.3 KIOPS', size=datalabel_size)

    # Add legend
    ax.legend(
        fontsize=legend_font_size,
        ncol=3,
        loc='upper left',
        bbox_to_anchor=(-0.02, 0.3),
        labelspacing=0,
        handlelength=1,
        handletextpad=0.3,
        columnspacing=0.,
        borderpad=0.,
    )

    plt.savefig(fig_save_path, bbox_inches='tight')

####################################
# CPU
####################################
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
        'mq-deadline': 'MQ-DL',
        'spdk': "SPDK"
    }

    title = None
    xlabel = 'Number of processes'
    ylabel = 'CPU usage'
    fig_save_path = 'fig-7-a-tapp-inc-proc-1-dev-10-core-cpu.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel, fontsize=axis_label_font_size)
    # plt.grid(True)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks([0, 1, 3, 5, 7, 9, 11, 13, 15])
    ax.yaxis.set_ticks([0, 2, 4, 6, 8, 10])
    ax.set_xlim([0, 15.5])
    ax.set_ylim([0, 10.5])

    # Throughput
    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        x = range(1, len(y_values[group_name]) + 1)
        y = y_values[group_name]
        yerr = None
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