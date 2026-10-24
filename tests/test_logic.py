import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from logic import emi_calc, foir

def test_emi_known_value():
    assert abs(emi_calc(100000, 12, 12) - 8884.88) < 0.01

def test_foir():
    assert foir(100000, 10000, 15000) == 25.0
