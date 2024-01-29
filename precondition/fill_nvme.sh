#! /bin/bash

# source: https://github.com/Krien/NVMeBenchmarks/blob/main/scripts/precondition.sh

dev=$1;

# trim
nvme format -s 1 $dev;

# fill sequential
fio \
--name "precondition_fill_nvme" \
--filename=$dev \
--size=100% \
--bs=512K \
--direct=1 \
--rw=write \
--thread=1 \
--ioengine=io_uring \
--fixedbufs=1 --registerfiles=1;
