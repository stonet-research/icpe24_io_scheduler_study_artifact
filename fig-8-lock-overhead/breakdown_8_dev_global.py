import argparse
import os
import os.path
import subprocess

import fio
'''
Experiment design:
1. 1 device, 1 proc, 4KB randread
2. 1 device, 2 proc, 4KB randread
3. 1 device, 3 proc, 4KB randread
4. 1 device, 4 proc, 4KB randread
5. 1 device, 5 proc, 4KB randread
6. 1 device, 10 proc, 4KB randread
7. 1 device, 15 proc, 4KB randread
'''

# FG_HOME = 
# FLAMEGRAPH = 
# VMLINUX = 
# PERF = 
# FIO_CMD = 

# Machine-dependent settings
# devices = '/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1:/dev/nvme8n1:/dev/nvme9n1'
num_proc = [1, 2, 3, 4, 5, 10, 15]  # this should be sorted
schedulers = ['none', 'bfq', 'kyber', 'mq-deadline']

# Machine-dependent settings done

# settings
results_dir = 'results_breakdown_8_dev_global'
fio_output = 'fio'
perf_data = 'perf_data'
perf_list = 'perf_list'
perf_graph = 'perf_graph'
flame_graph = 'flame_graph'
FIO_RAMP_TIME = 30
FIO_RUN_TIME = 120

os.mkdir(results_dir)
if not os.path.isdir(os.path.join(results_dir, fio_output)):
    os.mkdir(os.path.join(results_dir, fio_output))

if not os.path.isdir(os.path.join(results_dir, perf_data)):
    os.mkdir(os.path.join(results_dir, perf_data))

if not os.path.isdir(os.path.join(results_dir, perf_list)):
    os.mkdir(os.path.join(results_dir, perf_list))

if not os.path.isdir(os.path.join(results_dir, perf_graph)):
    os.mkdir(os.path.join(results_dir, perf_graph))

if not os.path.isdir(os.path.join(results_dir, flame_graph)):
    os.mkdir(os.path.join(results_dir, flame_graph))

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
parser.add_argument(
    '--perf',
    action='store',
    default='',
    help='Path to the perf binary'
)
parser.add_argument(
    '--vmlinux',
    action='store',
    default='',
    help='Path to the vm_linux file'
)
args = parser.parse_args()
config = vars(args)
print(config)

# Update constants
FIO_CMD = config['fio']
devices = config['dev']
spdk_devices = config['spdk_dev']
SPDK_DIR = config['spdk_dir']
SPDK_FIO_PLUGIN = os.path.join(SPDK_DIR, 'build/fio/spdk_nvme')
VMLINUX = config['vmlinux']
PERF = config['perf']

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

PERF_CMD = '{} record -a -e cycles,instructions -F 99'.format(PERF)
PERF_CMD_GRAPH = PERF_CMD + ' -g'

PERF_REPORT = '{} report --vmlinux {} -n -m --stdio --full-source-path --source -s symbol'.format(
    PERF, VMLINUX)


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
    for cur_num_process in num_proc:
        for cur_sched in schedulers:
            # construct output data for run
            fio_output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
                cur_num_process, 1, cur_sched)
            fio_output_file = os.path.join(results_dir, fio_output,
                                           fio_output_file)

            fio_output_file_g = 'proc_{}_dev_{}_sche_{}_g.txt'.format(
                cur_num_process, 1, cur_sched)
            fio_output_file_g = os.path.join(results_dir, fio_output,
                                             fio_output_file_g)

            perf_out_file = 'proc_{}_dev_{}_sche_{}_perf.data'.format(
                cur_num_process, 1, cur_sched)
            perf_out_file = os.path.join(results_dir, perf_data, perf_out_file)

            perf_out_file_g = 'proc_{}_dev_{}_sche_{}_g_perf.data'.format(
                cur_num_process, 1, cur_sched)
            perf_out_file_g = os.path.join(results_dir, perf_data,
                                           perf_out_file_g)

            scheduler_option = '--ioscheduler=' + cur_sched
            jobs = '--numjobs=' + str(cur_num_process)
            fio_option_cur = ' '.join([scheduler_option, jobs])

            cur_fio_command = ' '.join([
                PERF_CMD, '-o ', perf_out_file, FIO_CMD, fio_option_cur,
                FIO_COMMAND_GENERAL, '-o', fio_output_file
            ])

            cur_fio_command_g = ' '.join([
                PERF_CMD, '-g', '-o', perf_out_file_g, FIO_CMD, fio_option_cur,
                FIO_COMMAND_GENERAL, '-o', fio_output_file_g
            ])

            # execute command
            exec_cmd(cur_fio_command)
            exec_cmd(cur_fio_command_g)

# Parse output data
if config['run'] or config['parse']:
    for cur_num_process in num_proc:
        for cur_sched in schedulers:
            # construct output data for run
            fio_output_file = 'proc_{}_dev_{}_sche_{}.txt'.format(
                cur_num_process, 1, cur_sched)
            fio_output_file = os.path.join(results_dir, fio_output,
                                           fio_output_file)

            fio_output_file_g = 'proc_{}_dev_{}_sche_{}_g.txt'.format(
                cur_num_process, 1, cur_sched)
            fio_output_file_g = os.path.join(results_dir, fio_output,
                                             fio_output_file_g)

            perf_out_file = 'proc_{}_dev_{}_sche_{}_perf.data'.format(
                cur_num_process, 1, cur_sched)
            perf_out_file = os.path.join(results_dir, perf_data, perf_out_file)

            perf_out_file_g = 'proc_{}_dev_{}_sche_{}_g_perf.data'.format(
                cur_num_process, 1, cur_sched)
            perf_out_file_g = os.path.join(results_dir, perf_data,
                                           perf_out_file_g)

            # # parse output
            perf_parsed_list = os.path.join(
                results_dir, perf_list,
                'proc_{}_dev_{}_sche_{}_perf_list.txt'.format(
                    cur_num_process, 1, cur_sched))
            perf_parsed_graph = os.path.join(
                results_dir, perf_graph,
                'proc_{}_dev_{}_sche_{}_perf_graph.txt'.format(
                    cur_num_process, 1, cur_sched))

            perf_parse_list_cmd = ' '.join(
                [PERF_REPORT, '-i', perf_out_file, '>>', perf_parsed_list])
            perf_parse_graph_cmd = ' '.join([
                PERF_REPORT, '-g', '-i', perf_out_file_g, '>>',
                perf_parsed_graph
            ])

            exec_cmd(perf_parse_list_cmd)
            exec_cmd(perf_parse_graph_cmd)

            # flamegraph_cmd = ' '.join([
            #     FLAMEGRAPH, perf_out_file_g,
            #     os.path.join(
            #         results_dir, flame_graph,
            #         'proc_{}_dev_{}_sche_{}.svg'.format(
            #             cur_num_process, 1, cur_sched))
            # ])
            # flamegraph_cmd = ' '.join([
            #     PERF, 'script', '--vmlinux', VMLINUX, '-i', perf_out_file_g,
            #     '|',
            #     os.path.join(FG_HOME, 'stackcollapse-perf.pl'), '|',
            #     os.path.join(FG_HOME, 'flamegraph.pl'), '>',
            #     os.path.join(
            #         results_dir, flame_graph,
            #         'proc_{}_dev_{}_sche_{}.svg'.format(
            #             cur_num_process, 1, cur_sched))
            # ])
            # exec_cmd(flamegraph_cmd)
