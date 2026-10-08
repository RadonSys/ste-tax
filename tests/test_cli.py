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

    records = read_records(run)
    assert len(records) == 9
    assert [r.arm for r in records[:3]] == [Arm.A0, Arm.A2, Arm.A1]
    assert all(r.checker == Skipped("off") for r in records)
    assert all((r.rewrite is not None) == (r.arm is Arm.A2) for r in records)

    printed = capsys.readouterr().out
    assert summarize(records) in printed
    assert main(["summarize", str(run)]) == 0
    assert capsys.readouterr().out.strip() == summarize(records)


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
