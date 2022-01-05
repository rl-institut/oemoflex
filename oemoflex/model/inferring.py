import os
import shutil

from datapackage import Package, Resource

from oemoflex.tools.helpers import load_yaml

# Path definitions
module_path = os.path.dirname(os.path.abspath(__file__))

FOREIGN_KEYS = "foreign_keys.yml"


all_foreign_keys = load_yaml(os.path.join(module_path, FOREIGN_KEYS))

default_foreign_key_descriptors = {
    "bus": [
        {
            "fields": "bus",
            "reference": {"resource": "bus", "fields": "name"},
        },
    ],
    "from_to_bus": [
        {
            "fields": "from_bus",
            "reference": {"resource": "bus", "fields": "name"},
        },
        {
            "fields": "to_bus",
            "reference": {"resource": "bus", "fields": "name"},
        },
    ],
    "chp": [
        {
            "fields": "fuel_bus",
            "reference": {"resource": "bus", "fields": "name"},
        },
        {
            "fields": "electricity_bus",
            "reference": {"resource": "bus", "fields": "name"},
        },
        {
            "fields": "heat_bus",
            "reference": {"resource": "bus", "fields": "name"},
        },
    ],
}


default_foreign_keys = (
    {
        "bus": [
            "volatile",
            "dispatchable",
            "storage",
            "load",
            "reservoir",
            "shortage",
            "excess",
        ],
        "profile": ["load", "volatile", "ror"],
        "from_to_bus": ["connection", "line", "conversion"],
        "chp": ["backpressure", "extraction", "chp"],
    },
)


def infer_metadata(
    package_name="default-name",
    keep_resources=False,
    foreign_keys=None,
    foreign_key_descriptors=None,
    path=None,
):
    """Add basic meta data for a datapackage

    Parameters
    ----------
    package_name: string
        Name of the data package
    keep_resource: boolean
        Flag indicating of the resources meta data json-files should be kept
        after main datapackage.json is created. The reource meta data will
        be stored in the `resources` directory.
    foreign_keys: dict
        Dictionary with foreign key specification. Keys for dictionary are:
        'bus', 'profile', 'from_to_bus'. Values are list with
        strings with the name of the resources
    path: string
        Absoltue path to root-folder of the datapackage
    """
    if foreign_keys is None:
        foreign_keys = default_foreign_keys

    if foreign_key_descriptors is None:
        foreign_key_descriptors = default_foreign_key_descriptors

    current_path = os.getcwd()
    if path:
        print("Setting current work directory to {}".format(path))
        os.chdir(path)

    p = Package()
    p.descriptor["name"] = package_name
    p.descriptor["profile"] = "tabular-data-package"
    p.commit()
    if not os.path.exists("resources"):
        os.makedirs("resources")

    # create meta data resources elements
    if not os.path.exists("data/elements"):
        print("No data path found in directory {}. Skipping...".format(os.getcwd()))
    else:
        for f in os.listdir("data/elements"):
            r = Resource({"path": os.path.join("data/elements", f)})
            r.infer()
            r.descriptor["schema"]["primaryKey"] = "name"

            r.descriptor["schema"]["foreignKeys"] = []

            # Define foreign keys from dictionary 'foreign_key_descriptors'
            for label, descriptor in foreign_key_descriptors.items():
                if r.name in foreign_keys.get(label, []):
                    r.descriptor["schema"]["foreignKeys"].extend(descriptor)

            # Define foreign keys for 'profile' as <resource name>_profile
            if r.name in foreign_keys.get("profile", []):
                r.descriptor["schema"]["foreignKeys"].append(
                    {
                        "fields": "profile",
                        "reference": {"resource": r.name + "_profile"},
                    }
                )

            # Define all undefined foreign keys for as <var name>_profile
            for key in foreign_keys:
                if key not in ["profile"] + list(foreign_key_descriptors):
                    if r.name in foreign_keys[key]:
                        r.descriptor["schema"]["foreignKeys"].append(
                            {
                                "fields": key,
                                "reference": {"resource": key + "_profile"},
                            }
                        )

            # set foreign keys in resource descriptor

            r.commit()
            r.save(os.path.join("resources", f.replace(".csv", ".json")))
            p.add_resource(r.descriptor)

    # create meta data resources sequences
    if not os.path.exists("data/sequences"):
        print("No data path found in directory {}. Skipping...".format(os.getcwd()))
    else:
        for f in os.listdir("data/sequences"):
            r = Resource({"path": os.path.join("data/sequences", f)})
            r.infer()
            r.commit()
            r.save(os.path.join("resources", f.replace(".csv", ".json")))
            p.add_resource(r.descriptor)

    if not os.path.exists("data/geometries"):
        print(
            "No geometries path found in directory {}. Skipping...".format(os.getcwd())
        )
    else:
        for f in os.listdir("data/geometries"):
            r = Resource({"path": os.path.join("data/geometries", f)})
            r.infer()
            r.commit()
            r.save(os.path.join("resources", f.replace(".csv", ".json")))
            p.add_resource(r.descriptor)

    p.commit()
    p.save("datapackage.json")

    if not keep_resources:
        shutil.rmtree("resources")

    os.chdir(current_path)


def infer(select_components, package_name, path, foreign_keys_update=None):

    if foreign_keys_update:
        for key, value in foreign_keys_update.items():
            if key in all_foreign_keys:
                all_foreign_keys[key].extend(foreign_keys_update[key])
            else:
                all_foreign_keys[key] = foreign_keys_update[key]

        print("Updated foreign keys.")

    foreign_keys = {}

    for key, lst in all_foreign_keys.items():

        selected_lst = [item for item in lst if item in select_components]

        if selected_lst:
            foreign_keys[key] = selected_lst

    infer_metadata(
        package_name=package_name,
        foreign_keys=foreign_keys,
        path=path,
    )
