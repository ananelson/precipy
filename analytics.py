import numpy as np
import matplotlib.pyplot as plt
from identifiers import hash_for_item


def render_plot_to_file(plt, canonical_filename):
    h = hash_for_item(canonical_filename)
    print(h)
    return(h)

#def savegraph(fig, filepath, grid, plot_name, filetype = 'png'):
#    filepath = Path(filepath) / filename(grid, plot_name, filetype)
#    with open(filepath, 'w+b') as f:
#        fig.savefig(f, dpi=300, bbox_inches='tight')

def wavy_line_plot(a, b):
    x1 = np.linspace(0.0, a)
    x2 = np.linspace(0.0, b)

    y1 = np.cos(2 * np.pi * x1) * np.exp(-x1)
    y2 = np.cos(2 * np.pi * x2)
    
    plt.subplot(2, 1, 1)
    plt.plot(x1, y1, 'o-')
    plt.title('A tale of 2 subplots')
    plt.ylabel('Damped oscillation')
    
    plt.subplot(2, 1, 2)
    plt.plot(x2, y2, '.-')
    plt.xlabel('time (s)')
    plt.ylabel('Undamped')

    render_plot_to_file(plt, "two_subplots.png")

    return (list(x1), list(y1))
