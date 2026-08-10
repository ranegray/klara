from klara_core.records import EpisodeRecord, TurnRecord, append_record, read_records
from klara_core.stressor import ROBO9_STS3215


def sample(i: int = 0) -> EpisodeRecord:
    return EpisodeRecord(
        episode_id=f"ep-{i:04d}",
        task="cube_pick_place",
        backend="isaac",
        rung=2,
        model="test-model",
        machinery=["multi_turn"],
        seed=i,
        stressor=ROBO9_STS3215.to_dict(),
        success=i % 2 == 0,
        failure_category=None if i % 2 == 0 else "PERCEPTION",
        turns=[
            TurnRecord(index=0, prompt_tokens=1200, completion_tokens=300, wall_clock_s=2.1),
            TurnRecord(index=1, prompt_tokens=1500, completion_tokens=250, wall_clock_s=1.8,
                       primitive_calls=["pick(cube)"]),
        ],
        wall_clock_s=45.0,
        started_at="2026-08-10T14:00:00-06:00",
        git_sha="abc1234",
    )


def test_token_totals():
    r = sample()
    assert r.total_prompt_tokens == 2700
    assert r.total_completion_tokens == 550
    assert r.total_tokens == 3250


def test_jsonl_roundtrip(tmp_path):
    path = tmp_path / "runs.jsonl"
    for i in range(3):
        append_record(path, sample(i))
    back = read_records(path)
    assert [r.episode_id for r in back] == ["ep-0000", "ep-0001", "ep-0002"]
    assert back[1].failure_category == "PERCEPTION"
    assert back[0].turns[1].primitive_calls == ["pick(cube)"]
    assert back[0].total_tokens == 3250


def test_scripted_robot_satisfies_protocol():
    from klara_core.api import RobotAPI
    from klara_core.testing import ScriptedRobot

    assert isinstance(ScriptedRobot(), RobotAPI)
