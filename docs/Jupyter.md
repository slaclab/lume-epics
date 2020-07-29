# Jupyter Notebook Demo

This demo follows the simple implementation outlined in [lume-model-server-demo](https://github.com/jacquelinegarrahan/lume-model-server-demo). A conda installation is required for setting up the required packages.

## Clone the demo repository

``` $ git clone https://github.com/jacquelinegarrahan/lume-model-server-demo.git ```

## Navigate to the demo repository

``` $ cd lume-model-server-demo ```

## Set up and activate conda environment

Create the environment using conda and the environment.yml file included with the repository:

``` $ conda env create -f environment.yml ```

Activate the environment:

``` $ conda activate lume-model-server-demo```

## Set up the ipython kernel

```$ python -m ipykernel install --user --name=lume-model-server-demo ```

## Launch Jupyter

``` $ jupyter notebook ```

## Run demo

In two tabs, open the `SimpleServer` and `SimpleClient` notebooks. Begin by following the code outlined in the `SimpleServer` notebook, and then execute the code in the `SimpleClient` to render the application. Finally, terminate the server using the `Server.stop()` method in the `SimpleServer` notebook.
