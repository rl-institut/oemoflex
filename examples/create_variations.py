r"""
Example on how to use the VariationGenerator. To create the base DataFramePackage, run
simple_model.py first.
"""
import os
import pandas as pd
from oemoflex.model.variations import VariationGenerator
from oemoflex.model.datapackage import EnergyDataPackage


here = os.path.abspath(os.path.dirname(__file__))
preprocessed = os.path.join(here, '01_preprocessed', 'simple_model')
variation_specs = os.path.join(here, 'variations.csv')
varied = os.path.join(here, '04_variations')

edp = EnergyDataPackage.from_csv_dir(preprocessed)

vg = VariationGenerator(edp)

what_to_vary = pd.read_csv(variation_specs, header=[0, 1], index_col=0)

vg.create_variations(what_to_vary, varied)
