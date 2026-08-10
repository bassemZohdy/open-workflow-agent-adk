from openworkflow_adk.cli import main


def test_cli_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["owf-adk"])
    assert main() == 0
    assert "run" in capsys.readouterr().out
