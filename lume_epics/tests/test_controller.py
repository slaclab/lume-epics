import pytest
import time
import numpy as np
import epics


@pytest.fixture(scope="module")
def image_variables(model):
    return [
        var for var in model.input_variables.values() if var.variable_type == "image"
    ]


def test_controller_image_get(controller, image_variables, server):
    for var in image_variables:
        image = controller.get_image(var.name)


# @pytest.mark.skip(reason="Skip until pytest-ordering is compatable with 3.8")
# @pytest.mark.last
@pytest.mark.parametrize("x_min,x_max,y_min,y_max", [(0, 10, 0, 5), (5, 10, 4, 5)])
def test_controller_image_update(
    x_min, x_max, y_min, y_max, controller, image_variables, epics_config, server
):

    for var in image_variables:

        pvname = epics_config[var.name]["pvname"]
        new_image = np.random.uniform(0, 1, size=var.default.shape)

        controller.put_image(
            var.name, new_image, x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max
        )

        time.sleep(1)

        image_array_served = epics.caget(f"{pvname}:ArrayData_RBV")

        assert (image_array_served == new_image.flatten()).all()

        x_min_served = epics.caget(f"{pvname}:MinX_RBV")
        assert x_min == x_min_served

        y_min_served = epics.caget(f"{pvname}:MinY_RBV")
        assert y_min == y_min_served

        x_max_served = epics.caget(f"{pvname}:MaxX_RBV")
        assert x_max == x_max_served

        y_max_served = epics.caget(f"{pvname}:MaxY_RBV")
        assert y_max == y_max_served

        # reset variables
        controller.put_image(
            var.name,
            var.default,
            x_min=var.x_min,
            y_min=var.y_min,
            x_max=var.x_max,
            y_max=var.y_max,
        )
