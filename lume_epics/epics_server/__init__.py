from online_model.server import ca, pva


def get_server(
    prefix: str,
    model_class,
    model_kwargs: dict,
    protocol: str,
    data_file: str,
    array_pvs: List[str] = [],
) -> Union[ca.CAServer, pva.PVAServer]:

    pickled_data = open(data_file, "rb")
    data = pickle.load(pickled_data)

    input_pvdb, output_pvdb = pvdb_from_classes(data, protocol)

    if protocol == "ca":
        server = ca.CAServer(
            model_class, model_kwargs, input_pvdb, output_pvdb, prefix, array_pvs
        )

    elif protocol == "pva":
        server = pva.PVAServer(
            model_class, model_kwargs, input_pvdb, output_pvdb, prefix, array_pvs
        )

    else:
        raise Exception("Must use ca or pva for protocol.")

    return server
