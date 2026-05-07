from fitness_app.routes.cycling import (
    calculate_calories as cycling_calories,
)
from fitness_app.routes.cycling import (
    get_cycling_met,
)
from fitness_app.routes.running import (
    calculate_calories as running_calories,
)
from fitness_app.routes.running import (
    get_running_met,
)
from fitness_app.routes.swimming import (
    calculate_calories as swimming_calories,
)
from fitness_app.routes.swimming import (
    get_swimming_met,
)
from fitness_app.routes.walking import (
    calculate_calories as walking_calories,
)
from fitness_app.routes.walking import (
    get_walking_met,
)


def test_running_calories_valid():
    """Valid inputs return correct calories."""
    assert running_calories(9.8, 70, 30) == 343


def test_running_calories_missing_weight():
    """Missing weight returns None."""
    assert running_calories(9.8, None, 30) is None


def test_running_met_fast_run():
    """Fast run gives high MET."""
    assert get_running_met(5, 20) >= 9.8


def test_walking_calories_valid():
    """Valid inputs return correct calories."""
    assert walking_calories(3.5, 70, 60) == 245


def test_walking_met_slow_walk():
    """Slow walk returns lowest MET."""
    assert get_walking_met(1, 30) == 2.5


def test_walking_met_fast_walk():
    """Fast walk returns highest MET."""
    assert get_walking_met(4, 30) >= 7.0


def test_cycling_calories_valid():
    """Valid inputs return correct calories."""
    assert cycling_calories(8.0, 70, 60) == 560


def test_cycling_met_no_speed():
    """No speed returns default MET."""
    assert get_cycling_met(None) == 6.0


def test_cycling_met_fast_speed():
    """Fast speed returns max MET."""
    assert get_cycling_met(30) == 12.0


def test_swimming_calories_valid():
    """Valid inputs return correct calories."""
    assert swimming_calories(6.0, 70, 30) == 210


def test_swimming_met_missing_distance():
    """Missing distance returns default MET."""
    assert get_swimming_met(None, 30) == 6.0


def test_swimming_met_fast_pace():
    """Fast pace returns highest MET."""
    assert get_swimming_met(1, 14) == 10.0
