
from lume_epics.epics_server import Server
from lume_model.utils import model_from_yaml

with open("examples/files/iris_config.yaml", "r") as f:
    model_class, model_kwargs = model_from_yaml(f, load_model=False)

prefix = "test"
server = Server(
    model_class,
    prefix,
    model_kwargs=model_kwargs
)

# monitor = False does not loop in main thread
server.start(monitor=True)