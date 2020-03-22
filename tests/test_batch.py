from precipy.batch import Batch
import os

def test_batch():
    batch = Batch({})
    assert batch.uuid
    assert os.path.exists(batch.cachePath)
    assert os.path.exists(batch.templateWorkPath)
    assert os.path.exists(batch.outputPath)
