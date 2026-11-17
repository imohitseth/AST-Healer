import os
import tempfile
import uuid
import sys
import re
import asyncio
import argparse
from dotenv import load_dotenv

from schemas import IssuePayload
from parser import extract_function_source, replace_function_source

import vertexai
from vertexai.generative_models import GenerativeModel

load_dotenv()

def clean_agent_code(response_text: str, function_name: str) -> str:
    """Cleans up markdown code blocks, conversational prefixes, and whitespaces from agent response."""
    code = response_text.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    def_prefix = f"def {function_name}"
    if def_prefix in code:
        idx = code.find(def_prefix)
        code = code[idx:]

    if code.endswith("```"):
        code = code[:-3].strip()

    return code

async def run_pytest_suite(test_file: str) -> tuple[int, str]:
    """Runs pytest asynchronously inside the virtual environment and returns exit code and output."""
    if sys.platform == "win32":
        python_exe = os.path.join(".venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join(".venv", "bin", "python")

    if not os.path.exists(python_exe):
        python_exe = sys.executable

    cmd = [python_exe, "-m", "pytest", test_file]

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await process.communicate()
    exit_code = process.returncode
    output = stdout.decode("utf-8") + stderr.decode("utf-8")
    return exit_code, output

async def run_script_file(script_file: str) -> tuple[int, str]:
    """Runs a Python script asynchronously inside the virtual environment and returns exit code and output."""
    if sys.platform == "win32":
        python_exe = os.path.join(".venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join(".venv", "bin", "python")

    if not os.path.exists(python_exe):
        python_exe = sys.executable

    cmd = [python_exe, script_file]

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await process.communicate()
    exit_code = process.returncode
    output = stdout.decode("utf-8") + stderr.decode("utf-8")
    return exit_code, output

def parse_python_traceback(traceback_text: str) -> tuple[str, str, str]:
    """
    Parses a standard Python traceback output to extract:
    (buggy_file_path, function_name, error_message)
    """
    lines = traceback_text.splitlines()
    if not lines:
        raise ValueError("Empty output, no traceback found.")

    error_message = lines[-1].strip()
    file_path = None
    function_name = None

    traceback_re = re.compile(r'^\s*File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(\w+)')

    for i in range(len(lines) - 2, -1, -1):
        match = traceback_re.match(lines[i])
        if match:
            func = match.group(3)
            if func == "<module>":
                continue
            file_path = match.group(1).replace("\\", "/")
            function_name = func
            break

    if not file_path or not function_name:
        raise ValueError("Could not extract file path or function name from Python traceback.")

    return file_path, function_name, error_message

def parse_pytest_failure(pytest_output: str) -> tuple[str, str, str]:
    """
    Parses the stdout of a pytest failure to extract:
    (buggy_file_path, function_name, error_message)
    """
    lines = pytest_output.splitlines()
    if not lines:
        raise ValueError("Empty output, no pytest logs found.")

    file_path = None
    function_name = None
    error_log = []

    file_line_err_re = re.compile(r"^([a-zA-Z0-9_\-\/\\\. ]+\.py):(\d+): (\w+)")

    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        match = file_line_err_re.match(line)
        if match:
            possible_file = match.group(1).replace("\\", "/")
            if "test_" in os.path.basename(possible_file):
                continue

            file_path = possible_file

            for j in range(i, -1, -1):
                if lines[j].strip().startswith("E   "):
                    error_log.append(lines[j].strip()[4:])
                    break
            if not error_log:
                error_log.append(line)

            func_def_re = re.compile(r"^\s*def\s+(\w+)\s*\(")
            for j in range(i, -1, -1):
                m = func_def_re.match(lines[j])
                if m:
                    function_name = m.group(1)
                    break

            if file_path and function_name:
                break

    if not file_path or not function_name:
        raise ValueError("Could not auto-detect buggy file or function from pytest output.")

    return file_path, function_name, "\n".join(error_log)

async def heal_once(payload: IssuePayload) -> None:
    """Performs a single edit attempt on a specific function using Gemini and AST replacement."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is missing.")

    vertexai.init(project=project_id, location=location)
    system_instruction = (
        "You are an expert Python debugger and Principal Staff Engineer. "
        "Your task is to fix bugs inside a single Python function definition. "
        "You will be given the original code of the function and the error log. "
        "You must return ONLY the corrected function code, starting with 'def'. "
        "Do not include any explanation, description, markdown formatting, or comment blocks. "
        "Just return the raw Python code."
    )

    model = GenerativeModel(
        "gemini-3.8-flash",
        system_instruction=[system_instruction]
    )

    print(f"Extracting source for function '{payload.function_name}'...")
    try:
        func_source = extract_function_source(payload.file_path, payload.function_name)
    except Exception as e:
        err_msg = f"AST Extraction Error: {e}"
        print(err_msg)
        raise ValueError(err_msg)

    print(f"Original source extracted successfully:\n---\n{func_source}\n---")

    prompt = f"""
Original function code:
```python
{func_source}
```

Error details:
```
{payload.error_log}
```

Please correct the function to make the execution/tests pass. Remember, return ONLY the corrected function definition.
"""

    print("Sending prompt to Vertex AI...")
    try:
        response = await model.generate_content_async(prompt)
        raw_response = response.text
    except Exception as e:
        err_msg = f"Vertex AI Error: {e}"
        print(err_msg)
        raise RuntimeError(err_msg)

    healed_code = clean_agent_code(raw_response, payload.function_name)
    print(f"Received healed code from agent:\n---\n{healed_code}\n---")

    print("Applying healed code to file...")
    try:
        replace_function_source(payload.file_path, payload.function_name, healed_code)
    except Exception as e:
        err_msg = f"Error replacing function source: {e}"
        print(err_msg)
        raise RuntimeError(err_msg)

async def heal_code(payload: IssuePayload, max_attempts: int = 1) -> bool:
    """Wrapper function to maintain backward compatibility with manual heal requests."""
    await heal_once(payload)
    return True

async def auto_heal_code(run_target: str, mode: str = "script", max_attempts: int = 5) -> bool:
    """
    Runs the target script or test suite. If it fails, auto-detects the error details,
    heals the detected function, and loops until all bugs are resolved or max_attempts is reached.
    """
    print("=" * 60)
    print(f"Starting Auto-Heal Loop for target: '{run_target}' in mode: '{mode}'")
    print("=" * 60)

    for attempt in range(1, max_attempts + 1):
        print(f"\n[Auto-Heal Attempt {attempt}/{max_attempts}] Running target...")
        if mode == "pytest":
            exit_code, output = await run_pytest_suite(run_target)
        else:
            exit_code, output = await run_script_file(run_target)

        if exit_code == 0:
            print("\n" + "*" * 60)
            print("SUCCESS: Target executed successfully with no errors!")
            print("*" * 60)
            return True

        print("Execution failed. Parsing traceback to auto-detect target...")
        try:
            if mode == "pytest":
                file_path, function_name, error_msg = parse_pytest_failure(output)
            else:
                file_path, function_name, error_msg = parse_python_traceback(output)
        except Exception as e:
            print(f"Failed to auto-detect bug: {e}")
            print(f"Raw Target Output:\n{output}")
            raise ValueError(f"Could not auto-detect buggy code: {e}")

        print("Auto-Detected Bug Details:")
        print(f"  File Path:     {file_path}")
        print(f"  Function Name: {function_name}")
        print(f"  Error Message: {error_msg}")
        payload = IssuePayload(
            file_path=file_path,
            function_name=function_name,
            error_log=error_msg
        )
        print(f"Triggering repair for function '{function_name}'...")
        await heal_once(payload)

        print("Pausing for 8 seconds to stay under the API rate limit...")
        await asyncio.sleep(8)

    print("\n" + "!" * 60)
    err_msg = f"Could not heal all errors after {max_attempts} attempts. Last output:\n{output}"
    print(err_msg)
    print("!" * 60)
    raise RuntimeError(err_msg)

async def process_autonomous_healing(file_content: str) -> dict:
    """
    Saves raw content to a temp file, runs it, parses any traceback,
    heals the file, and returns the updated content.
    """
    # 1. Generate a completely unique filename inside the system's safe /tmp directory
    unique_id = uuid.uuid4().hex
    temp_filename = os.path.join(tempfile.gettempdir(), f"temp_execution_{unique_id}.py")

    # 2. Save the uploaded content to disk
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(file_content)

    try:
        # 3. Run the file using your existing subprocess wrapper
        exit_code, output = await run_script_file(temp_filename)

        if exit_code != 0:
            print("Execution failed. Auto-detecting target from traceback...")
            try:
                # 4. Use your existing parser to isolate the bug
                file_path, function_name, error_msg = parse_python_traceback(output)
            except Exception as e:
                os.remove(temp_filename)
                return {"status": "error", "message": f"Could not auto-detect bug: {str(e)}"}

            # 5. Trigger the Vertex AI AST healer
            payload = IssuePayload(
                file_path=temp_filename,
                function_name=function_name,
                error_log=error_msg
            )
            await heal_once(payload)

            # 6. Read the newly healed file
            with open(temp_filename, "r", encoding="utf-8") as f:
                fixed_content = f.read()

            os.remove(temp_filename)
            return {
                "status": "healed",
                "fixed_code": fixed_content,
                "function_name": function_name,
                "error_msg": error_msg
            }

        else:
            # Code ran perfectly with no errors
            os.remove(temp_filename)
            return {"status": "no_error", "fixed_code": file_content}

    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"status": "error", "message": f"Autonomous healing failed: {str(e)}"}

async def main():
    parser = argparse.ArgumentParser(description="AST-Healer: Automated Self-healing Loop")
    parser.add_argument("--mode", default="script", choices=["script", "pytest"], help="Execution mode")
    parser.add_argument("--target", default="tests/mock_run.py", help="Target file to run")
    parser.add_argument("--max-attempts", type=int, default=5, help="Max attempts to try")
    args = parser.parse_args()

    success = await auto_heal_code(args.target, mode=args.mode, max_attempts=args.max_attempts)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
