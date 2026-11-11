from amar_tax.settings import EnvLoader


def test_dotenv_rotation_removal_and_shell_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shell-test-key")
    path = tmp_path / ".env"
    loader = EnvLoader()
    path.write_text('OPENAI_API_KEY="first-test-key"\n', encoding="utf-8-sig")
    loader.load(path)
    import os
    assert os.environ["OPENAI_API_KEY"] == "first-test-key"
    path.write_text("OPENAI_API_KEY=second-test-key\n", encoding="utf-8")
    loader.load(path)
    assert os.environ["OPENAI_API_KEY"] == "second-test-key"
    path.unlink()
    loader.load(path)
    assert os.environ["OPENAI_API_KEY"] == "shell-test-key"


def test_dotenv_blank_key_and_allowed_settings_only(tmp_path, monkeypatch):
    import os
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("UNRELATED_SETTING", "original")
    path = tmp_path / ".env"
    path.write_text("OPENAI_API_KEY=\nUNRELATED_SETTING=changed\n", encoding="utf-8")
    loader = EnvLoader()
    loader.load(path)
    assert os.environ["OPENAI_API_KEY"] == ""
    assert os.environ["UNRELATED_SETTING"] == "original"
    path.write_text("", encoding="utf-8")
    loader.load(path)
    assert "OPENAI_API_KEY" not in os.environ
