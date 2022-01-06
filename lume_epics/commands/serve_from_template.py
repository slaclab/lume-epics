import click
from lume_epics.epics_server import Server
from lume_model.utils import model_from_yaml
from lume_epics.utils import config_from_yaml


@click.command()
@click.argument("filename")
@click.argument("epics_config_filename")
@click.option("--serve-ca", type=bool, default=True)
@click.option("--serve-pva", type=bool, default=True)
def serve_from_template(filename, epics_config_filename, serve_ca, serve_pva):

    with open(filename, "r") as f:
        model_class, model_kwargs = model_from_yaml(f, load_model=False)

    with open(epics_config_filename, "r") as f:
        epics_config = config_from_yaml(f)

    server = Server(model_class, epics_config, model_kwargs=model_kwargs)

    server.start(monitor=True)


if __name__ == "__main__":
    serve_from_template()
