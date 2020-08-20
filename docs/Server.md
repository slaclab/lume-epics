# EPICS Server

The lume-epics server synchronizes process variables over Channel Access and pvAccess servers. Updates to input process variables are queued for model execution and the model output is queued for updates over both protocols. 

![Server Structure](img/lume-epics.jpeg)


::: lume_epics.epics_server

::: lume_epics.epics_ca_server

::: lume_epics.epics_pva_server