# Fictional worktree review walkthrough

Extract the [Git Worktree Review Reporter 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/git-worktree-reporter-v0.1.0) and verify SHA256SUMS. Supply ordinary CPython 3.12, 3.13, 3.14 or 3.15; qualification selects 3.15.2 for that minor. Supply a separately approved trusted Git 2.49+ executable. Qualification uses pinned Git 2.56.1 on both operating systems; release VALIDATION.json records its archive/source and actual binary hashes. The source ZIP contains neither Git nor Python. No Python packages are required.

Choose an existing trusted private parent outside the source checkout, selected repositories, their Git metadata and public/synchronized folders. Replace all fictional absolute paths below with your actual source, Python, trusted Git and private parent. Use a new environment path. No administrator privilege, activation, account login, execution-policy change or system installation is part of these commands; actual permissions and workplace tool policy apply. The runtime never searches PATH for Git.

PowerShell:

```powershell
$source = 'D:\Source\git-worktree-reporter-0.1.0'
$gitExe = 'D:\Tools\approved-git\bin\git.exe'
$privateWork = 'D:\Private\worktree-review'
python -I -B -m venv --without-pip (Join-Path $privateWork 'new-environment')
$py = Join-Path $privateWork 'new-environment\Scripts\python.exe'
& $gitExe --version
& $py -I -B (Join-Path $source 'git_worktree_report.py') --help
```

Ubuntu:

```sh
source=/path/to/git-worktree-reporter-0.1.0
git_exe=/path/to/approved-git/bin/git
private_work=/path/to/private-worktree-review
python3 -I -B -m venv --without-pip "$private_work/new-environment"
py="$private_work/new-environment/bin/python"
"$git_exe" --version
"$py" -I -B "$source/git_worktree_report.py" --help
```

## Run the complete eleven-case exercise

Save the single Python block below as `fictional_walkthrough.py` in your private parent. Run it with assertions enabled, as shown. It creates one uniquely named workspace, invokes the preserved demo generator, creates five additional fictional repository/worktree roots and retains all results for inspection. It does not read or copy an existing project. Git, runtime and input paths are explicitly selected.

The generator and setup helper deliberately initialize repositories, write invented text, add files, create commits and add linked/detached worktrees **only inside their new fixture workspace**. Those are explicit fixture-building operations. The inspector itself runs read-only Git commands; it never stages, commits, checks out, fetches, pushes, backs up or restores a repository. Its calls must preserve all preexisting fixture/report file bytes and sampled metadata.

Five successful inspections cover dirty, clean, linked, detached and unborn worktrees. Dirty work returns exit 0. Five expected refusals cover an existing report, output inside a worktree, output inside linked/common metadata, unsupported filter configuration and invalid CLI arguments. Together with the generator there are six exit-0 outcomes and five exit-2 outcomes. Every stdout object and empty stderr is checked in full, including native line endings.

The script independently reads each complete `report.json` and MANIFEST.json, verifies the exact report byte length/hash and checks the supported report fields. Object IDs depend on actual fixture commits; it validates them against the newly created local repository and does not invent a fixed commit ID. Reports retain private filenames, branches and IDs. They are not anonymized, encrypted or publication-cleared.

PowerShell:

```powershell
& $py -I -B (Join-Path $privateWork 'fictional_walkthrough.py') $source $gitExe $privateWork
```

Ubuntu:

```sh
"$py" -I -B "$private_work/fictional_walkthrough.py" "$source" "$git_exe" "$private_work"
```

