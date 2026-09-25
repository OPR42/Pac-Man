import os
import sys

from types import TracebackType


class SuppressStderr(object):
    """ Temporarily redirect stderr to the null device. """
    def __enter__(self) -> "SuppressStderr":
        """ Redirect stderr until leaving the context. """
        self.errnull_file = open(os.devnull, 'w')
        self.old_stderr_fileno_undup = sys.stderr.fileno()
        self.old_stderr_fileno = os.dup(sys.stderr.fileno())
        self.old_stderr = sys.stderr
        os.dup2(self.errnull_file.fileno(), self.old_stderr_fileno_undup)
        sys.stderr = self.errnull_file

        return self

    def __exit__(self,
                 exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType | None,
                 ) -> None:
        """ Restore the original stderr stream. """
        sys.stderr = self.old_stderr
        os.dup2(self.old_stderr_fileno, self.old_stderr_fileno_undup)
        os.close(self.old_stderr_fileno)
        self.errnull_file.close()
