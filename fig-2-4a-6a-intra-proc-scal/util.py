import numpy as np
import pickle


def pickle_load(filename):
    f = open(filename, 'rb')
    ret = pickle.load(f)
    f.close()
    print("{} loaded".format(filename))
    return ret


# Sampled
def sample_list(l, sample_size):
    if len(l) <= sample_size:
        return l
    return l[::len(l) // sample_size]
