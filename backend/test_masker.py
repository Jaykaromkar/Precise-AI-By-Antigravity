import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pii_masker import PIIVault

vault = PIIVault()
test_text = "I have $26.3 billion and 10% of 183,346 people, which is millions of dollars. There are two options costing 39,177) $."
masked = vault.mask(test_text)
print("Original:", test_text)
print("Masked:", masked)
print("Mapping:", vault.mapping)
