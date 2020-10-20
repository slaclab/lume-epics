import click
import subprocess
from lume_epics.commands import bokeh_template

@click.command()
@click.argument("filename")
@click.argument("protocol")
@click.argument("prefix")
@click.option("--read-only", default=False, type=bool)
def render_from_template(filename, protocol, prefix, read_only):
    template_file = bokeh_template.__file__
    subprocess.call(["bokeh", "serve", template_file, "--show", "--args", filename, protocol, prefix, str(read_only)])


if __name__ == "__main__":
    render_from_template()
