import os
import os.path
import subprocess

import fio
'''
Experiment design:
1. 1 device, 1 proc, 4KB randread
2. 1 device, 3 proc, 4KB randread
3. 1 device, 10 proc, 4KB randread
4. 1 device, 11 proc, 4KB randread
5. 1 device, 20 proc, 4KB randread
'''

# Machine-dependent settings
num_proc = [1, 2, 3, 4, 5, 10, 15]  # this should be sorted
schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']

# Machine-dependent settings done

# settings
resutls_dir = 'results_breakdown_8_dev_global'
fio_output = 'fio'
perf_data = 'perf_data'
perf_list = 'perf_list'
perf_graph = 'perf_graph'
flame_graph = 'flame_graph'

lock_symbol = [
    'native_queued_spin_lock_slowpath', '_raw_spin_lock', '_raw_spin_lock_irq',
    '_raw_spin_unlock_irq', '_raw_spin_lock_irqsave', '_raw_spin_unlock',
    'mutex_lock', 'mutex_unlock'
]


def get_lock_percentage(filename):
    f = open(filename, 'r')

    lock_overhead = 0
    contents = []
    curline = f.readline()
    while curline[0] == '#':
        curline = f.readline()
    while curline[0] != '#' and curline[0] != '\n':
        contents.append(curline)
        curline = f.readline()
    f.close()

    for line in contents:
        line = line.split(' ')
        line = [x for x in line if x != '']
        if line[3] in lock_symbol:
            lock_overhead += float(line[0][:-1])

    return lock_overhead


all_lock_overhead = {}
for cur_sched in schedulers:
    all_lock_overhead[cur_sched] = []
    for cur_num_process in num_proc:
        # parse output
        perf_parsed_list = os.path.join(
            resutls_dir, perf_list,
            'proc_{}_dev_{}_sche_{}_perf_list.txt'.format(
                cur_num_process, 1, cur_sched))
        all_lock_overhead[cur_sched].append(
            get_lock_percentage(perf_parsed_list))

# plot

import numpy as np

import matplotlib
import matplotlib.pyplot as plt

# Switch to type 1 fonts
# matplotlib.rcParams['text.usetex'] = True
# plt.rc('font', **{'family': 'serif', 'serif': ['Times']})

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
# Global parameters
bar_width = 0.2
linewidth = 4
markersize = 15

datalabel_size = 36
datalabel_va = 'bottom'
axis_tick_font_size = 46
axis_label_font_size = 52
legend_font_size = 46

# Data, set unused value to none
group_list = schedulers
y_values = all_lock_overhead
std_dev = None
x_ticks = num_proc
legend_label = {
    'none': 'None',
    'kyber': 'Kyber',
    'bfq': 'BFQ',
    'mq-deadline': 'MQ-DL'
}

title = None
xlabel = 'Number of processes'
ylabel = 'Lock overhead (\%)'
fig_save_path = 'lock_overhead_8_dev.pdf'

# plot
fig, ax = plt.subplots(figsize=(12, 8))
plt.grid(axis='y')  # x, y, both

# x, y axis limit
# ax.set_xlim(0, 2)
ax.set_ylim(0, 100)
ax.yaxis.set_tick_params(labelleft=False)

# set ticks
plt.xticks(list(np.arange(len(x_ticks))), x_ticks)

if title:
    plt.title(title)

if xlabel:
    plt.xlabel(xlabel, fontsize=axis_label_font_size)
# if ylabel:
#     plt.ylabel(ylabel, fontsize=axis_label_font_size)

ax.tick_params(axis='both', which='major', labelsize=axis_tick_font_size)
# compute bar offset, with respect to center
bar_offset = []
mid_point = (len(group_list) * bar_width) / 2
for i in range(len(group_list)):
    bar_offset.append(bar_width * i + 0.5 * bar_width - mid_point)

x_axis = np.arange(len(x_ticks))
# draw figure by column
for (index, group_name) in zip(range(len(group_list)), group_list):
    y = y_values[group_name]
    yerr = None
    if std_dev:
        yerr = std_dev[group_name]
    bar_pos = x_axis + bar_offset[index]
    plt.bar(bar_pos,
            y,
            width=bar_width,
            label=legend_label[group_name],
            yerr=yerr)

    # print data label
    for (x, y, index) in zip(bar_pos, y, range(1, len(y) + 1)):
        if index != 7:
            continue

        x_offset = 0
        y_offset = 0
        if group_name == 'mq-deadline':
            x_offset = 0.
            y_offset = -7
        if group_name == 'bfq' and index == 1:
            y_offset = 5
        if group_name == 'kyber':
            x_offset = 0.3
        if group_name == 'none':
            y_offset = -3

        if index == 1 and group_name == 'none':
            x_offset = -0.1
            y_offset = -2
        elif index == 1 and group_name == 'mq-deadline':
            x_offset = 0.3
        elif index == 1 and group_name == 'kyber':
            y_offset = -2
        text = '{:.2f}'.format(y)
        plt.text(
            x + x_offset,
            y + y_offset,
            text,
            size=datalabel_size,
            ha='center',
            va=
            datalabel_va,  # 'bottom', 'baseline', 'center', 'center_baseline', 'top'
        )

# # Legend: Change the ncol and loc to fine-tune the location of legend
# if legend_label != None:
#     #plt.legend(fontsize=legend_font_size)
#     plt.legend(
#         fontsize=legend_font_size,
#         ncol=2,
#         loc='upper left',
#         bbox_to_anchor=(0.08, 1.265),
#     )

plt.savefig(fig_save_path, bbox_inches='tight')