```python
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if not __debug__:
    raise RuntimeError("ASSERTIONS_REQUIRED")
assert len(sys.argv) == 4
source = Path(sys.argv[1]).resolve()
git = Path(sys.argv[2]).resolve()
parent = Path(sys.argv[3]).resolve()
assert source.is_dir() and git.is_file() and parent.is_dir()
assert not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)()
runtime_names = ("git_worktree_report.py", "examples/make_demo.py")
runtime = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
           for name in runtime_names}
work = Path(tempfile.mkdtemp(prefix="fictional-worktree-", dir=parent))
assert not work.is_relative_to(source)
env = {key: value for key, value in os.environ.items()
       if not key.upper().startswith(("GIT_", "GCM_", "SSH_", "PYTHON", "PIP_"))
       and key.upper() not in {"PAGER", "LD_PRELOAD", "LD_LIBRARY_PATH",
                               "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"}}
env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_SYSTEM=os.devnull,
           GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="",
           PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
version = subprocess.run([str(git), "--version"], env=env, capture_output=True,
                         stdin=subprocess.DEVNULL, timeout=15)
assert version.returncode == 0 and version.stderr == b""
match = re.fullmatch(rb"git version ([0-9]+)\.([0-9]+)\.([0-9]+)[^\r\n]*\r?\n", version.stdout)
assert match is not None and tuple(map(int, match.groups())) >= (2, 49, 0)
git_version = ".".join(str(int(value)) for value in match.groups())
outcomes = []
protected = []
reports = []

def snapshot():
    result = {}
    for root in protected:
        for path in root.rglob("*"):
            assert not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()
            if path.is_file():
                info = path.stat()
                result[path.relative_to(work).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest(), info.st_size,
                    info.st_mtime_ns, info.st_ino, info.st_nlink,
                    info.st_birthtime_ns if os.name == "nt" else info.st_ctime_ns)
    return result

def invoke(label, program, arguments, expected, exit_code=0, *, sorted_output=True):
    before = snapshot()
    done = subprocess.run([sys.executable, "-I", "-B", str(source / program),
                           *map(str, arguments)], cwd=work, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
    assert done.returncode == exit_code, (label, done.returncode)
    assert done.stderr == b"", label
    assert done.stdout == (json.dumps(expected, sort_keys=sorted_output)
                           + os.linesep).encode("utf-8"), label
    assert snapshot() == before, label
    assert runtime == {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                       for name in runtime_names}
    outcomes.append(dict(case=label, exit_code=exit_code, stdout=json.loads(done.stdout)))

def command(repo, *arguments):
    # These are deliberate setup/readback commands in our new fictional repos.
    done = subprocess.run([str(git), "-c", "core.hooksPath=" + os.devnull,
        "-c", "user.name=Fictional Reviewer", "-c", "user.email=review@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-C", str(repo),
        *map(str, arguments)], cwd=work, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=30)
    assert done.returncode == 0, "FICTIONAL_GIT_SETUP_OR_READBACK_FAILED"
    return done.stdout

def initialized(name, committed=False):
    repo = work / name
    repo.mkdir()
    command(repo, "init", "--initial-branch=main", "--template=")
    (repo / "note.txt").write_bytes(b"Invented review note.\n")
    if committed:
        command(repo, "add", "note.txt")
        command(repo, "commit", "-m", "Fictional review baseline")
    return repo

def summary(head_state, *, staged=0, unstaged=0, untracked=0):
    counts = dict(staged=staged, unstaged=unstaged, untracked=untracked, unmerged=0)
    return dict(status="LOCAL_STATUS_RECORDED", head_state=head_state,
                entry_count=staged + unstaged + untracked, counts=counts)

def inspect(label, repo, head_state, branch, entries, **counts):
    output = work / (label + "-report")
    expected = summary(head_state, **counts)
    invoke(label, "git_worktree_report.py", ["--repo", repo, "--git-executable", git,
           "--output", output], expected)
    assert {path.name for path in output.iterdir()} == {"report.json", "MANIFEST.json"}
    raw = (output / "report.json").read_bytes()
    manifest = json.loads((output / "MANIFEST.json").read_bytes())
    assert manifest == dict(schema_version=1, files=[dict(path="report.json", bytes=len(raw),
                             sha256=hashlib.sha256(raw).hexdigest())])
    report = json.loads(raw)
    assert raw == (json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    assert set(report) == {"schema_version", "tool", "head_oid", "branch", "head_state",
        "upstream", "entry_count", "entries", "counts", "ignored_header_count",
        "status_sha256", "coverage", "interpretation", "git_version",
        "observed_control_files_unchanged", "configuration", "subprocess_limits"}
    assert report["schema_version"] == 1 and report["tool"] == "git-worktree-reporter"
    assert report["head_state"] == head_state and report["branch"] == branch
    assert report["entry_count"] == expected["entry_count"] and report["counts"] == expected["counts"]
    assert report["entries"] == entries
    assert report["upstream"] == dict(name=None, ahead=None, behind=None,
        basis="stored_local_refs_only_no_network_refresh", comparison="unavailable")
    assert report["observed_control_files_unchanged"] is True
    assert report["git_version"] == git_version
    assert report["configuration"] == "global_system_disabled_local_includes_filters_partial_clones_refused"
    assert report["subprocess_limits"] == dict(seconds_each=15, stdout_bytes=8 * 1024 * 1024,
        stderr_bytes=65536, max_entries=10000)
    assert report["coverage"] == "selected_worktree_status_excluding_ignored_and_submodule_contents"
    assert report["interpretation"] == ("Git status observations under isolated configuration, not a backup, "
        "content inventory, secret scan, ownership or publication clearance.")
    assert re.fullmatch("[0-9a-f]{64}", report["status_sha256"])
    assert report["ignored_header_count"] == 0
    if head_state == "unborn":
        assert report["head_oid"] is None
    else:
        assert re.fullmatch("[0-9a-f]{40}|[0-9a-f]{64}", report["head_oid"])
        assert report["head_oid"] == command(repo, "rev-parse", "HEAD").decode().strip()
    assert str(work) not in raw.decode("utf-8")
    reports.append(output)
    protected.append(output)
    return output

dirty = work / "invented-dirty"
invoke("create-fictional-demo", "examples/make_demo.py",
       ["--destination", dirty, "--git-executable", git],
       dict(status="FICTIONAL_REPOSITORY_CREATED", expected_entries=3), sorted_output=False)
protected.append(dirty)
dirty_entries = [
    dict(kind="tracked", path="README.md", index_status=".", worktree_status="M", submodule=None),
    dict(kind="untracked", path="new item.txt", index_status="?", worktree_status="?", submodule=None),
    dict(kind="tracked", path="staged.txt", index_status="M", worktree_status=".", submodule=None)]
dirty_report = inspect("dirty", dirty, "branch", "main", dirty_entries,
                       staged=1, unstaged=1, untracked=1)
clean = initialized("invented-clean", committed=True)
protected.append(clean)
inspect("clean", clean, "branch", "main", [])
linked = work / "invented-linked"
command(clean, "worktree", "add", "-b", "fictional-linked", linked)
protected.append(linked)
inspect("linked", linked, "branch", "fictional-linked", [])
detached = work / "invented-detached"
command(clean, "worktree", "add", "--detach", detached, "HEAD")
protected.append(detached)
inspect("detached", detached, "detached", None, [])
unborn = initialized("invented-unborn")
protected.append(unborn)
inspect("unborn", unborn, "unborn", "main",
        [dict(kind="untracked", path="note.txt", index_status="?", worktree_status="?", submodule=None)],
        untracked=1)

def refuse(label, repo, output, code):
    invoke(label, "git_worktree_report.py", ["--repo", repo, "--git-executable", git,
           "--output", output], dict(status="INCOMPLETE", error=code), 2)

refuse("refuse-existing-report", dirty, dirty_report, "FRESH_OUTPUT_REQUIRED")
refuse("refuse-worktree-output", clean, clean / "new-report", "OUTPUT_INSIDE_WORKTREE")
refuse("refuse-common-metadata-output", linked, clean / ".git" / "new-report",
       "OUTPUT_INSIDE_GIT_METADATA")
blocked = initialized("invented-filter-config")
command(blocked, "config", "filter.fictional.clean", "fictional-unused-placeholder")
protected.append(blocked)
refuse("refuse-filter-config", blocked, work / "not-created-filter-report",
       "CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED")
invoke("refuse-invalid-arguments", "git_worktree_report.py", [],
       dict(status="INCOMPLETE", error="ARGUMENTS_INVALID"), 2)
assert {path.name for path in work.iterdir()} == {
    "invented-dirty", "invented-clean", "invented-linked", "invented-detached",
    "invented-unborn", "invented-filter-config", "dirty-report", "clean-report",
    "linked-report", "detached-report", "unborn-report"}
assert not (clean / "new-report").exists()
assert not (clean / ".git" / "new-report").exists()
assert not (work / "not-created-filter-report").exists()
assert not list(work.rglob("*.pyc")) and not list(work.rglob("__pycache__"))
assert len(outcomes) == 11 and len(reports) == 5
print(json.dumps(dict(outcomes=outcomes, reports_verified=5, fixture_roots=6,
    inspector_repository_writes=0, unexpected_application_files=0, bytecode_files=0,
    runtime_bytes_preserved=True, real_repositories_inspected=False), sort_keys=True, indent=2))
```

