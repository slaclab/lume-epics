# lume-epics
Lume-epics is a dedicated API for serving LUME model variables. Configurations for LUME model variables can be found in [lume-model](https://github.com/slaclab/lume-model). lume-epics also houses controllers for interacting with the lume-epics server during application development. 

## Project layout
    docs/
    lume_epics/
        client/
            widgets/
                __init__.py
                plots.py
                sliders.py
                tables.py
            __init__.py
            controller.py
            monitors.py
        tests/
            __init__.py
            conftest.py
            test_server.py
            test_widgets.py
        __init__.py
        _version.py
        epics_server.py
        logconfig.py
        model.py
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

    

