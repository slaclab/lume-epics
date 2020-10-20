import click
import subprocess
from lume_epics.commands import bokeh_template

@click.command()
@click.argument("filename")
@click.argument("protocol")
@click.argument("prefix")
@click.option("--read-only", is_flag=True)
def render_from_template(filename, protocol, prefix, read_only):
    template_file = bokeh_template.__file__
    if read_only:
        subprocess.call(["bokeh", "serve", template_file, "--show", "--args", filename, protocol, prefix, "--read-only"])
    else:
        subprocess.call(["bokeh", "serve", template_file, "--show", "--args", filename, protocol, prefix])

if __name__ == "__main__":
    render_from_template()
