# Performance Characterization of the Linux Storage I/O Schedulers in the NVMe Era

## Introduction

This repro contains all the scripts used in ICPE'23 BFQ, Multiqueue-Deadline, or Kyber? Performance Characterization of Linux Storage Schedulers in the NVMe Era. 

## Installation

### Update Linux to the latest version

Clone the source code

```bash
git clone git@github.com:ZebinRen/icpe24_io_scheduler_study_public.git scheduler_study_artifact
```

Download Linux 6.3.8

```bash
# Install dependencies for building the Linux kernel
sudo apt-get update
sudo apt-get install git fakeroot build-essential libncurses-dev bison flex libssl-dev libelf-dev debhelper zstd bison libssl-dev bc pahole

mkdir linux_build; cd linux_build
wget https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.3.8.tar.xz
tar -xf linux-6.3.8.tar.xz
# copy the updated fops.c
cp ../scheduler_study_artifact/linux/fops.c linux-6.3.8/block
cd linux-6.3.8
make olddefconfig

# disable keys
scripts/config --disable SYSTEM_TRUSTED_KEYS
scripts/config --disable SYSTEM_REVOCATION_KEYS

# make the linux kernel
make -j $(getconf _NPROCESSORS_ONLN) bindeb-pkg LOCALVERSION=-sched-expr

# After the make finished
cd ..
sudo dpkg -i *deb

# update grub and reboot
sudo update-grub2
sudo sync
sudo reboot now

# After reboot, check the kernel version, the kernel version should be 6.3.8-sched-expr
uname -r
```
Enable all the I/O schedulers:

```bash
sudo modprobe kyber-iosched
sudo modprobe bfq
```
Force synchronous dispatching:

```bash
echo 2 | sudo tee /sys/module/fops/parameters/force_sync_submission
```

Note: During the experiments, we find that the I/O requests with None are processed by the same process where the I/O request is issues. The I/O requests with BFQ, Kyber and MQ-Deadline are processed by a kernel worker, this cause a nearly 50% performance drop. Since this work focuses on the I/O schedulers instead of the Linux storage stack, thus we force all the requests to be processed in the same way.

### Install fio

Download and install fio

```bash
cd ~
mkdir local; cd local
git clone https://github.com/axboe/fio
cd fio
git checkout fio-3.35
./configure
make -j $(getconf _NPROCESSORS_ONLN)
```

The fio binary is located at fio/fio

### Install SPDK

```bash
sudo apt-get install -y pkg-config meson python3-pyelftools uuid-dev libpcap-dev libssl-dev libncurses5 libncurses5-dev
cd ~/local
git clone https://github.com/spdk/spdk.git
cd spdk
git checkout aed4ece93c659195d4b56399a181f41e00a7a25e
git submodule update --init
sudo scripts/pkgdep.sh
./configure --with-fio=/path_to_fio_repo
# If you follow the path used in this manual
# ./configure --with-fio=~/local/fio
make 
```

SPDK needs the PCIe address to access the storage devices, to get the PCIe address:
```bash
ls -l /sys/block/nvme0n1/device/device
# output: lrwxrwxrwx 1 root root 0 Jan 27 02:00 /sys/block/nvme0n1/device/device -> ../../../0000:00:04.0
```
Then the PCIe address of this storage device is 0000:00:04.0. This address will be used in the following experiments.

### Install BPF trace

```bash
sudo apt-get install asciidoctor binutils-dev bison build-essential clang cmake flex libbpf-dev libbpfcc-dev libcereal-dev libdw-dev libelf-dev libiberty-dev libpcap-dev llvm-dev libclang-dev systemtap-sdt-dev zlib1g-dev
cd ~/local
git clone https://github.com/iovisor/bpftrace.git
cd bpftrace
git checkout v0.19.0
git submodule init
git submodule update
mkdir build
./build-libs.sh
cmake -B ./build -DBUILD_TESTING=OFF
make -C ./build -j$(nproc)
```

The binary file is located in ~/local/bpftrace/build/src/bpftrace

### Install perf

```bash
# Install dependencies for building perf
sudo apt install libdw-dev libunwind-dev libiberty-dev libzstd-dev libperl-dev libbfd-dev libcap-dev libnuma-dev libaudit-dev systemtap-sdt-dev libgtk2.0-dev
cd ~/linux_build/linux-6.3.8/tools/perf
make -j$(getconf _NPROCESSORS_ONLN)
```

After make, the perf binary is located at ~/linux_build/linux-6.3.8/tools/perf/perf

### Python
```bash
sudo apt-get install pip
sudo pip install matplotlib
```

## Artifact Evaluation

