from precipy.batch import Batch
from precipy.mock import Request
import sys

import analytics
analytics_modules = [analytics]

def render_fn(request, analytics_mods=analytics_modules):
    batch = Batch(request)
    batch.generate_analytics(analytics_mods)
    output = batch.process_filters()
    return output

render = render_fn

if __name__ == '__main__':
    render(Request(sys.argv[1]))
