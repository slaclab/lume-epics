import click
import subprocess

@click.command()
@click.argument("filename")
@click.argument("protocol")
@click.argument("prefix")
@click.option("--read-only", default=False, type=bool)
def render_from_template(filename, protocol, prefix, read_only):
    subprocess.call(["bokeh", "serve", "bin/bokeh_template.py", "--show", "--args", filename, protocol, prefix, str(read_only)])


if __name__ == "__main__":
    render_from_template()
