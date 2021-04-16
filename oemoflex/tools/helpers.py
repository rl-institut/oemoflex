import yaml


def load_yaml(file_path):
    with open(file_path, 'r') as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)

    return yaml_data
