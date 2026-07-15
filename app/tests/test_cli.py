import json
from typer.testing import CliRunner
from trader.cli import app

runner = CliRunner()

def test_init_scaffolds(tmp_path):
    r = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert (tmp_path / "config.json").exists() and (tmp_path / "stocks.json").exists()

def test_init_refuses_overwrite(tmp_path):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    r = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert r.exit_code != 0

def test_list_numbers_stocks(tmp_path):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    (tmp_path / "stocks.json").write_text(json.dumps({"stocks": ["RELIANCE", "TCS"]}))
    r = runner.invoke(app, ["list", "--dir", str(tmp_path)])
    assert r.exit_code == 0 and "1" in r.output and "RELIANCE" in r.output and "TCS" in r.output
