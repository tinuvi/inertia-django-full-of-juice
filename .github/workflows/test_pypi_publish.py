import json
import shlex
import subprocess
import urllib.request
from pathlib import Path
from typing import List, Union


def execute_command(command: Union[List[str], str], path=None) -> str:
    if not path:
        path = Path("./").resolve()

    print(f"{execute_command.__name__}: current path: {path}")

    subprocess_params = {"capture_output": True, "encoding": "utf8", "cwd": str(path)}
    if type(command) is not str:
        return subprocess.run(command, **subprocess_params).stdout
    else:
        process_list = list()
        previous_process = None
        for command_part in command.split("|"):
            args = shlex.split(command_part)
            if previous_process is None:
                process = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(path)
                )
            else:
                process = subprocess.Popen(
                    args,
                    stdin=previous_process.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(path),
                )
            process_list.append(process)
            previous_process = process
        last_process = process_list[-1]
        output, errors = last_process.communicate()
        result = output.decode("utf-8", "ignore")
        if errors:
            result += errors.decode("utf-8", "ignore")
        return result


def increase_version_to_test_pypi(path=None):
    result = execute_command(["poetry", "version", "prerelease"], path=path)
    print(result.strip())
    new_version = execute_command(["poetry", "version", "-s"], path=path).strip()
    return new_version


def version_exists_on_test_pypi(package_name, version):
    url = f"https://test.pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return version in data.get("releases", {})
    except urllib.error.HTTPError:
        return False


def publish_test_pypi(number_of_tries=20, path=None):
    first_command = "yes"
    second_command = "poetry publish --build --repository testpypi"
    command_to_publish = "|".join([first_command, second_command])

    version_output = execute_command(["poetry", "version"], path=path).strip()
    package_name, current_version = version_output.rsplit(" ", 1)

    for _ in range(number_of_tries):
        if version_exists_on_test_pypi(package_name, current_version):
            print(f"Version {current_version} already exists on TestPyPI, bumping...")
            current_version = increase_version_to_test_pypi(path=path)
            continue

        print(f"Publishing version: {current_version}")
        result = execute_command(command_to_publish, path=path)
        print(f"Received result from pypi: {result}")
        return

    print("Could not upload the package after all retries")
    exit(1)
