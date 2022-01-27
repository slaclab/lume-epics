import yaml
import logging
import sys

logger = logging.getLogger(__name__)


def config_from_yaml(config_file):
    """Load yaml file into configuration
    """

    config = yaml.safe_load(config_file)

    if not isinstance(config, (dict,)):
        logger.exception("Invalid config file.")
        sys.exit()

    epics_configuration = {}

    variables = config["input_variables"]
    variables.update(config["output_variables"])

    # keep formatting distinction btw inputs/outputs for clarity
    for variable, var_config in variables.items():
        protocol = var_config.get("protocol")
        serve = var_config.get("serve", True)
        pvname = var_config.get("pvname")

        keys = list(var_config.keys())

        if not protocol:
            raise ValueError(f"No protocol provided for {variable}")

        if not pvname:
            raise ValueError(f"No pvname provided for {variable}")

        keys.remove("protocol")
        keys.remove("pvname")
        try:
            keys.remove("serve")
        except ValueError:
            pass

        if len(keys) > 0 and protocol == "pva":
            epics_configuration[variable]["fields"] = keys

        epics_configuration[variable] = {
            "pvname": pvname,
            "serve": serve,
            "protocol": protocol,
        }

    if "summary" in config:
        pvname = config["summary"].get("pvname")
        owner = config["summary"].get("owner", "")
        date_published = config["summary"].get("date_published", "")
        description = config["summary"].get("description", "")
        id = config["summary"].get("id", "")

        if not pvname:
            raise ValueError("No pvname provided for summary variable.")

        epics_configuration["summary"] = {
            "pvname": pvname,
            "owner": owner,
            "date_published": date_published,
            "description": description,
            "id": id,
        }

    return epics_configuration
