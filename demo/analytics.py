import numpy as np
import os
import matplotlib.pyplot as plt
import time

def generate_data(batch, filename, a, b, n, seed=None):
    if not seed:
        seed = int(time.time())
    print("random seed is %s " % seed)
    print(os.getcwd())
    np.random.seed(seed)
    data = np.random.randint(a, b, n)
    assert filename.endswith(".npy"), "use .npy for file extension"
    for _, f in batch.save_binary(filename):
        np.save(f, data)
    return n

def plot_values(batch, input_filename, c, n, output_filename):
    for f in batch.read_binary(input_filename):
        ary = np.load(f)
    plt.plot(ary, 'ro')
    plt.plot([0, n], [c, c])

    batch.save_matplotlib_plt(plt, output_filename)