Since the experiment results varies with different hardware, we also provide all the original data such as fio output and fio traces used in this paper. If you want to plot with our datasets, please see [Artifact Evaluation with Existing Outputs](#Artifact-Evaluation-with-Existing-Outputs).

All the experiments in our paper are carried out in a single socket server with a 10-core CPU and 8 Samsung 980 pro 1TB. The result may vary with different hardware~(such as CPU) or different storage devices. Here is a list to check if you use a different environment:

* We disable Hyper-threading and Trubo in all the experiments.
* Please make sure that all the fio processes/threads are run on the CPU cores that in the same socket. We have noticed that the some I/O schedulers induces significantly high lock contention with cross NUMA settings.
* We do CPU pinning in figure 1, 2, 3, table 2, 3, 4. Please make sure CPU 1 and 2 are available. If CPU 1 or 2 is not available to the experiments, the pinned CPU core should be changed in the scritps.
* Since different hardware leads to different performance, you might need to change the xlimt and ylimit used in the plots~(or delete them).


NOTE: Please check if the device used (the --dev option) does not contain any useful data. The experiments will corrupt the data in the used storage devices.

### Setup

Before running the experiments, force all the I/O requests to be dispatched synchronously every time the machine is restarted.

```bash
echo 2 | sudo tee /sys/module/fops/parameters/force_sync_submission
```

### Precondition

Before the experiments, we need to precondition the device.
<span style="color:red"> WARNING: This will erase all the data on the device.</span>

```bash
cd precondition
sudo ./fill_nvme.sh YOUR_DEVICE
sudo ./fill_random.sh YOUR_DEVICE
```

### Figure 1: SSD Performance

Note: In figure 1, we measure the random read throughput and latency with vary request size start from 512B. If you see the following error message, it means that your device does not support 512b block size, please remove it from line 8 in qd_iops_vary_bs.py

```bash
# fio error message
fio: io_u error on file /dev/nvme1n1: Invalid argument: read offset=537125032448, buflen=512
fio: first direct IO errored. File system may not support direct IO, or iomem_align= is bad, or invalid block size. Try setting direct=0.
```

TODO: Add spdk for B and Ca
```bash
cd fig-1-samsung-baseline
# figure 1a, use a single storage device.
sudo python3 qd_iops_vary_bs.py
sudo python3 qd_iops_vary_bs.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 qd_iops_vary_bs.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1

# figure 1b, use a single storage device.
sudo python3 qd_iops_inc_proc_4kb.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE --spdk_dir YOUR_SPDK_DIR --spdk_dev YOUR_SPDK_DEVICE
# Example: sudo python3 qd_iops_inc_proc_4kb.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1 --spdk_dir /home/user/local/spdk --spdk_dev 'trtype=PCIe traddr=0000.00.09.0 ns=1'

# figure 1c, use all 8 storage devices.
sudo python3 qd_iops_inc_proc_4kb_8_dev.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE --spdk_dir YOUR_SPDK_DIR --spdk_dev YOUR_SPDK_DEVICE
# Example: sudo python3 qd_iops_inc_proc_4kb_8_dev.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1 --spdk_dir /home/user/local/spdk --spdk_dev 'trtype=PCIe traddr=0000.00.09.0 ns=1:traddr=0000.00.0a.0:traddr=0000.00.0b.0:traddr=0000.00.08.0:traddr=0000.00.05.0:traddr=0000.00.04.0:traddr=0000.00.06.0:traddr=0000.00.07.0 ns=1'
```

### Figure 2: 4a and 6a Intra-process scalability

```bash
# figure 2, 4a and 6a, use a single storage device
cd ../fig-2-4a-6a-intra-proc-scal
sudo python3 lapp_cdf_inc_qd_1_dev_1_core.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 lapp_cdf_inc_qd_1_dev_1_core.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1
```

### Figure 3: 4b and 6b Inter-process scalability

```bash
# figure 3, 4b and 6b, use a signle storage device
cd ../fig-3-4b-6b-inter-proc-scal
sudo python3 lapp_cdf_inc_proc_1_dev_1_core.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 lapp_cdf_inc_proc_1_dev_1_core.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1
```


### Figure 5 and 6c: Inter-process scalability with 10 CPU cores

```bash
# figure 5 and 6c, use a single storage device
cd ../fig-5-6c-inter-proc-scal-all-core
sudo python3 lapp_cdf_inc_proc_1_dev_10_core.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 lapp_cdf_inc_proc_1_dev_10_core.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1
```

### Figure 7: T-app inter-process scalability

```bash
# figure 7, use a single storage device
cd ../fig-7-tapp-scal-1-ssd/
sudo python3 tapp_inc_proc_1_dev_10_core.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 tapp_inc_proc_1_dev_10_core.py -r --fio /home/user/local/fio/fio --dev /dev/nvme1n1 --spdk_dir /home/user/local/spdk --spdk_dev 'trtype=PCIe traddr=0000.00.09.0 ns=1'
```

### Figure 8: Lock overhead

```bash
cd ../fig-8-lock-overhead/
# figure 8-a, use a single device
sudo python3 breakdown_1_dev_global.py -r --fio YOUR_FIO_PATH  --perf YOUR_PERF_PATH --vmlinux YOUR_VMLINUX_PATH --dev YOUR_DEVICE
# Exmaple: sudo python3 breakdown_1_dev_global.py -r --fio /home/user/local/fio/fio  --perf /home/user/linux_build/linux-6.3.8/tools/perf/perf --vmlinux /home/user/linux_build/linux-6.3.8/vmlinux --dev /dev/nvme1n1
python3 plot_lock_contention.py

# figure8-b, use all the storage devices
sudo python3 breakdown_8_dev_global.py -r --fio YOUR_FIO_PATH  --perf YOUR_PERF_PATH --vmlinux YOUR_VMLINUX_PATH --dev YOUR_DEVICE
# Example: sudo python3 breakdown_8_dev_global.py -r --fio /home/user/local/fio/fio  --perf /home/user/linux_build/linux-6.3.8/tools/perf/perf --vmlinux /home/user/linux_build/linux-6.3.8/vmlinux --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1
python3 plot_lock_contention_8_dev.py
```

### Figure 9: T-app inter-process scalability with an increasing number of SSDs

The devices are setted in the source code fig-9-ssd-scala/tapp_inc_dev_10_proc.py at line 8. Please provide the devices used in the experment as the example given at line 9 - line 12.

```bash
cd fig-9-ssd-scala
sudo python3 tapp_inc_dev_10_proc.py -r --fio YOUR_FIO_PATH
# Example： sudo python3 tapp_inc_dev_10_proc.py -r --fio /home/user/local/fio/fio
```

### Figure 10: T-app inter-process scalability with 10 SSDs

```bash
# Figure 10: use all 8 devices
cd ../fig-10-tapp-scal-8-ssd/
sudo python3 tapp_inc_proc_8_dev_10_core.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE --spdk_dir YOUR_SPDK_DIR --spdk_dev YOUR_SPDK_DEVICE
# Example: sudo python3 tapp_inc_proc_8_dev_10_core.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1 --spdk_dir /home/user/local/spdk --spdk_dev 'trtype=PCIe traddr=0000.00.09.0 ns=1:traddr=0000.00.0a.0:traddr=0000.00.0b.0:traddr=0000.00.08.0:traddr=0000.00.05.0:traddr=0000.00.04.0:traddr=0000.00.06.0:traddr=0000.00.07.0 ns=1' 
```

### Fig 11: Interference - L-app with background T-app

There are four directories for figure-11, please follow the same step.

```bash
cd ../fig-11-a-lapp-t4kb-mix/
sudo python3 1_lapp_inc_rtapp_8_dev_10_cpu.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 1_lapp_inc_rtapp_8_dev_10_cpu.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1

cd ../fig-11-b-lapp-t64kb-mix/
sudo python3 1_lapp_inc_rtapp_64k_8_dev_10_cpu.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 1_lapp_inc_rtapp_64k_8_dev_10_cpu.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1

cd ../fig-11-c-lapp-t4kbw-mix/
sudo python3 1_lapp_inc_wtapp_8_dev_10_cpu.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 1_lapp_inc_wtapp_8_dev_10_cpu.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1

cd ../fig-11-d-lapp-t64kbw-mix/
sudo python3 1_lapp_inc_wtapp_64k_8_dev_10_cpu.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 1_lapp_inc_wtapp_64k_8_dev_10_cpu.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1

```

### Fig 12: Interference - T-app with background T-app

There are two directories for figure-12, please follow the same step.

```bash
cd ../fig-12-a-t4kb-t64kb-mix/
sudo python3 1_tapp_4k__inc_rtapp_64k_8_dev_10_cpu.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 1_tapp_4k__inc_rtapp_64k_8_dev_10_cpu.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1 

cd ../fig-12-b-t4kb-t64kbw-mix/
sudo python3 1_tapp_4k__inc_wtapp_64k_8_dev_10_cpu.py -r --fio YOUR_FIO_PATH --dev YOUR_DEVICE
# Example: sudo python3 1_tapp_4k__inc_wtapp_64k_8_dev_10_cpu.py -r --fio /home/user/local/fio/fio --dev /dev/nvme0n1:/dev/nvme1n1:/dev/nvme2n1:/dev/nvme3n1:/dev/nvme4n1:/dev/nvme5n1:/dev/nvme6n1:/dev/nvme7n1 
```

### Table 2: Kyber parameter concurrent T-app with random read and write

```bash
cd ../table-2
sudo python3 kyber_vary_target_lat.py -r --fio YOUR_FIO_PATH --bpftrace YOUR_BPFTRACE_PATH --dev YOUR_DEVICE --dev_name YOUR_DEVICE_NAME
# Example: sudo python3 kyber_vary_target_lat.py -r --fio /home/user/local/fio/fio --bpftrace /home/user/local/bpftrace/build/src/bpftrace --dev /dev/nvme1n1 --dev_name nvme1n1 

```

### Table 3 and 4: Kyber parameter concurrent L-app with read and T-app with write

```bash
cd ../table-3-4
sudo python3 kyber_l_t_mix_2_core.py -r --fio YOUR_FIO_PATH --bpftrace YOUR_BPFTRACE_PATH --dev YOUR_DEVICE --dev_name YOUR_DEVICE_NAME
# Example: sudo python3 kyber_l_t_mix_2_core.py -r --fio /home/user/local/fio/fio --bpftrace /home/user/local/bpftrace/build/src/bpftrace --dev /dev/nvme1n1 --dev_name nvme1n1 
```

## Artifact Evaluation with Existing Outputs

Change to the results directory:

```bash
cd results
```

### Figure 1: SSD Performance

```bash
cd fig-1-samsung-baseline
# figure 1a
python3 qd_iops_vary_bs.py
# figure 1b
python3 qd_iops_inc_proc_4kb.py
# figure 1c
python3 qd_iops_inc_proc_4kb_8_dev.py
```

### Figure 2: 4a and 6a Intra-process scalability

```bash
# figure 2, 4a and 6a
cd ../fig-2-4a-6a-intra-proc-scal
python3 lapp_cdf_inc_qd_1_dev_1_core.py
```

### Figure 3: 4b and 6b Inter-process scalability

```bash
# figure 3, 4b and 6b
cd ../fig-3-4b-6b-inter-proc-scal
python3 lapp_cdf_inc_proc_1_dev_1_core.py
```

### Figure 5 and 6c: Inter-process scalability with 10 CPU cores

```bash
# figure 5 and 6c
cd ../fig-5-6c-inter-proc-scal-all-core
python3 lapp_cdf_inc_proc_1_dev_10_core.py
```

### Figure 7: T-app inter-process scalability

```bash
# figure 7
cd ../fig-7-tapp-scal-1-ssd/
python3 tapp_inc_proc_1_dev_10_core.py
```

### Figure 8: Lock overhead

```bash
cd ../fig-8-lock-overhead/
# figure 8-a
python3 plot_lock_contention.py
# figure8-b
python3 plot_lock_contention_8_dev.py
```

### Figure 9: T-app inter-process scalability with an increasing number of SSDs

```bash
cd ../fig-9-ssd-scala
python3 tapp_inc_dev_10_proc.py
```

### Figure 10: T-app inter-process scalability with 10 SSDs

```bash
cd ../fig-10-tapp-scal-8-ssd/
python3 tapp_inc_proc_8_dev_10_core.py 
```

### Fig 11: Interference - L-app with background T-app

There are four directories for figure-11, please follow the same step.

```bash
cd ../fig-11-a-lapp-t4kb-mix/
python3 1_lapp_inc_rtapp_8_dev_10_cpu.py

cd ../fig-11-b-lapp-t64kb-mix/
python3 1_lapp_inc_rtapp_64k_8_dev_10_cpu.py

cd ../fig-11-c-lapp-t4kbw-mix/
python3 1_lapp_inc_wtapp_8_dev_10_cpu.py

cd ../fig-11-d-lapp-t64kbw-mix/
python3 1_lapp_inc_wtapp_64k_8_dev_10_cpu.py
```

### Fig 12: Interference - T-app with background T-app

There are two directories for figure-12, please follow the same step.

```bash
cd ../fig-12-a-t4kb-t64kb-mix/
python3 1_tapp_4k__inc_rtapp_64k_8_dev_10_cpu.py

cd ../fig-12-b-t4kb-t64kbw-mix/
python3 1_tapp_4k__inc_wtapp_64k_8_dev_10_cpu.py
```

### Table 2: Kyber parameter concurrent T-app with random read and write

```bash
cd ../table-2
python3 kyber_vary_target_lat.py
```

### Table 3 and 4: Kyber parameter concurrent L-app with read and T-app with write

```bash
cd ../table-3-4
python3 kyber_l_t_mix_2_core.py

# License
This code and artifact is distributed under the MIT license. 
```
MIT License

Copyright (c) 2023 @Large Research

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```