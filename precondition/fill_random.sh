#! /bin/bash

dev=$1;
fio \
    --name "precondition_rand_nvme" \
    --filename=$dev \
    --size=100% \
    --loops=2 \
    --bs=4kb \
    --direct=1 \
    --rw=randwrite \
    --thread=1 \
    --ioengine=io_uring \
    --fixedbufs=1 --registerfiles=1 --hipri;

echo Fill random $dev done;