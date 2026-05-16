FOODS_SEARCHABLE_ATTRIBUTES = [
    "name",
    "brand",
    "categories",
]

FOODS_FILTERABLE_ATTRIBUTES = [
    "type",
    "categories",
]

FOODS_SORTABLE_ATTRIBUTES = [
    "completeness_score",
    "name_length",
    "generic_boost",
]

FOODS_CUSTOM_RANKING = [
    "words",
    "typo",
    "proximity",
    "attribute",
    "sort",
    "exactness",
    "completeness_score:desc",
    "generic_boost:desc",
    "name_length:asc",
]
