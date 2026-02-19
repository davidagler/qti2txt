import logging
import sys
from logging.handlers import RotatingFileHandler  # for file handling and backups


# Class for coloring logging
class SimpleColorFormatter(logging.Formatter):
    # map colors ANSI
    LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",  # 10 Cyan
        logging.INFO: "\033[32m",  # 20 Green
        logging.WARNING: "\033[33m",  # 30 Yellow
        logging.ERROR: "\033[31m",  # 40 Red
        logging.CRITICAL: "\033[41m",  # 50 Red
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, "")
        # Format normally
        formatted = super().format(record)
        # Add color only if available
        if color:
            return f"{color}{formatted}{self.RESET}"  # Add color + message + reset
        return formatted  # otherwise no color


# Two-stage logging setup.
def startup_logger():
    """Basic logging before argparse. https://docs.python.org/3/library/logging.html"""
    ch = logging.StreamHandler(sys.stdout)
    formatter = SimpleColorFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[ch],
    )


def primary_logger(output_dir, verbose=False):
    """Enhanced logging setup. Initialized after the initial file checks are complete. Essentially follows the logging tut in the Python documentation: https://docs.python.org/3/howto/logging.html#logging-basic-tutorial"""

    # clears the startup_logger handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:  # iterate over copy not original
        logger.removeHandler(handler)

    level = logging.DEBUG if verbose else logging.INFO

    # create console handler and set level to INFO
    # Formatting. Requires old %-style string formatting. For list of attributes https://docs.python.org/3/library/logging.html#logrecord-attributes
    log_output_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

    ch = logging.StreamHandler(sys.stdout)  # sys.stderr
    ch.setFormatter(SimpleColorFormatter(log_output_format))

    # File handler - Since we are using color and don't want ANSI codes in color codes in our log file, we'll use a separate formatter
    # add formatter to ch
    fh = RotatingFileHandler(
        output_dir / "qti2txt.log",
        maxBytes=1 * 1024 * 1024,
        backupCount=2,  # 1MB, 2 backup
    )
    fh.setFormatter(logging.Formatter(log_output_format))

    # File handler for log file. When log file reaches 1MB, it becomes backup and a new qti2txt.log file is created with new logs. When the new file reaches 1MB, it becomes backup. Max backups = 2. When a 4th file is created, the third file replaces the earliest backup (which is deleted.). This is probably overkill. See here https://docs.python.org/3/howto/logging.html#useful-handlers

    logger.setLevel(level)
    logger.addHandler(ch)
    logger.addHandler(fh)
