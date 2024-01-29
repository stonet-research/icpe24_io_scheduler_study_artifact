import os.path
import subprocess


def get_scheduler(device):
    sched_path = os.path.join('/sys/block', device, 'queue/scheduler')
    f = open(sched_path, 'r')
    line = f.readline()
    f.close()

    sched_name = line[line.find('[') + 1:line.find(']')]

    return sched_name


def assert_scheduler(device, sched):
    return get_scheduler(device) == sched


def set_scheduler(device, sched):
    sched_path = os.path.join('/sys/block', device, 'queue/scheduler')
    # set to none to set all parameters to default
    set_to_none = ' '.join(['echo none', '>', sched_path])
    cmd = ' '.join(['echo', sched, '>', sched_path])
    subprocess.run(set_to_none,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True,
                   check=True)
    subprocess.run(cmd,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True,
                   check=True)

    return assert_scheduler(device, sched)


def get_parameter(device, param_name):
    parameter_path = os.path.join('/sys/block', device, 'queue/iosched/',
                                  param_name)
    f = open(parameter_path, 'r')
    line = f.readline()
    f.close()

    line = line.strip()

    return line


def assert_parameter(device, param_name, value):

    return get_parameter(device, param_name) == str(value)


def set_parameter(device, param_name, value):
    parameter_path = os.path.join('/sys/block', device, 'queue/iosched/',
                                  param_name)
    cmd = ' '.join(['echo', str(value), '>', parameter_path])
    subprocess.run(cmd,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True,
                   check=True)

    return assert_parameter(device, param_name, value)


if __name__ == '__main__':
    print(set_scheduler('nvme0n1', 'bfq'))