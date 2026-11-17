from pydantic import BaseModel, Field

class IssuePayload(BaseModel):
    """Pydantic model representing the incoming bug report payload."""

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True,
    }

    file_path: str = Field(
        ...,
        min_length=1,
        description="Path to the python file containing the buggy function (relative or absolute)."
    )
    function_name: str = Field(
        ...,
        min_length=1,
        description="The exact name of the function def containing the bug."
    )
    error_log: str = Field(
        ...,
        min_length=1,
        description="The error message, exception name, or stderr output representing the failure."
    )


class AgentPayload(BaseModel):
    """Pydantic model representing incoming raw Python code payload for autonomous healing."""

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True,
    }

    file_content: str = Field(
        ...,
        min_length=1,
        description="The raw Python source code content to execute and heal."
    )
    file_name: str = Field(
        ...,
        min_length=1,
        description="The name of the uploaded Python file."
    )
