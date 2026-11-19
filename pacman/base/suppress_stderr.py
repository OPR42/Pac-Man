import os
import sys

from types import TracebackType


class SuppressStderr(object):
    """ Temporarily redirect stderr to the null device. """

    def __enter__(self) -> "SuppressStderr":
        """ Redirect stderr until leaving the context. """
        self.old_stderr = sys.stderr

        if self.old_stderr is None:
            return self

        self.errnull_file = open(os.devnull, 'w')
        self.old_stderr_fileno_undup = self.old_stderr.fileno()
        self.old_stderr_fileno = os.dup(self.old_stderr_fileno_undup)
        os.dup2(self.errnull_file.fileno(), self.old_stderr_fileno_undup)
        sys.stderr = self.errnull_file

        return self

    def __exit__(self,
                 exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType | None,
                 ) -> None:
        """ Restore the original stderr stream. """
        if self.old_stderr is None:
            return

        sys.stderr = self.old_stderr
        os.dup2(self.old_stderr_fileno, self.old_stderr_fileno_undup)
        os.close(self.old_stderr_fileno)
        self.errnull_file.close()
