import pathlib

from dynaconf import Dynaconf


CONFIG_PATH = pathlib.Path(__file__).parent

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=[CONFIG_PATH / "settings.yaml"],
)
