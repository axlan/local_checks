
from enum import Enum
from typing import NamedTuple, List, Optional

class ReturnStatus(Enum):
    OK = '0'
    WARN = '1'
    CRIT = '2'
    UNKNOWN = '3'
    PROGRAMATIC = 'P'

class Metric(NamedTuple):
    name: str
    warn_low: Optional[float] = None
    warn_high: Optional[float] = None
    crit_low: Optional[float] = None
    crit_high: Optional[float] = None
    value: Optional[float] = None

    def from_value(self, value:Optional[float]) -> 'Metric':
        return Metric(self.name, self.warn_low, self.warn_high, self.crit_low, self.crit_high, value)

    @staticmethod
    def __get_optional(val: Optional[float]) -> str:
        if val is None:
            return ''
        return str(val)

    def __repr__(self) -> str:
        value = Metric.__get_optional(self.value)
        warn = Metric.__get_optional(self.warn_low) + ':' + Metric.__get_optional(self.warn_high)
        crit = Metric.__get_optional(self.crit_low) + ':' + Metric.__get_optional(self.crit_high)
        return f'{self.name}={value};{warn};{crit}'


def print_result(status: ReturnStatus, name: str, values: List[Metric], description: str):
    if len(values) == 0:
        metrics_str = '-'
    else:
        metrics_str = '|'.join([str(v) for v in values])

    print(f'{status.value} {name} {metrics_str} {description}')


# Helper function for pulling values out of the reported state
def get_recursively(search_dict, field):
    """
    Takes a dict with nested lists and dicts,
    and searches all dicts for a key of the field
    provided.
    """
    fields_found = []

    for key, value in search_dict.items():

        if key == field:
            fields_found.append(value)

        elif isinstance(value, dict):
            results = get_recursively(value, field)
            for result in results:
                fields_found.append(result)

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    more_results = get_recursively(item, field)
                    for another_result in more_results:
                        fields_found.append(another_result)

    return fields_found
