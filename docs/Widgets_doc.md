# Widgets

`Lume-epics` is packaged along with several widgets that can be used alongside a `lume-epics` controller to interact with the model process variables over EPICS. These widgets have bokeh attributes, which may be embedded into bokeh page layouts during client construction.

All widgets accept a `lume-epics` controller, and a `lume-model` variable or a list of variables for construction.

## Control widgets

These widgets are used for manipulating process variable values.

### Sliders

Sliders are used for setting process variable values along a continuous range. A utility function (`build_sliders.py`) has been provided that returns a list of slider widgets. The associated bokeh widget for rendering may be accessed on any slider by the `.slider` attribute.

An example implementation, including registered callbacks for continual value syncing with the server is included below:

```python
from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables
from lume_epics.client.widgets.controls import build_sliders
from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

# use example variables packaged with lume-epics
with open("examples/files/demo_config.yml.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

with open("examples/files/epics_config.yml.yml", "r") as f:
    epics_config = config_from_yaml(f)

# load variables
input_variables, output_variables = load_variables(variable_filename)

# set up controller
controller = Controller(epics_config)

# convert ot list for slider use
input_variables = list(input_variable.values())

# build sliders
sliders = build_sliders(input_variables, controller)

# render
curdoc().title = "Demo App"
curdoc().add_root(
            column([slider.bokeh_slider for slider in sliders])
        )

for slider in sliders:
    curdoc().add_periodic_callback(slider.update, 250)
```
### Entry table

The entry table is used for single value updates to process variables. Bulk modification can also be submitted using the entry table. The table is composed of labels and entry fields. The entry table is also packaged with a clear button, for clearing the entered values from the fields, and a submit button for sending the values to the process variables.


```python
from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables
from lume_epics.client.widgets.controls import EntryTable

from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

with open("examples/files/demo_config.yml.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

with open("examples/files/epics_config.yml.yml", "r") as f:
    epics_config = config_from_yaml(f)

# set up controller
controller = Controller(epics_config)

# conver to list for use with table
input_variables = list(input_variable.values())

# build entry table
entry_table = EntryTable(input_variables, controller)

# render
curdoc().title = "Demo App"
curdoc().add_root(
            row(entry_table.table, column(entry_table.submit, entry_table.clear))
        )
```

## Display widgets

### ImagePlot

Image plots are used for displaying image process variables. The image plot requires a manual call of the `build_plot` function which accepts a bokeh colormap or palette for rendering. The image update callback must be registed in order to sync with the server.

```python
from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables
from lume_epics.client.widgets.plots import ImagePlot

from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

with open("examples/files/demo_config.yml.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

with open("examples/files/epics_config.yml.yml", "r") as f:
    epics_config = config_from_yaml(f)

# set up controller
controller = Controller(epics_config)

# select our image output variable to render
image_output = [output_variables["output1"]]

# create image plot
image_plot = ImagePlot(image_output, controller)

pal = palettes.viridis(256)
color_mapper = LinearColorMapper(palette=pal, low=0, high=256)

image_plot.build_plot(color_mapper=color_mapper)

# render
curdoc().title = "Demo App"
curdoc().add_root(column(image_plot.plot))

# add image update callback
curdoc().add_periodic_callback(image_plot.update, 250)
```

### Striptool

The striptool includes a dropdown field for toggling between process variables. The striptool includes a selection toggle and a reset button, which may be rendered along with the plot.

```python
from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables
from lume_epics.client.widgets.plots import Striptool

from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

with open("examples/files/demo_config.yml.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

with open("examples/files/epics_config.yml.yml", "r") as f:
    epics_config = config_from_yaml(f)

# set up controller
controller = Controller(epics_config)

striptool = Striptool([output_variables["output2"], output_variables["output3"]], controller)

# render
curdoc().title = "Demo App"
curdoc().add_root(row(striptool.plot,  striptool.selection, striptool.reset_button))

# add striptool update callback
curdoc().add_periodic_callback(striptool.update, 250)

```

### ValueTable

The `ValueTable` widget is used for displaying process variables and their current values.


```python
from bokeh.io import curdoc
from bokeh import palettes
from bokeh.layouts import column, row

from lume_epics.client.controller import Controller
from lume_model.utils import load_variables
from lume_epics.client.widgets.table import ValueTable

from lume_model.utils import variables_from_yaml
from lume_epics.utils import config_from_yaml

with open("examples/files/demo_config.yml.yml", "r") as f:
    input_variables, output_variables = variables_from_yaml(f)

with open("examples/files/epics_config.yml.yml", "r") as f:
    epics_config = config_from_yaml(f)

# set up controller
controller = Controller(epics_config)

value_table = ValueTable([output_variables["output2"], output_variables["output3"]], controller)

# render
curdoc().title = "Demo App"
curdoc().add_root(value_table.table)

# add striptool update callback
curdoc().add_periodic_callback(value_table.update, 250)

```
