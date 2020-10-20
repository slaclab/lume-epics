from lume_model.utils import model_from_yaml


def serve_from_yaml(config_filename: str, prefix: str, serve_ca: bool = True, serve_pva: bool = True):
    """Serves model from a configuration file.

    Args:
        config_filename (str): Configuration file to reference
        prefix (str): Prefix for serving variables
        serve_ca (bool): Whether or not to serve with channel access
        serve_pva (bool): Whether or not to serve with pvAccess

    """

    # load model
    with open(config_filename, "r") as f:
        model_class, model_kwargs = model_from_yaml(f, load_model=False)

    server = Server(
        model_class,
        prefix,
        model_kwargs=model_kwargs
        protocols
    )

    server.start()