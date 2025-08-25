"""TokenBuffer module

This module contains the TokenBuffer class, which is a class that provides a
way to look ahead in a token stream. It uses a deque to store the tokens and
provides a way to look ahead in the stream by indexing the buffer. It also
provides a way to advance the buffer by one token at a time, which is useful
for parsing.

The buffer is initially empty and is populated by the token stream as tokens
are requested. The buffer is only populated up to the point where the requested
token is, so if the token stream is infinite, the buffer will never contain
more than one token.

"""

from collections import deque
from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class TokenBuffer(Generic[T]):
    """A TokenBuffer is a class that provides a way to look ahead in a token
    stream. It uses a deque to store the tokens and provides a way to look
    ahead in the streamby indexing the buffer. It also provides a way to
    advance the buffer by one token
    at a time, which is useful for parsing.

    The buffer is initially empty and is populated by the token stream as
    tokens are requested. The buffer is only populated up to the point where
    the requested token is, so if the token stream is infinite, the buffer will
    never contain more than one token.

    :param token_stream: An iterator over the tokens in the stream.
    """

    def __init__(self, token_stream: Iterator[T]):
        self.token_stream = token_stream
        self.buffer: deque[T] = deque()

    def __getitem__(self, index: int) -> T:
        while len(self.buffer) <= index:
            try:
                self.buffer.append(next(self.token_stream))
            except StopIteration as exc:
                raise IndexError("TokenBuffer: out of tokens.") from exc
        return self.buffer[index]

    def advance(self) -> None:
        """Advance the buffer by one token."""
        if not self.buffer:
            raise IndexError("TokenBuffer: trying to advance empty buffer.")
        self.buffer.popleft()

    def current(self) -> T:
        """Return the current token."""
        return self[0]

    def __len__(self) -> int:
        return len(self.buffer)

    def __repr__(self) -> str:
        return f"TokenBuffer({self.buffer!r})"

    def __str__(self) -> str:
        return str(self.buffer)

    def __iter__(self):
        return iter(self.buffer)
