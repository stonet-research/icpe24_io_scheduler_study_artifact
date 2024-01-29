import argparse
import os.path
import subprocess

import fio

# Machine-dependent settings
num_proc = ['1', '2', '4', '8']
all_qd = ['1', '2', '4', '8', '16', '32', '64', '128', '256']
bs = '4kb'

# settings
results_dir = 'results_qd_iops_inc_proc_4kb'
fio_results_dir = os.path.join(results_dir, 'fio_output')

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
FIO_OPTIONS = '--ioscheduler=none --size=100% --norandommap=1 --group_reporting=1 --direct=1 --rw=randread --allow_file_create=0 --output-format=json'.format(
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
                         stderr=subprocess.STDOUT,
                         shell=True,
                         check=True)
    print(res.stdout)
    print(res.stderr)


if config['run']:
    # Linux storage stack
    os.makedirs(fio_results_dir)
    for cur_proc in num_proc:
        for cur_qd in all_qd:
            output_file = 'bs_4_proc_{}_qd_{}.txt'.format(cur_proc, cur_qd)
            output_file = os.path.join(fio_results_dir, output_file)
            bs_option = '--bs=' + bs
            qd_option = '--iodepth=' + cur_qd
            jobs = '--numjobs=' + cur_proc
            fio_option_cur = ' '.join([bs_option, qd_option, jobs])
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
    # use two processes
    for cur_proc in [1, 2]:
        for cur_qd in all_qd:
            output_file = 'bs_4_proc_{}_qd_{}_spdk.txt'.format(
                cur_proc, cur_qd)
            output_file = os.path.join(fio_results_dir, output_file)
            spdk_preload = 'LD_PRELOAD={} '.format(SPDK_FIO_PLUGIN)
            engine_options = '--ioengine=spdk'
            qd_option = '--iodepth=' + cur_qd
            jobs = '--numjobs=' + str(cur_proc)
            filename = "--filename='{}'".format(spdk_devices)
            fio_option_cur = '--time_based=1 --ramp_time={}s --runtime={}s --bs=4kb --norandommap=1 --group_reporting=1 --direct=1 --rw=randread --allow_file_create=0 --output-format=json  --thread=1 --name=1 --size=100%'.format(
                FIO_RAMP_TIME, FIO_RUN_TIME)
            fio_option_cur = ' '.join([fio_option_cur, qd_option, jobs])
            cur_fio_command = ' '.join([
                spdk_preload, FIO_CMD, engine_options, filename,
                fio_option_cur, '-o', output_file
            ])

            # execute command
            print(cur_fio_command)
            exec_cmd(cur_fio_command)
    exec_cmd(spdk_reset)

print('SPDK finished.')

# Read and parse results, throughput
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'usr_cpu', 'sys_cpu', 'read:bw'
    #'read:clat_ns:percentile:99.900000'
]

# Parse Linux storage stack
iops_results = {}
iops_stddev = {}
avg_lat_results = {}
cpu_results = {}
bw_results = {}
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

# Parse SPDK
spdk_iops_results = {}
spdk_iops_stddev = {}
spdk_avg_lat_results = {}
spdk_cpu_results = {}
spdk_bw_results = {}
for cur_proc in [1, 2]:
    spdk_iops_results[cur_proc] = []
    spdk_iops_stddev[cur_proc] = []
    spdk_avg_lat_results[cur_proc] = []
    spdk_cpu_results[cur_proc] = []
    spdk_bw_results[cur_proc] = []
    for cur_qd in all_qd:
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
    legend_label = {'1': '1p', '2': '2p', '4': '4p', '8': '8p'}

    title = None
    xlabel = 'Throughput (KIOPS)'
    ylabel_ax1 = 'Latency ($\mu$s)'
    fig_save_path = 'fig-1b-qd-iops-inc-proc-4kb.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel_ax1, fontsize=axis_label_font_size)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks([0, 200, 400, 600, 800])
    ax.set_xlim([0, 800])
    ax.set_ylim([0, 1000])

    # Throughput
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

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            label=label,
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )
        if group_name == '1':
            # Add data label
            for i in range(len(x)):
                ax.text(x[i], y[i], all_qd[i], size=datalabel_size)
        elif group_name == '2':
            # Add data label
            for i in range(len(x)):
                if i > 4:
                    ax.text(x[i], y[i], all_qd[i], size=datalabel_size)

    # Throughput SPDK
    group_list = [1, 2]
    y_values_ax1 = spdk_avg_lat_results
    std_dev_ax1 = None
    x_ticks = spdk_iops_results
    legend_label = {
        1: '1p SPDK',
        2: '2p SPDK',
    }
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
        fontsize=legend_font_size,
        ncol=3,
        loc='upper left',
        bbox_to_anchor=(0, 1.04),
        columnspacing=0.2,
        handletextpad=0.2,
        handlelength=1.5,
        labelspacing=0.0,
        borderpad=0.0,
    )

    # draw arrows
    plt.arrow(600, 500, 150, -160, width=10, head_width=20, color='black')
    plt.text(500, 520, '774 KIOPS', size=datalabel_size)
    plt.savefig(fig_save_path, bbox_inches='tight')
