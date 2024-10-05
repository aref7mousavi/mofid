import argparse
import configparser
import logging
import os
import re
from datetime import datetime

from git import NoSuchPathError, TagReference, repo

SETTINGS_FILE = "backend/settings.py"
TOML_PATH = "configs/pyproject.toml"


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        yellow = "\033[93m"
        green = "\033[92m"
        reset = "\033[0m"
        record.msg = record.msg.capitalize()
        if record.levelno == logging.INFO:
            record.msg = f"{green}{record.msg}{reset}"
        elif record.levelno == logging.WARNING:
            record.msg = f"{yellow}{record.msg}{reset}"
        elif record.levelno == logging.ERROR:
            record.msg = f"\033[91m{record.msg}{reset}"
        return super().format(record)


logging.basicConfig(level=logging.INFO, format="%(message)s")
for handler in logging.getLogger().handlers:
    handler.setFormatter(ColoredFormatter("%(message)s"))


class BumpVersion:
    """
    bump version
        check first git config name and email
        check untracked files
        create version and tag
        push tag
        override settings file, commit and push updated settings file

    :argument: -m: minor -j major -s settings file
    """

    def __init__(self, version_type_format: str):
        try:
            self.repo = repo.Repo("./.git")
        except NoSuchPathError:
            logging.error("No git repository found")
            exit(1)
        self.version_type_format = version_type_format
        self.version = None
        self.version_ref = None

    def start(self):
        self.global_configs()
        self.check_untracked()
        self.create_tag()
        self.update_settings_file()
        self.push_tag()

    def update_settings_file(self):
        global SETTINGS_FILE

        if not SETTINGS_FILE:
            return

        if not os.path.exists(SETTINGS_FILE):
            return

        with open(SETTINGS_FILE, "r") as f:
            content = f.read()

        if not bool(re.search(r'VERSION\s*=\s*"(.*?)"', content)):
            content += f'VERSION = "{self.version}"\n'
        else:
            content = re.sub(r'VERSION\s*=\s*"(.*?)"', f'VERSION = "{self.version}"', content)

        if not bool(re.search(r'VERSION_REFERENCE\s*=\s*"(.*?)"', content)):
            content += f'VERSION_REFERENCE = "{self.version_ref}"\n'
        else:
            content = re.sub(
                r'VERSION_REFERENCE\s*=\s*"(.*?)"',
                f'VERSION_REFERENCE = "{self.version_ref}"',
                content,
            )

        with open(SETTINGS_FILE, "w") as file:
            file.write(content)

        if TOML_PATH:
            with open(TOML_PATH, "r") as file:
                content = file.read()

            content = re.sub(
                r'version\s*=\s*".*?"', f'version = "{self.version.lstrip("v")}"', content
            )

            with open(TOML_PATH, "w") as file:
                file.write(content)

        self.repo.git.add(A=True)
        self.repo.git.commit(m=f"build version: {self.version}")
        origin = self.repo.remote(name="origin")
        origin.push()

    def push_tag(self):
        origin = self.repo.remote(name="origin")
        origin.push(tags=True)
        logging.info("All tags pushed to the remote repository.")

    def create_tag(self) -> TagReference:
        self.version = self.next_tag()
        self.version_ref = self.repo.head.commit.hexsha[:8]
        tag_message = (
            f"new Version created:\n\t"
            f"version type: {self.version_type_format}\n\t"
            f"version number: {self.version}\n\t"
            f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\t"
            f"reference: {self.version_ref}"
        )
        new_tag = self.repo.create_tag(self.version, ref=self.version_ref, message=tag_message)
        logging.info(tag_message)
        return new_tag

    def next_tag(self) -> str:
        latest_version, sha = self.get_latest_version
        if self.version_type_format == "patch":
            latest_version[2] += 1
        if self.version_type_format == "minor":
            latest_version[2] = 0
            latest_version[1] += 1
        if self.version_type_format == "major":
            latest_version[2] = 0
            latest_version[1] = 0
            latest_version[0] += 1
        return "v" + ".".join(tuple(map(str, latest_version)))

    @property
    def get_latest_version(self) -> tuple[list[int], str] | tuple[list[int], None]:
        tags = sorted(self.repo.tags, key=lambda t: t.commit.committed_datetime)
        if tags:
            versions = [int(i) for i in tags[-1].name.lstrip("v").split(".")]
            if len(versions) != 3:
                logging.error("Invalid tag format. Tags must be like v0.0.1")
                exit(1)
            return versions, tags[-1].commit.hexsha
        return [0, 0, 0], None

    def check_untracked(self) -> None:
        if self.repo.is_dirty(untracked_files=True):
            logging.warning(self.repo.git.status())
            logging.error("There are changes that need to be committed.")
            exit(1)
        return

    def global_configs(self, config_level="repository"):
        if config_level == "repository":
            logging.info("Check local repository config ...")
            reader = self.repo.config_reader(config_level="repository")
        else:
            logging.info("Check global config ...")
            reader = self.repo.config_reader()
        try:
            name = reader.get_value("user", "name")
            email = reader.get_value("user", "email")
            logging.info(f"found name '{name}' and email '{email}' in local repository")
        except configparser.NoSectionError:
            if config_level == "repository":
                logging.warning("Git user or email not found")
                return self.global_configs(config_level="")
            else:
                logging.error("Git user or email not found")
                exit(1)
        if config_level != "repository":
            logging.info(f"Setting name '{name}' and email '{email}' in local repository")
            with self.repo.config_writer(config_level="repository") as config:
                config.set_value("user", "name", name)
                config.set_value("user", "email", email)


def arguments() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m", "--minor", help="Create minor version", default=False, action="store_true"
    )
    parser.add_argument(
        "-j", "--major", help="Create major version", default=False, action="store_true"
    )
    parser.add_argument("-s", "--settings", help="Settings file", nargs="?")
    args = parser.parse_args()
    if args.settings:
        global SETTINGS_FILE

        SETTINGS_FILE = args.settings
    if args.minor:
        return "minor"
    if args.major:
        return "major"
    return "patch"


if __name__ == "__main__":
    version_type = arguments()
    logging.info(f"starting {version_type} version ...")
    bump = BumpVersion(version_type)
    bump.start()
