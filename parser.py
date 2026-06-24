import ast
import textwrap

def extract_function_source(file_path: str, function_name: str) -> str:
    """
    Parses the file at file_path into an AST, finds the FunctionDef node 
    matching function_name, and returns its raw source code block.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            source_segment = ast.get_source_segment(source_code, node)
            if source_segment is not None:
                return source_segment
            else:
                raise ValueError(f"Could not retrieve source segment for function '{function_name}'.")

    raise ValueError(f"Function '{function_name}' not found in file '{file_path}'")

def adjust_indentation(code: str, target_indent_spaces: int) -> str:
    """
    Dedents the input code first, then indents non-empty lines to match 
    the target_indent_spaces level.
    """
    dedented = textwrap.dedent(code)
    return textwrap.indent(dedented, " " * target_indent_spaces)

def replace_function_source(file_path: str, function_name: str, new_source_code: str) -> None:
    """
    Locates the FunctionDef node in the source file, calculates its line range, 
    replaces it with the new healed function code matching the original 
    indentation level, and writes the updated contents back to disk.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    target_node = None
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            target_node = node
            break

    if target_node is None:
        raise ValueError(f"Function '{function_name}' not found in file '{file_path}'")

    # Match indentation of original FunctionDef
    indent_spaces = target_node.col_offset
    adjusted_new_code = adjust_indentation(new_source_code, indent_spaces)

    if not adjusted_new_code.endswith("\n"):
        adjusted_new_code += "\n"

    # Split original code by lines to do line-range replacement
    lines = source_code.splitlines(keepends=True)
    
    # ast line numbers are 1-indexed
    start_idx = target_node.lineno - 1
    end_idx = target_node.end_lineno

    # Perform the in-place line replacement
    lines[start_idx:end_idx] = [adjusted_new_code]

    # Write the modified code back to the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
