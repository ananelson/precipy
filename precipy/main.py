from batch import Batch

def render(request):
    batch = Batch(request)
    batch.generate_analytics()
    output = batch.process_filters()
    return output

from mock import Request
import sys
if __name__ == '__main__':
    render(Request(sys.argv[1]))
