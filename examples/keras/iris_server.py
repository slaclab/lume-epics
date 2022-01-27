from lume_epics.epics_server import Server
from lume_model.utils import model_from_yaml
from lume_epics.utils import config_from_yaml

if __name__ == "__main__":
    with open("examples/files/iris_config.yml", "r") as f:
        model_class, model_kwargs = model_from_yaml(f, load_model=False)

    with open("examples/files/iris_epics_config.yml", "r") as f:
        epics_config = config_from_yaml(f)

    server = Server(model_class, epics_config, model_kwargs=model_kwargs)

    # monitor = False does not loop in main thread
    server.start(monitor=True)
