import json
import re
from functools import lru_cache, partial
from pathlib import Path

defaults_dir = Path(__file__).parent.joinpath("defaults")

re_parameter_column = re.compile(r"(.*) \(Parameter\)")

PARAMETER_DESCRIPTIONS = {
    "Method (Parameter)": {
        -1: "-1: Default",
        0: "0: Primal Simplex",
        1: "1: Dual Simplex",
        2: "2: Barrier",
        3: "3: Nondeterministic Concurrent",
        4: "4: Deterministic Concurrent",
        5: "5: Deterministic Concurrent Simplex",
    },
    "Presolve (Parameter)": {
        -1: "-1: Automatic",
        0: "0: Off",
        1: "1: Conservative",
        2: "2: Aggressive",
    },
    "Cuts (Parameter)": {
        -1: "-1: Automatic",
        0: "0: Off",
        1: "1: Moderate",
        2: "2: Aggressive",
        3: "3: Very aggressive",
    },
    "MIPFocus (Parameter)": {
        0: "0: Balanced",
        1: "1: Feasibility",
        2: "2: Optimality",
        3: "3: Bound",
    },
}


@lru_cache()
def load_defaults(version):
    version_file = defaults_dir.joinpath(f"{version}.json")
    if not version_file.exists():
        # Fall back to 950 defaults
        version_file = defaults_dir.joinpath("950.json")
    with version_file.open() as infile:
        return json.load(infile)


def fill_for_version(group, parameter_columns):
    parameter_defaults = load_defaults(
        version=group["Version"].iloc[0].replace(".", "")
    )
    for column in parameter_columns:
        default = parameter_defaults.get(re_parameter_column.match(column).group(1))
        if default is not None:
            group[column] = group[column].fillna(default).astype(type(default))
    return group


def fill_default_parameters(summary):
    """Fill NaN parameter values with the actual default value."""
    parameter_columns = [
        column
        for column, series in summary.items()
        if re_parameter_column.match(column) and series.isnull().any()
    ]
    # TODO test cases where there are different versions involved
    return summary.groupby("Version").apply(
        partial(fill_for_version, parameter_columns=parameter_columns)
    )


def fill_for_version_nosuffix(group):
    parameter_defaults = load_defaults(
        version=group["Version"].iloc[0].replace(".", "")
    )
    for parameter in group.columns:
        default = parameter_defaults.get(parameter)
        if default is not None:
            group[parameter] = group[parameter].fillna(default).astype(type(default))
    return group


def fill_default_parameters_nosuffix(parameters):
    """Fill defaults for Version and parameter cols with no (Parameter) suffix."""
    return parameters.groupby("Version").apply(fill_for_version_nosuffix)


def add_categorical_descriptions(summary):
    """Replace some columns with categorical descriptions if available.

    It modifies the summary dict in place.
    """
    parameter_columns = [
        column for column in summary.columns if column in PARAMETER_DESCRIPTIONS
    ]
    for column in parameter_columns:
        summary[column] = (
            summary[column].map(PARAMETER_DESCRIPTIONS[column]).astype("category")
        )
    return summary


def strip_model_and_seed(row):
    """Return the Log name.

    If the log path contains the model name, return everything to the left.
    Otherwise, just return the log stem.

    i.e. with Model = 'glass4'
        data/912-Cuts0-glass4-0.log -> 912-Cuts0
        data/some-log.log -> some-log
    """
    log_stem = Path(row["LogFilePath"]).stem
    run, mid, _ = log_stem.partition(row["Model"])
    if mid and run:
        return run.rstrip("-")
    return log_stem
