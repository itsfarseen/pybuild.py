#!/usr/bin/env python3

##############################################
#  pybuild.py                                #
#  ==========                                #
#  A thin wrapper around requirements.txt    #
#  to auto-remove unused transitive deps.    #
#                                            #
#  GitHub:                                   #
#  https://github.com/itsfarseen/pybuild.py  #
##############################################

import json
import subprocess as sp
import sys
import os
from typing import TypedDict


class PyPackageJson(TypedDict):
    venv_dir: str
    dependencies: list[str]


VERSION = "1.1.0"

DEFAULT_CONFIG: PyPackageJson = {
    "venv_dir": ".venv",
    "dependencies": [],
}


def print_usage():
    print("pybuild.py", VERSION)
    print()
    print("  init <venv-dir>")
    print("    Init pypackage.json and create virtual env")
    print("    venv-dir: Directory to create virtual env in")
    print()
    print("  add <package>      Add package")
    print("  rm <package>       Remove package")
    print("  sync               Install packages specified in pypackages.json")
    print("                     and uninstall unnecessary packages.")


def main():
    args = sys.argv[1:]
    if len(args) == 0:
        print_usage()
        exit(0)

    if args[0] == "init":
        cmd_init(args[1:])
    elif args[0] == "add":
        cmd_add(args[1:])
    elif args[0] == "rm":
        cmd_rm(args[1:])
    elif args[0] == "sync":
        cmd_sync(args[1:])
    else:
        print_usage()


def load_pypackagejson():
    try:
        with open("pypackage.json") as f:
            pypackagejson = json.load(f)
    except FileNotFoundError:
        print("pypackage.json not found.")
        print("Run ./pybuild.py init to generate one")
        exit(-1)

    errors = []

    if not isinstance(pypackagejson, dict):
        errors.append("Invalid contents.")
    else:
        venv_dir = pypackagejson.get("venv_dir")
        if venv_dir is None:
            errors.append(("venv_dir", "not found"))
        elif not isinstance(venv_dir, str):
            errors.append(("venv_dir", "must be a string"))

        dependencies = pypackagejson.get("dependencies")
        if dependencies is None:
            dependencies = []
        elif not isinstance(dependencies, list):
            errors.append(("dependencies", "must be a list"))
    if len(errors) != 0:
        print("Error reading pypackage.json:")
        for error in errors:
            if isinstance(error, str):
                print(error)
            else:
                key, msg = error
                print(f"{key}: {msg}")
        exit(-1)
    else:
        return PyPackageJson(
            venv_dir=venv_dir,  # type: ignore
            dependencies=dependencies,  # type: ignore
        )


def save_pypackagejson(config: PyPackageJson):
    with open("pypackage.json", "w") as f:
        json.dump(config, f, indent=2)


def run(cmd, can_fail=False, capture_stdout=False):
    proc = sp.run(
        cmd,
        stdout=sp.PIPE if capture_stdout else None,
    )
    if not can_fail:
        if proc.returncode != 0:
            print("Failed to run:", " ".join(cmd))
            print("Process returned", proc.returncode)
            print("stdout:")
            print(proc.stdout)
            exit(-1)
    return proc.returncode, proc.stdout


def create_venv(config: PyPackageJson):
    venv_dir = config["venv_dir"]
    print("Creating virtual env in", venv_dir)
    run(["python3", "-m", "venv", venv_dir])


def ensure_venv(config: PyPackageJson, log_if_exists=False):
    venv_dir = config["venv_dir"]
    if not os.path.isdir(venv_dir):
        create_venv(config)
    elif log_if_exists:
        print("Virtual env folder exists:", venv_dir + ".", "Not overwriting.")
        print("(Delete this folder and run again if you want to recreate.)")
        print()


def pip_bin(config: PyPackageJson):
    pip = config["venv_dir"] + "/bin/pip"
    return pip


def pip_get_installed(config: PyPackageJson, uninstall_base_packages=False):
    base_packages = {"pip", "setuptools"}
    pip = pip_bin(config)
    _, stdout = run(
        [
            pip,
            "list",
            "--not-required",
            "--format",
            "json",
            "--disable-pip-version-check",
        ],
        capture_stdout=True,
    )
    installed_json = json.loads(stdout)
    installed = [
        x["name"].lower()
        for x in installed_json
        if not uninstall_base_packages or x["name"] not in base_packages
    ]
    return installed


def pip_install(config: PyPackageJson, packages: list[str]):
    pip = pip_bin(config)

    print("Installing packages:")
    for p in packages:
        print(" ", p)
    run(
        [
            pip,
            "install",
            "--disable-pip-version-check",
            *packages,
        ]
    )


def pip_uninstall(config: PyPackageJson, packages: list[str]):
    pip = pip_bin(config)

    print("Removing packages:")
    for p in packages:
        print(" ", p)
    run(
        [
            pip,
            "uninstall",
            "--disable-pip-version-check",
            *packages,
        ]
    )


def pip_freeze(config: PyPackageJson):
    pip = pip_bin(config)

    _, stdout = run([pip, "freeze"], capture_stdout=True)
    with open("requirements.txt", "wb") as f:
        f.write(stdout)


def sync_deps(config: PyPackageJson):
    ensure_venv(config)

    deps = config["dependencies"]
    installed = pip_get_installed(config)

    to_install = []
    for p in deps:
        if p not in installed:
            to_install.append(p)

    if len(to_install) > 0:
        print("Installing:")
        for p in to_install:
            print(" ", p)
        print()

        pip_install(config, to_install)

    while True:
        installed = pip_get_installed(
            config,
            uninstall_base_packages=True,
        )

        to_uninstall = []
        for p in installed:
            if p not in deps:
                to_uninstall.append(p)

        if len(to_uninstall) == 0:
            break

        print("Removing:")
        for p in to_uninstall:
            print(" ", p)
        print()
        pip_uninstall(config, to_uninstall)

    pip_freeze(config)


def cmd_init(args):
    if len(args) > 1:
        print("Error: Extra options received.")
        print()
        print_usage()
        exit(-1)

    if len(args) < 1:
        print("Error: Too few options received.")
        print()
        print_usage()
        exit(-1)

    venv_dir = args[0]

    if os.path.isfile("pypackage.json"):
        print("pypackage.json exists. Not overwriting.")
        print()
    else:
        config = DEFAULT_CONFIG
        config["venv_dir"] = venv_dir
        save_pypackagejson(config)

    config = load_pypackagejson()
    ensure_venv(config, log_if_exists=True)
    sync_deps(config)


def cmd_add(args):
    if len(args) == 0:
        print("Error: Please specify the packages.")
        print()
        print_usage()
        exit(-1)

    config = load_pypackagejson()
    packages = args
    to_lowercase(packages)

    for p in packages:
        if p not in config["dependencies"]:
            config["dependencies"].append(p)

    save_pypackagejson(config)
    sync_deps(config)


def cmd_rm(args):
    if len(args) == 0:
        print("Error: Please specify the packages.")
        print()
        print_usage()
        exit(-1)

    config = load_pypackagejson()
    packages = args
    to_lowercase(packages)

    config["dependencies"] = [p for p in config["dependencies"] if p not in packages]

    save_pypackagejson(config)
    sync_deps(config)


def cmd_sync(args):
    if len(args) != 0:
        print("Error: Extra options received.")
        print()
        print_usage()

    config = load_pypackagejson()
    sync_deps(config)


def to_lowercase(list):
    for i in range(len(list)):
        list[i] = list[i].lower()


if __name__ == "__main__":
    main()
