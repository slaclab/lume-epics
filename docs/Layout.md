# Project layout

    docs/
        Controller.md
        Index.md
        Install.md
        Layout.md
        Model.md
        Monitors.md
        QuickStart.md
        Server.md
    lume_epics/
        client/
            widgets/
                __init__.py
                plots.py    # Bokeh figure-based widgets
                controls.py # Widgets for controlling input variables 
                tables.py   # Table based widgets
            __init__.py
            controller.py   # Controller for accessing EPICS process variables
            monitors.py     # Artifacts for monitoring process variables by variable type
        tests/
            __init__.py
            conftest.py
            test_server.py
            test_widgets.py
        __init__.py
        _version.py
        epics_server.py # EPICS server 
        logconfig.py
        model.py    # Online serving of the surrogate model
    mkdocs.yml    # Docs configuration file.
    README.md
    requirements.txt    # run requirements
    dev-requirements.txt # development requirments
    docs-requirements.txt # requirements for building docs
    setup.cfg
    setup.py
    versioneer.py
    LICENSE
    MANIFEST.in
    .travis.yml
    .pre-commit-config.yml

    

