import argparse
import os.path
import subprocess

import fio

# Machine-dependent settings
all_bs = ['512', '1k', '2k', '4k', '8k', '16k', '32k', '64k']
all_bs = ['4k', '8k', '16k', '32k', '64k']
all_qd = ['1', '2', '4', '8', '16', '32', '64', '128', '256']
cpus_allowed = 0

# Machine-dependent settings done

# settings
results_dir = 'results_qd_iops_vary_bs/fio_output'
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
args = parser.parse_args()
config = vars(args)
print(config)

# Update constants
FIO_CMD = config['fio']
devices = config['dev']

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
                        #  stdout=subprocess.STDOUT,
                         stderr=subprocess.STDOUT,
                         shell=True,
                         check=True)
    print(res.stdout)
    print(res.stderr)


if config['run']:
    os.makedirs(results_dir)
    for cur_bs in all_bs:
        for cur_qd in all_qd:
            output_file = 'bs_{}_qd_{}.txt'.format(cur_bs, cur_qd)
            output_file = os.path.join(results_dir, output_file)
            bs_option = '--bs=' + cur_bs
            qd_option = '--iodepth=' + cur_qd
            cpu_option = '--cpus_allowed=' + str(cpus_allowed)
            jobs = '--numjobs=1'
            fio_option_cur = ' '.join([bs_option, qd_option, jobs])
            cur_fio_command = ' '.join([
                FIO_CMD, fio_option_cur, cpu_option, FIO_COMMAND_GENERAL, '-o',
                output_file
            ])

            # execute command
            print(cur_fio_command)
            exec_cmd(cur_fio_command)

# Read and parse results, throughput
global_rk = []
jobs_rk = [
    'read:lat_ns:mean', 'read:iops', 'read:lat_ns:stddev', 'read:iops_stddev',
    'usr_cpu', 'sys_cpu', 'read:bw'
]

iops_results = {}
iops_stddev = {}
avg_lat_results = {}
cpu_results = {}
bw_results = {}
for cur_bs in all_bs:
    iops_results[cur_bs] = []
    iops_stddev[cur_bs] = []
    avg_lat_results[cur_bs] = []
    cpu_results[cur_bs] = []
    bw_results[cur_bs] = []
    for cur_qd in all_qd:
        output_file = 'bs_{}_qd_{}.txt'.format(cur_bs, cur_qd)
        output_file = os.path.join(results_dir, output_file)
        _, j_res = fio.parse_experiment(output_file, global_rk, jobs_rk)
        j_res = j_res[0]
        iops_results[cur_bs].append(j_res['read:iops'] / 1000)
        iops_stddev[cur_bs].append(j_res['read:iops_stddev'] / 1000)
        avg_lat_results[cur_bs].append(j_res['read:lat_ns:mean'] / 1000)
        cpu_results[cur_bs].append((j_res['usr_cpu'] + j_res['sys_cpu']) / 100)
        bw_results[cur_bs].append(j_res['read:bw'] / 1024 / 1024)

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
    group_list = all_bs
    y_values_ax1 = avg_lat_results
    y_values_ax2 = cpu_results
    std_dev_ax1 = None
    std_dev_ax2 = None
    x_ticks = iops_results
    legend_label = {
        '512': '512B',
        '1k': '1KiB',
        '2k': '2KiB',
        '4k': '4KiB',
        '8k': '8KiB',
        '16k': '16KiB',
        '32k': '32KiB',
        '64k': '64KiB'
    }

    title = None
    xlabel = 'Throughput (KIOPS)'
    ylabel_ax1 = 'Latency ($\mu$s)'
    fig_save_path = 'fig-1a-qd-iops-vary-bs-throughput.pdf'

    reset_color()
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_xlabel(xlabel, fontsize=axis_label_font_size)
    ax.set_ylabel(ylabel_ax1, fontsize=axis_label_font_size)
    ax.grid(True)

    ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
    ax.xaxis.set_ticks([0, 100, 200, 300])
    ax.set_ylim([0, 1000])

    # Throughput
    for (index, group_name) in zip(range(len(group_list)), group_list):
        # x, y, std_dev, data_label = data[group_name]
        if x_ticks:
            x = x_ticks[group_name]
        y = y_values_ax1[group_name]
        y = [i for i in y if i < 900]
        x = x[:len(y)]
        yerr = None
        if std_dev_ax1:
            yerr = std_dev_ax1[group_name]
        label = legend_label[group_name]
        # if group_name in ['8k', '16k', '32k', '64k']:
        #     label = None

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            label=label,
            marker=dot_style[index % len(dot_style)],
            linewidth=linewidth,
            markersize=markersize,
        )

        if not group_name in [
                '512',
                '1k',
                '2k',
        ]:
            # Add data label
            for i in range(len(x)):
                if i > 3:
                    ax.text(x[i], y[i], all_qd[i], size=datalabel_size)

        if group_name in ['512', '8k']:
            for i in range(len(x)):
                if i <= 3:
                    ax.text(x[i], y[i], all_qd[i], size=datalabel_size)

    ax.legend(
        fontsize=legend_font_size,
        ncol=3,
        loc='upper left',
        handlelength=1.5,
        handletextpad=0.2,
        bbox_to_anchor=(0, 1.02),
        columnspacing=0.2,
        labelspacing=0.1,
        borderpad=0,
    )

    # draw arrows
    plt.arrow(200, 500, 150, -280, width=10, head_width=20, color='black')
    plt.text(180, 520, '370 KIOPS', size=datalabel_size)
    plt.savefig(fig_save_path, bbox_inches='tight')