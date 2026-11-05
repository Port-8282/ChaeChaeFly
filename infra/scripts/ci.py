"""CI-only checks. Docker contexts and docker cp also work with a remote DinD daemon.

Run from any directory: python3 infra/scripts/ci.py all
Jenkins invokes individual phases and always invokes cleanup. No push or deployment.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "ci-results"
STATE = RESULTS / "state.json"
LABEL = "io.port8282.ci-run"
CONTEXTS = {"front": "front", "back": "back", "ai": "ai-data/ai-service", "ml": "ai-data/ml-service"}
PHASES = ("config", "front", "back", "ai", "ml", "smoke")


class Failure(RuntimeError):
    pass


def save(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load():
    if not STATE.exists():
        raise Failure("Run init first; ci-results/state.json is missing.")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if len(state.get("id", "")) != 12 or any(c not in "0123456789abcdef" for c in state["id"]):
        raise Failure("Invalid CI state; refusing Docker resource operations.")
    return state


def command(args, *, timeout=900, check=True):
    """Write full command output to an artifact; show only a failure tail in Jenkins."""
    RESULTS.mkdir(exist_ok=True)
    number = len(list(RESULTS.glob("command-*.log"))) + 1
    log = RESULTS / f"command-{number:03d}.log"
    print("+ " + shlex.join(map(str, args)), flush=True)
    with log.open("w", encoding="utf-8") as output:
        output.write("$ " + shlex.join(map(str, args)) + "\n")
        output.flush()
        try:
            result = subprocess.run(args, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                    timeout=timeout, text=True, check=False)
        except subprocess.TimeoutExpired as exc:
            raise Failure(f"Command timed out after {timeout}s; see {log.name}") from exc
    if result.returncode and check:
        tail = log.read_text(encoding="utf-8", errors="replace")[-6000:]
        print(tail, file=sys.stderr)
        raise Failure(f"Exit {result.returncode}; see {log.name}")
    return result.returncode


def capture(args, *, timeout=30):
    try:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise Failure("Timed out: " + shlex.join(args)) from exc
    if result.returncode:
        raise Failure(result.stderr.strip() or "Command failed: " + shlex.join(args))
    return result.stdout.strip()


def report(name, *, error=None, skipped=None, elapsed=0):
    suite = ET.Element("testsuite", name=name, tests="1", failures=str(int(error is not None)),
                       skipped=str(int(skipped is not None)), time=f"{elapsed:.3f}")
    case = ET.SubElement(suite, "testcase", classname="infra.ci", name=name, time=f"{elapsed:.3f}")
    if error is not None:
        ET.SubElement(case, "failure", message=str(error)).text = str(error)
    if skipped is not None:
        ET.SubElement(case, "skipped", message=skipped).text = skipped
    ET.ElementTree(suite).write(RESULTS / f"{name}.xml", encoding="utf-8", xml_declaration=True)


def init():
    if STATE.exists():
        previous = load()
        if not previous.get("cleaned"):
            raise Failure("Previous run is not cleaned; run cleanup before init.")
    # Results belong only to this runner; prevent stale JUnit reports from a previous run.
    RESULTS.mkdir(exist_ok=True)
    for path in RESULTS.iterdir():
        if path.is_file() and (path.suffix in {".xml", ".log"} or path.name in {"state.json", "summary.json"}):
            path.unlink()
    back_reports = RESULTS / "back-junit"
    if back_reports.is_dir():
        for path in back_reports.glob("*.xml"):
            path.unlink()
    state = {"id": uuid.uuid4().hex[:12], "images": {}, "containers": [], "network": None,
             "phases": {}, "cleaned": False}
    save(state)
    command(["docker", "version"], timeout=30)
    command(["docker", "compose", "version"], timeout=30)
    print("CI run: " + state["id"], flush=True)


def build(state, service, target):
    key = f"{service}-{target}"
    tag = f"port8282-ci-{state['id']}-{service}:{target}"
    state["images"][key] = tag
    save(state)
    command(["docker", "build", "--progress=plain", "--target", target,
             "--label", f"{LABEL}={state['id']}", "-t", tag, CONTEXTS[service]], timeout=1200)
    return tag


def container(state, suffix, image, args=(), options=()):
    name = f"p8282-ci-{state['id']}-{suffix}"
    if name not in state["containers"]:
        state["containers"].append(name)
        save(state)
    command(["docker", "create", "--name", name, "--label", f"{LABEL}={state['id']}",
             *options, image, *args], timeout=30)
    return name


def run_test(state, suffix, image, args, copy_from=None):
    name = container(state, suffix, image, args, options=["--init", "--env", "CI=true"])
    try:
        command(["docker", "start", "--attach", name], timeout=900)
        exit_code = capture(["docker", "inspect", "-f", "{{.State.ExitCode}}", name])
        if exit_code != "0":
            raise Failure(f"{suffix}: container exited {exit_code}")
    finally:
        if copy_from:
            copied = command(["docker", "cp", f"{name}:{copy_from}", str(RESULTS / f"{suffix}.xml")],
                             timeout=30, check=False)
            if copied:
                raise Failure(f"{suffix}: JUnit report could not be collected")


def config(_state):
    # Explicit sample env prevents loading a developer's ignored root .env.
    base = ["docker", "compose", "--env-file", ".env.example", "-f", "compose.yaml"]
    command([*base, "config", "--quiet"], timeout=30)
    command([*base, "-f", "compose.dev.yaml", "config", "--quiet"], timeout=30)


def front(state):
    build(state, "front", "runtime")  # npm ci + npm run build in the pinned Dockerfile.
    manifest = json.loads((ROOT / "front/package.json").read_text(encoding="utf-8"))
    if "test" in manifest.get("scripts", {}):
        image = build(state, "front", "development")
        run_test(state, "front-tests", image, ["npm", "test"])
    else:
        report("front-function-tests", skipped="No npm test script yet; production build only.")


def back(state):
    image = build(state, "back", "build")  # Existing Dockerfile runs locked Gradle build/test.
    name = container(state, "back-report", image)
    destination = RESULTS / "back-junit"
    destination.mkdir(exist_ok=True)
    command(["docker", "cp", f"{name}:/workspace/build/test-results/test/.", str(destination)], timeout=30)
    if not list(destination.glob("TEST-*.xml")):
        raise Failure("Back build produced no JUnit reports; expected at least the health test.")
    build(state, "back", "runtime")


def python_service(state, service):
    image = build(state, service, "development")
    run_test(state, f"{service}-lint", image, ["uv", "run", "--locked", "ruff", "check", "src", "tests"])
    tests = ROOT / CONTEXTS[service] / "tests"
    has_tests = any(p.name.startswith("test_") or p.name.endswith("_test.py") for p in tests.rglob("*.py"))
    if has_tests:
        # A collection failure or pytest exit 5 is a failure when test files are present.
        run_test(state, f"{service}-tests", image,
                 ["uv", "run", "--locked", "pytest", "--junitxml=/app/pytest.xml"], "/app/pytest.xml")
    else:
        report(f"{service}-function-tests", skipped="No pytest test files yet; Ruff and runtime health only.")
    build(state, service, "runtime")


def healthy(name, deadline):
    while time.monotonic() < deadline:
        data = json.loads(capture(["docker", "inspect", name]))[0]
        status = data["State"]
        if not status.get("Running"):
            command(["docker", "logs", name], timeout=30, check=False)
            raise Failure(f"{name} stopped before becoming healthy")
        if status.get("Health", {}).get("Status") == "healthy":
            return
        time.sleep(2)
    command(["docker", "logs", name], timeout=30, check=False)
    raise Failure(f"{name} health timeout")


def smoke(state):
    network = f"p8282-ci-{state['id']}"
    state["network"] = network
    save(state)
    command(["docker", "network", "create", "--label", f"{LABEL}={state['id']}", network], timeout=30)
    names = {}
    for service in CONTEXTS:
        image = state["images"].get(f"{service}-runtime")
        if not image:
            raise Failure(f"Build {service} before smoke.")
        options = ["--init", "--network", network, "--network-alias", service]
        if service == "back":
            options += ["--env", "SPRING_PROFILES_ACTIVE=local"]
        name = container(state, f"{service}-smoke", image, options=options)
        names[service] = name
        command(["docker", "start", name], timeout=30)
    deadline = time.monotonic() + 180
    for name in names.values():
        healthy(name, deadline)
        user = capture(["docker", "exec", name, "id", "-u"])
        if user == "0":
            raise Failure(f"{name} runs as root")
    command(["docker", "exec", names["front"], "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"], timeout=15)
    body = capture(["docker", "exec", names["back"], "curl", "-fsS", "--max-time", "5",
                    "http://127.0.0.1:8080/actuator/health"])
    if json.loads(body).get("status") != "UP":
        raise Failure("Back health response is not UP")
    for service in ("ai", "ml"):
        expression = ("import json,urllib.request; "
                      "d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5)); "
                      f"assert d == {{'status':'ok','service':'{service}'}}")
        command(["docker", "exec", names[service], "python", "-c", expression], timeout=15)
    command(["docker", "exec", names["ai"], "python", "-c",
             ("import json,urllib.request; d=json.load(urllib.request.urlopen('http://ml:8000/health',timeout=5)); "
              "assert d == {'status':'ok','service':'ml'}")], timeout=15)
    print("Runtime smoke passed. Back uses local profile: no DB, business API or model inference validation.")


def cleanup(state):
    command(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=30)
    errors = []
    resources = [("container", n) for n in state["containers"]]
    if state["network"]:
        resources.append(("network", state["network"]))
    resources.extend(("image", image) for image in state["images"].values())
    for kind, name in resources:
        result = subprocess.run(["docker", kind, "inspect", name], cwd=ROOT, capture_output=True,
                                text=True, timeout=30, check=False)
        if result.returncode:
            if "no such" in result.stderr.lower() or "not found" in result.stderr.lower():
                continue
            errors.append(f"Cannot inspect {kind} {name}: {result.stderr.strip()}")
            continue
        data = json.loads(result.stdout)[0]
        labels = data.get("Labels", {}) if kind == "network" else data.get("Config", {}).get("Labels", {})
        if (labels or {}).get(LABEL) != state["id"]:
            errors.append(f"Refusing to remove unowned {kind}: {name}")
            continue
        args = ["docker", kind, "rm"]
        if kind == "container":
            args += ["--force"]
        if command([*args, name], timeout=30, check=False):
            errors.append(f"Cannot remove {kind}: {name}")
    if errors:
        raise Failure("; ".join(errors))
    state["cleaned"] = True
    save(state)


def phase(name):
    state = load()
    started = time.monotonic()
    try:
        if name in ("ai", "ml"):
            python_service(state, name)
        else:
            globals()[name](state)
    except Exception as exc:
        report(f"phase-{name}", error=exc, elapsed=time.monotonic() - started)
        state["phases"][name] = "failed"
        save(state)
        raise
    report(f"phase-{name}", elapsed=time.monotonic() - started)
    state["phases"][name] = "passed"
    save(state)
    (RESULTS / "summary.json").write_text(json.dumps({
        "id": state["id"], "phases": state["phases"],
        "scope": "CI configuration/build/lint/runtime smoke; missing feature tests are explicitly skipped",
        "skipped_reports": [p.name for p in RESULTS.glob("*-function-tests.xml")],
        "not_validated": ["DB integration", "scheduling", "demurrage calculations", "model inference", "deployment"],
    }, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("init", *PHASES, "cleanup", "all"))
    args = parser.parse_args()
    if args.phase == "init":
        init()
    elif args.phase == "all":
        init()
        try:
            for name in PHASES:
                phase(name)
        finally:
            if STATE.exists():
                phase("cleanup")
    elif args.phase == "cleanup" and not STATE.exists():
        print("No CI state; nothing to clean up.")
    else:
        phase(args.phase)


if __name__ == "__main__":
    try:
        main()
    except (Failure, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"CI FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
