import sys
sys.stdout.reconfigure(encoding='utf-8')

import lunar_python
print("lunar_python OK:", getattr(lunar_python, '__version__', 'installed'))

from iztro_py import astro
print("iztro-py OK (iztro_py.astro imported)")

import swisseph as swe
print("pyswisseph OK:", getattr(swe, '__version__', 'installed'))
print("SIDM_LAHIRI:", swe.SIDM_LAHIRI)
