from klara_core.stressor import ROBO9_STS3215, JointStressor, StressorParams


def make(params: StressorParams | None = None, n: int = 1) -> JointStressor:
    return JointStressor(params or ROBO9_STS3215, n_joints=n)


def test_deterministic_per_seed():
    a, b = make(), make()
    seq = [[0.0], [30.0], [15.0], [15.2], [60.0]]
    assert [a.perturb(c) for c in seq] == [b.perturb(c) for c in seq]


def test_different_seeds_diverge():
    a = make(StressorParams(seed=1))
    b = make(StressorParams(seed=2))
    assert a.perturb([30.0]) != b.perturb([30.0])


def test_deadband_holds_position():
    s = make(StressorParams(repeatability_deg=0.0))
    (start,) = s.perturb([10.0])
    # A command within the ~0.88 deg deadband of current position must not move.
    (held,) = s.perturb([start + 0.5 * ROBO9_STS3215.deadband_deg])
    assert held == start


def test_backlash_absorbs_reversal_travel():
    p = StressorParams(repeatability_deg=0.0, deadband_counts=0)
    s = make(p)
    s.perturb([0.0])
    s.perturb([30.0])  # establish +1 direction; lands exactly at 30
    (reached,) = s.perturb([20.0])  # reversal: 10 deg commanded, backlash eats 0.85
    assert abs(reached - (30.0 - (10.0 - p.backlash_deg))) < 1e-9


def test_noise_bounded_by_repeatability():
    p = StressorParams(deadband_counts=0, backlash_deg=0.0)
    s = make(p)
    prev = s.perturb([0.0])[0]
    target = 0.0
    for _ in range(200):
        target += 5.0
        (reached,) = s.perturb([target])
        assert abs(reached - target) <= p.repeatability_deg + 1e-9
        assert reached != prev
        prev = reached
