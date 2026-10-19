"""`vela whoami --role`: a person says their role once, like their handle, and it is kept beside it.

The role is one of the dashboard's six. It defaults the onboarding path and the dashboard's own view of "what is mine";
the lead's record of someone (`roles:` in .vela.yaml) wins over it (see test_onboard_cli and test_onboard_data).
"""
import json

import pytest

from conftest import run


def whoami(vault, *argv):
    code, out = run("whoami", "--vault", str(vault), *argv, "--json")
    return code, json.loads(out)


@pytest.fixture
def vault(tmp_path):
    (tmp_path / ".vela").mkdir()
    (tmp_path / ".vela" / "handle").write_text("sam\n", encoding="utf-8")
    return tmp_path


def test_a_role_never_set_is_empty_so_the_skill_knows_to_ask(vault):
    code, said = whoami(vault)
    assert code == 0 and said["handle"] == "sam" and said["role"] == ""


@pytest.mark.parametrize("given, role", [("eng", "eng"), ("Engineer", "eng"), ("QA lead", "qa"), ("exec sponsor", "exec"), ("delivery manager", "mgr")])
def test_the_role_is_kept_beside_the_handle_and_shown_with_it(vault, given, role):
    code, said = whoami(vault, "--role", given)
    assert code == 0 and said["role"] == role and said["wrote"] == [".vela/role"]
    assert (vault / ".vela" / "role").read_text(encoding="utf-8") == role + "\n"
    assert whoami(vault)[1]["role"] == role and whoami(vault)[1]["handle"] == "sam"


def test_changing_the_role_replaces_it(vault):
    whoami(vault, "--role", "eng")
    whoami(vault, "--role", "product")
    assert whoami(vault)[1]["role"] == "product"


def test_a_word_that_is_no_role_is_refused_and_keeps_what_was_there(vault):
    whoami(vault, "--role", "eng")
    code, said = whoami(vault, "--role", "janitor")
    assert code == 1 and said["refusals"][0]["rule"] == "role" and "use one of: lead, exec, product, qa, eng, mgr" in said["refusals"][0]["fix"]
    assert whoami(vault)[1]["role"] == "eng"


def test_a_role_file_that_holds_something_else_is_not_a_role(vault):
    (vault / ".vela" / "role").write_text("janitor\n", encoding="utf-8")
    assert whoami(vault)[1]["role"] == ""


def test_whoamis_own_handle_check_refuses_a_trailing_newline():
    from vela.commands import whoami as who
    assert who.HANDLE.match("sam") and who.HANDLE.match("sam\n") is None
