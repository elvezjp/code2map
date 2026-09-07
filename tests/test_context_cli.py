"""Public command entry points and validation of persisted context artifacts."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from code2map import build_index, pack_index, validate_pack
from code2map.context.model import canonical, digest


ROOT = Path(__file__).resolve().parents[1]


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "code2map", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_module_commands_and_version(tmp_path):
    index = tmp_path / "index.json"
    packed = tmp_path / "pack.json"
    assert invoke("--version").stdout.strip() == "code2map 0.4.0"
    assert invoke("index", ROOT / "examples", "--output", index).returncode == 0
    assert (
        invoke("pack", index, "--output", packed, "--budget-bytes", 16000).returncode
        == 0
    )
    assert invoke("check", index, "--pack", packed).returncode == 0
    data = json.loads(index.read_text())
    assert data["generator"] == "code2map/0.4.0"
    assert invoke("tree", index, "--depth", 1).returncode == 0
    node = data["nodes"][0]
    assert invoke("show", index, node["id"]).returncode == 0
    assert invoke("show", index, "missing-node").returncode == 2
    assert (
        invoke("pack", index, "--output", packed, "--budget-bytes", 1).returncode == 3
    )
    assert invoke("check", index, "--pack", packed).returncode == 0
    assert (
        invoke("pack", index, "--output", packed, "--budget-bytes", 0).returncode == 2
    )
    index.write_text("{broken")
    assert invoke("check", index).returncode == 2


def test_unknown_source_exit_code(tmp_path):
    source = tmp_path / "bad.java"
    source.write_text("class Example { ???")
    index = tmp_path / "index.json"
    assert invoke("index", source, "--output", index).returncode == 3
    assert invoke("check", index).returncode == 0


def test_omissions_and_summary_are_checked(tmp_path):
    source = tmp_path / "example.py"
    source.write_text("def helper():\n    pass\ndef work():\n" + "    helper()\n" * 100)
    index = build_index(source)
    packed = pack_index(index, budget=2500, dependency_limit=0)
    assert any(p["omitted_context"] for p in packed["packets"])
    corrupt = copy.deepcopy(packed)
    next(p for p in corrupt["packets"] if p["omitted_context"])["omitted_context"] = []
    with pytest.raises(ValueError, match="missing dependency"):
        validate_pack(index, corrupt)
    corrupt = copy.deepcopy(packed)
    corrupt["summary"]["ready"] += 1
    with pytest.raises(ValueError, match="summary"):
        validate_pack(index, corrupt)
    corrupt = copy.deepcopy(packed)
    corrupt["policy"]["algorithm"] = "unknown"
    with pytest.raises(ValueError, match="algorithm"):
        validate_pack(index, corrupt)


def test_unrelated_dependency_cannot_be_injected(tmp_path):
    source = tmp_path / "example.py"
    source.write_text("def unrelated():\n    pass\ndef work():\n    pass\n")
    index = build_index(source)
    packed = pack_index(index)
    packet = packed["packets"][0]
    body = json.loads(packet["payload"])
    body["dependency_context"] = [{"node_id": index["nodes"][1]["id"]}]
    packet["payload"] = canonical(body)
    packet["payload_sha256"] = digest(packet["payload"])
    packet["budget_used"] = len(packet["payload"].encode("utf-8"))
    with pytest.raises(ValueError, match="invalid dependency"):
        validate_pack(index, packed)
