from precipy.batch import Batch

def render_fn(request, analytics_mods=None):
    batch = Batch(request)
    batch.generate_analytics(analytics_mods)
    output = batch.process_filters()
    return output

render = render_fn

from precipy.mock import Request
import sys
if __name__ == '__main__':
    render(Request(sys.argv[1]))
