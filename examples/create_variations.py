import os
import pandas as pd
from oemoflex.model.variations import VariationGenerator
from oemoflex.model.datapackage import EnergyDataPackage


here = os.path.abspath(os.path.dirname(__file__))
preprocessed = os.path.join(here, '01_preprocessed', 'simple_model')
variation = os.path.join(here, 'variations.csv')
varied = os.path.join(here, '04_variations')

edp = EnergyDataPackage.from_csv_dir(preprocessed)

vg = VariationGenerator(edp)

var = pd.read_csv(variation, header=[0, 1], index_col=0)

vg.create_variations(var, varied)
