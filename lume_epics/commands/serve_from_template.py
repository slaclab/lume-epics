import click
from lume_epics.epics_server import Server
from lume_model.utils import model_from_yaml


@click.command()
@click.argument("filename")
@click.argument("protocol")
@click.argument("prefix")
@click.option("--serve-ca", type=bool, default=True)
@click.option("--serve-pva", type=bool, default=True)
def serve_from_template(filename, protocol, prefix, serve_ca, serve_pva):

    with open(filename, "r") as f:
        model_class, model_kwargs = model_from_yaml(f, load_model=False)

    protocols = []
    if serve_ca:
        protocols.append("ca")
    
    if serve_pva:
        protocols.append("pva")

    prefix = "test"
    server = Server(
        model_class,
        prefix,
        model_kwargs=model_kwargs
    )

    server.start(monitor=True)

if __name__ == "__main__":
    serve_from_template()