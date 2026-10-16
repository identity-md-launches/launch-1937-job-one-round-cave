# This file is input data. An analyzer must never execute it.
raise RuntimeError('inspected source was executed')
import pkg.nested.worker
from pkg import nested
from pkg.nested import worker
