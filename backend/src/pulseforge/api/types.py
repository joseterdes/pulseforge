from typing import Annotated

from pydantic import StringConstraints


def plain_text(min_length: int, max_length: int) -> type[str]:
    """Whitespace-stripped single-line text that rejects control characters (incl. NUL)."""
    return Annotated[  # type: ignore[return-value]
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=min_length,
            max_length=max_length,
            pattern=r"^[^\x00-\x1f\x7f]*$",
        ),
    ]
