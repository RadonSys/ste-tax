"""End to end on the mock backend: manifest, records, summary read back."""

import json

from eval.cli import main, read_records
from eval.harness import summarize
from eval.records import Arm, Skipped


def test_mock_run_writes_manifest_and_records(tmp_path, capsys):
    code = main(
        [
            "run",
            "--backend",
            "mock",
            "--limit",
            "3",
            "--checker",
            "off",
            "--results",
            str(tmp_path),
            "--run-id",
            "r1",
        ]
    )
    assert code == 0
    run = tmp_path / "r1"
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["mode"] == "arms" and manifest["arms"] == ["A0", "A2", "A1"]
    assert len(manifest["tasks"]["ids"]) == 3
    assert manifest["finished"] is not None
    assert manifest["git"]["ste-tax"]["commit"]
    assert "eval/tasks.jsonl" in manifest["tasks"]["files"]
    assert {"rocminfo", "rocm-smi", "packages"} <= manifest["environment"].keys()
    assert manifest["config"]["prefix_caching"] is False
    assert manifest["config"]["wordlist"] == "ids"
    config = manifest["config"]
    assert config["decoding"] == "thinking"
    assert (config["temperature"], config["top_p"], config["top_k"]) == (1.0, 0.95, 20)
    assert (config["max_new_tokens"], config["samples"]) == (16384, 3)

    records = read_records(run)
    assert len(records) == 27  # 3 tasks x 3 samples x 3 arms
    assert [r.arm for r in records[:3]] == [Arm.A0, Arm.A2, Arm.A1]
    assert [r.sample for r in records[:9]] == [0, 0, 0, 1, 1, 1, 2, 2, 2]
    assert all(r.checker == Skipped("off") for r in records)
    assert all((r.rewrite is not None) == (r.arm is Arm.A2) for r in records)

    printed = capsys.readouterr().out
    assert summarize(records) in printed
    assert main(["summarize", str(run)]) == 0
    assert capsys.readouterr().out.strip() == summarize(records)


def test_greedy_preset_and_override(tmp_path):
    args = ["run", "--limit", "1", "--checker", "off", "--results", str(tmp_path)]
    assert main([*args, "--run-id", "g", "--decoding", "greedy"]) == 0
    config = json.loads((tmp_path / "g" / "manifest.json").read_text())["config"]
    assert (config["temperature"], config["max_new_tokens"], config["samples"]) == (
        0.0,
        1024,
        1,
    )
    assert len(read_records(tmp_path / "g")) == 3
    assert main([*args, "--run-id", "o", "--samples", "2"]) == 0
    config = json.loads((tmp_path / "o" / "manifest.json").read_text())["config"]
    assert (config["samples"], config["temperature"]) == (2, 1.0)


def test_run_refuses_existing_run_dir(tmp_path):
    args = [
        "run",
        "--limit",
        "1",
        "--checker",
        "off",
        "--results",
        str(tmp_path),
        "--run-id",
        "x",
    ]
    assert main(args) == 0
    try:
        main(args)
    except FileExistsError:
        return
    raise AssertionError("second run with the same id must fail")


def test_bad_task_file_exits_1(tmp_path, capsys):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "x"}\n')
    assert main(["tasks", "--tasks", str(bad)]) == 1
    assert "missing keys" in capsys.readouterr().err
