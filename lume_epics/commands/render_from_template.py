import click
import subprocess
from lume_epics.commands import bokeh_template


@click.command()
@click.argument("filename")
@click.argument("epics_config_filename")
@click.option("--read-only", is_flag=True)
@click.option("--striptool-limit", default=50)
@click.option("--ncol-widgets", default=5)
def render_from_template(
    filename, epics_config_filename, read_only, striptool_limit, ncol_widgets
):
    template_file = bokeh_template.__file__
    if read_only:
        subprocess.call(
            [
                "bokeh",
                "serve",
                template_file,
                "--show",
                "--args",
                filename,
                epics_config_filename,
                "--striptool-limit",
                str(striptool_limit),
                "--ncol-widgets",
                str(ncol_widgets),
                "--read-only",
            ]
        )
    else:
        subprocess.call(
            [
                "bokeh",
                "serve",
                template_file,
                "--show",
                "--args",
                filename,
                epics_config_filename,
                "--striptool-limit",
                str(striptool_limit),
                "--ncol-widgets",
                str(ncol_widgets),
            ]
        )


if __name__ == "__main__":
    render_from_template()
