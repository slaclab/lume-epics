import yaml
import logging
import sys

logger = logging.getLogger(__name__)


def config_from_yaml(config_file):
    """
    """

    config = yaml.safe_load(config_file)

    if not isinstance(config, (dict,)):
        logger.exception("Invalid config file.")
        sys.exit()

    epics_configuration = {}

    if "input_variables" in config:

        for variable in config["input_variables"]:
            protocol = config["input_variables"][variable].get("protocol")
            serve = config["input_variables"][variable].get("serve", True)
            pvname = config["input_variables"][variable].get("pvname")

            if not protocol:
                raise ValueError(f"No protocol provided for {variable}")

            if not pvname:
                raise ValueError(f"No pvname provided for {variable}")

            epics_configuration[variable] = {
                "pvname": pvname,
                "serve": serve,
                "protocol": protocol,
            }

    # Is this redundant? Do we need?
    if "output_variables" in config:

        for variable in config["output_variables"]:
            protocol = config["output_variables"][variable].get("protocol")
            serve = config["output_variables"][variable].get("serve", True)
            pvname = config["output_variables"][variable].get("pvname")

            if not protocol:
                raise ValueError(f"No protocol provided for {variable}")

            if not pvname:
                raise ValueError(f"No pvname provided for {variable}")

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
