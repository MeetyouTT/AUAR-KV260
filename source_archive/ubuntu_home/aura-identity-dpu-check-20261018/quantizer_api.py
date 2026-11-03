import inspect
from pathlib import Path
from pytorch_nndct.apis import torch_quantizer
import pytorch_nndct
print('quantizer_api:', inspect.signature(torch_quantizer), flush=True)
print(inspect.getsource(torch_quantizer.__init__), flush=True)
print('module:', pytorch_nndct.__file__, flush=True)
