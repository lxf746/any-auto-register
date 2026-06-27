"""Verify no production code imports from the deleted base_mailbox shim."""
import subprocess
import pathlib


def test_no_base_mailbox_imports():
    """No .py file (except base_mailbox.py itself and tests) should import from core.base_mailbox."""
    root = pathlib.Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["grep", "-rn", "from core.base_mailbox import", "--include=*.py", str(root)],
        capture_output=True,
        text=True,
    )
    # Filter out base_mailbox.py itself and test files
    lines = [
        l for l in result.stdout.splitlines()
        if "base_mailbox.py" not in l and "/tests/" not in l
    ]
    assert not lines, (
        f"Found deprecated core.base_mailbox imports:\n" + "\n".join(lines)
    )
