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