## Complete CLI outcomes

Each stdout object is the complete decoded output for that invocation. The wrapper prints these outcomes and its final checks. Source/report JSON is read in full locally; report object IDs and hashes can vary with the newly created commits.

```json
[
  {
    "case": "create-fictional-demo",
    "exit_code": 0,
    "stdout": {
      "status": "FICTIONAL_REPOSITORY_CREATED",
      "expected_entries": 3
    }
  },
  {
    "case": "dirty",
    "exit_code": 0,
    "stdout": {
      "status": "LOCAL_STATUS_RECORDED",
      "head_state": "branch",
      "entry_count": 3,
      "counts": {
        "staged": 1,
        "unstaged": 1,
        "untracked": 1,
        "unmerged": 0
      }
    }
  },
  {
    "case": "clean",
    "exit_code": 0,
    "stdout": {
      "status": "LOCAL_STATUS_RECORDED",
      "head_state": "branch",
      "entry_count": 0,
      "counts": {
        "staged": 0,
        "unstaged": 0,
        "untracked": 0,
        "unmerged": 0
      }
    }
  },
  {
    "case": "linked",
    "exit_code": 0,
    "stdout": {
      "status": "LOCAL_STATUS_RECORDED",
      "head_state": "branch",
      "entry_count": 0,
      "counts": {
        "staged": 0,
        "unstaged": 0,
        "untracked": 0,
        "unmerged": 0
      }
    }
  },
  {
    "case": "detached",
    "exit_code": 0,
    "stdout": {
      "status": "LOCAL_STATUS_RECORDED",
      "head_state": "detached",
      "entry_count": 0,
      "counts": {
        "staged": 0,
        "unstaged": 0,
        "untracked": 0,
        "unmerged": 0
      }
    }
  },
  {
    "case": "unborn",
    "exit_code": 0,
    "stdout": {
      "status": "LOCAL_STATUS_RECORDED",
      "head_state": "unborn",
      "entry_count": 1,
      "counts": {
        "staged": 0,
        "unstaged": 0,
        "untracked": 1,
        "unmerged": 0
      }
    }
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "FRESH_OUTPUT_REQUIRED"
    }
  },
  {
    "case": "refuse-worktree-output",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "OUTPUT_INSIDE_WORKTREE"
    }
  },
  {
    "case": "refuse-common-metadata-output",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "OUTPUT_INSIDE_GIT_METADATA"
    }
  },
  {
    "case": "refuse-filter-config",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED"
    }
  },
  {
    "case": "refuse-invalid-arguments",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "ARGUMENTS_INVALID"
    }
  }
]
```

The workspace retains six fixture roots and five new two-file reports. Expected refusals create no additional report paths. Existing repositories, reports and runtime bytes must stay unchanged during inspector calls; no bytecode or unexpected application files are accepted within the fixture workspace.

These examples do not inject a late output failure. Such a failure can retain a new partial report directory, returns exit 2 and must not be described as completed. Keep it private and use a different new destination for a retry. No overwrite, cleanup or rollback is performed. Native failure/partial-output controls are separate qualification cases.

Upstream comparisons use stored local refs; the report performs no network refresh. Global ignore/attribute/config isolation can differ from normal interactive Git. Ignored files, submodule contents, complete LFS preservation and recovery are outside the report. Use one operator with stable trusted local files; this is not an atomic snapshot, hostile-repository sandbox, backup or proof of publication rights. See [current qualification](docs/QUALIFICATION.md), the preserved [format contract](docs/FORMAT.md) and [private workspace guidance](docs/PRIVATE-WORKSPACE.md).
