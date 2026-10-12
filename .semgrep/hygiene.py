import subprocess, yaml  # noqa: F401 - semgrep rule example
# ruleid: todo-needs-owner-and-reason
# TODO fix this
# ok: todo-needs-owner-and-reason
# TODO(jason): drop after the v4 catalogue lands; see #41
def run(root):
    # ruleid: subprocess-needs-timeout
    subprocess.run(["git", "-C", root, "status"], capture_output=True)
    # ok: subprocess-needs-timeout
    subprocess.run(["git", "-C", root, "status"], capture_output=True, timeout=10)
    # ruleid: text-io-needs-encoding
    page = path.read_text()  # noqa: F841 - semgrep rule example
    # ok: text-io-needs-encoding
    page = path.read_text(encoding="utf-8")  # noqa: F841 - semgrep rule example
    # ruleid: text-io-needs-encoding
    open(path, "w")
    # ok: text-io-needs-encoding
    open(path, "rb")
