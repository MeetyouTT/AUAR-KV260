"""Inside offline container: frozen identity/timing regressions on our overlay."""
import bootstrap
import importlib
import sys
import unittest

# The previous runtime tests use standalone imports. Resolve them to exactly
# the same candidate modules the production package imports would use.
for name in ('dpu_vision_runtime', 'dpu_vision_schedule'):
    sys.modules[name] = importlib.import_module('board.vision.'+name)

success = True
for directory in ('/frozen/tests', '/implementation/tests'):
    suite = unittest.TestLoader().discover(directory)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = result.wasSuccessful() and success
raise SystemExit(0 if success else 1)
