from batch import Batch

def render(request):
    batch = Batch(request)
    batch.generate_analytics()
    return batch.render_template()
